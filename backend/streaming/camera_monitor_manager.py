import threading
from urllib.parse import quote, urlsplit, urlunsplit

from django.db import close_old_connections
from django.utils import timezone

from cameras.models import Camera, CameraStream

from streaming.camera_frame_hub import (
    camera_frame_hub,
)

from recordings.recording_service import (
    CameraRecordingService,
)

from ai_engine.camera_inference_service import (
    CameraInferenceError,
    CameraInferenceService,
)


class CameraMonitorManager:

    def __init__(
        self,
        reconnect_delay=5,
        tracking_timeout_seconds=30,
    ):
        self.reconnect_delay = reconnect_delay
        self.tracking_timeout_seconds = (
            tracking_timeout_seconds
        )

        self._workers = {}
        self._lock = threading.RLock()

    def start_camera(self, camera_id):
        with self._lock:
            existing = self._workers.get(
                camera_id
            )

            if (
                existing is not None
                and existing["thread"].is_alive()
            ):
                return False

            stop_event = threading.Event()

            thread = threading.Thread(
                target=self._worker,
                args=(camera_id, stop_event),
                daemon=True,
                name=f"camera-monitor-{camera_id}",
            )

            self._workers[camera_id] = {
                "thread": thread,
                "stop_event": stop_event,
            }

            thread.start()

            return True

    def stop_camera(self, camera_id):
        with self._lock:
            worker = self._workers.get(
                camera_id
            )

            if worker is None:
                return False

            worker["stop_event"].set()

            return True

    def is_running(self, camera_id):
        with self._lock:
            worker = self._workers.get(
                camera_id
            )

            if worker is None:
                return False

            return worker["thread"].is_alive()

    def get_status(self, camera_id):
        with self._lock:
            worker = self._workers.get(
                camera_id
            )

            if worker is None:
                return {
                    "camera_id": camera_id,
                    "running": False,
                }

            return {
                "camera_id": camera_id,
                "running": worker["thread"].is_alive(),
            }

    def stop_all(self):
        with self._lock:
            for worker in self._workers.values():
                worker["stop_event"].set()

    @staticmethod
    def _build_authenticated_stream_url(
        camera,
        stream_url,
    ):
        username = camera.username
        password = camera.get_credential()

        if not username or not password:
            return stream_url

        parsed = urlsplit(stream_url)
        host = parsed.hostname

        if not host:
            return stream_url

        netloc = (
            f"{quote(username, safe='')}:"
            f"{quote(password, safe='')}@"
            f"{host}"
        )

        if parsed.port:
            netloc += f":{parsed.port}"

        return urlunsplit(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )

    def _build_recorder(
        self,
        camera,
        main_stream,
        service,
    ):
        try:
            properties = service.get_stream_properties()

            return CameraRecordingService(
                camera=camera,
                stream=main_stream,
                fps=properties.get("fps") or 20.0,
                segment_seconds=300,
            )

        except Exception:
            return None

    def _worker(
        self,
        camera_id,
        stop_event,
    ):
        close_old_connections()

        try:
            while not stop_event.is_set():
                camera = (
                    Camera.objects
                    .select_related(
                        "organization"
                    )
                    .filter(id=camera_id)
                    .first()
                )

                if camera is None:
                    break

                if not camera.enabled:
                    self._set_camera_status(
                        camera,
                        Camera.Status.OFFLINE,
                    )
                    break

                main_stream = (
                    camera.streams
                    .filter(
                        stream_type=(
                            CameraStream.StreamType.MAIN
                        ),
                        enabled=True,
                    )
                    .first()
                )

                if main_stream is None:
                    self._set_camera_status(
                        camera,
                        Camera.Status.ERROR,
                    )
                    break

                service = None
                recorder = None

                try:
                    stream_url = (
                        self._build_authenticated_stream_url(
                            camera,
                            main_stream.url,
                        )
                    )

                    service = CameraInferenceService(
                        source=stream_url,
                        reconnect_attempts=3,
                        reconnect_delay=2,
                        tracking_timeout_seconds=(
                            self.tracking_timeout_seconds
                        ),
                    )

                    service.connect()

                    self._set_camera_status(
                        camera,
                        Camera.Status.ONLINE,
                    )

                    if camera.recording_enabled:
                        recorder = self._build_recorder(
                            camera,
                            main_stream,
                            service,
                        )

                    while not stop_event.is_set():
                        try:
                            # One physical RTSP read.
                            frame = service.read_frame()

                            if frame is None:
                                raise CameraInferenceError(
                                    "Empty camera frame."
                                )

                            # Publish immediately so live viewers
                            # do not wait for AI/database work.
                            camera_frame_hub.publish(
                                camera_id,
                                frame,
                            )

                            result = (
                                service.process_frame(
                                    camera=camera,
                                    frame=frame,
                                )
                            )

                            self._mark_camera_seen(
                                camera_id
                            )

                            if recorder is not None:
                                try:
                                    recorder.write(
                                        frame
                                    )
                                except Exception:
                                    try:
                                        recorder.close()
                                    except Exception:
                                        pass

                                    recorder = None

                            service.cleanup_stale_tracking()

                        except CameraInferenceError:
                            self._set_camera_status(
                                camera,
                                Camera.Status.ERROR,
                            )
                            break

                except CameraInferenceError:
                    self._set_camera_status(
                        camera,
                        Camera.Status.OFFLINE,
                    )

                except Exception:
                    self._set_camera_status(
                        camera,
                        Camera.Status.ERROR,
                    )

                finally:
                    if recorder is not None:
                        try:
                            recorder.close()
                        except Exception:
                            pass

                    if service is not None:
                        try:
                            service.stop()
                        except Exception:
                            pass

                camera_frame_hub.clear(
                    camera_id
                )

                if stop_event.is_set():
                    break

                if stop_event.wait(
                    self.reconnect_delay
                ):
                    break

        finally:
            close_old_connections()

            with self._lock:
                worker = self._workers.get(
                    camera_id
                )

                if (
                    worker is not None
                    and worker["stop_event"] is stop_event
                ):
                    del self._workers[camera_id]

            try:
                camera = (
                    Camera.objects
                    .filter(id=camera_id)
                    .first()
                )

                if camera is not None:
                    self._set_camera_status(
                        camera,
                        Camera.Status.OFFLINE,
                    )

            except Exception:
                pass

            camera_frame_hub.clear(
                camera_id
            )

            close_old_connections()

    @staticmethod
    def _set_camera_status(
        camera,
        status,
    ):
        Camera.objects.filter(
            id=camera.id
        ).update(
            status=status,
            updated_at=timezone.now(),
        )

    @staticmethod
    def _mark_camera_seen(
        camera_id,
    ):
        Camera.objects.filter(
            id=camera_id
        ).update(
            status=Camera.Status.ONLINE,
            last_seen=timezone.now(),
            updated_at=timezone.now(),
        )


camera_monitor_manager = CameraMonitorManager()
