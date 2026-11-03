import time
import queue
import threading
from urllib.parse import quote, urlsplit, urlunsplit

from django.db import close_old_connections
from django.utils import timezone

from cameras.models import Camera, CameraStream

from streaming.camera_frame_hub import (
    camera_frame_hub,
)

from streaming.camera_ai_frame_hub import (
    camera_ai_frame_hub,
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
        frame_queue_size=2,
        status_update_interval=1.0,
        tracking_cleanup_interval=2.0,
    ):
        self.reconnect_delay = reconnect_delay
        self.tracking_timeout_seconds = (
            tracking_timeout_seconds
        )
        self.frame_queue_size = max(
            1,
            int(frame_queue_size),
        )
        self.status_update_interval = float(
            status_update_interval
        )
        self.tracking_cleanup_interval = float(
            tracking_cleanup_interval
        )

        self._workers = {}
        self._ai_states = {}
        self._camera_failures = {}
        self._camera_runtime = {}
        self._lock = threading.RLock()

    def start_camera(self, camera_id):
        with self._lock:
            existing = self._workers.get(camera_id)

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

            self._camera_runtime[camera_id] = {
                "last_frame_at": None,
                "stream_healthy": False,
                "consecutive_failures": 0,
            }

            thread.start()

            return True

    def stop_camera(self, camera_id):
        with self._lock:
            worker = self._workers.get(camera_id)

            if worker is None:
                return False

            worker["stop_event"].set()

            return True

    def is_running(self, camera_id):
        with self._lock:
            worker = self._workers.get(camera_id)

            if worker is None:
                return False

            return worker["thread"].is_alive()

    def get_status(self, camera_id):
        with self._lock:
            worker = self._workers.get(camera_id)

            runtime = dict(
                self._camera_runtime.get(
                    camera_id,
                    {},
                )
            )

            running = (
                worker is not None
                and worker["thread"].is_alive()
            )

        last_frame_at = runtime.get(
            "last_frame_at"
        )

        last_frame_age_ms = None

        if last_frame_at is not None:
            last_frame_age_ms = max(
                0,
                int(
                    (
                        timezone.now()
                        - last_frame_at
                    ).total_seconds()
                    * 1000
                ),
            )

        stream_healthy = bool(
            runtime.get(
                "stream_healthy",
                False,
            )
        )

        if not running:
            connection_state = "STOPPED"
        elif stream_healthy:
            connection_state = "ONLINE"
        else:
            connection_state = runtime.get(
                "connection_state",
                "STARTING",
            )

        return {
            "camera_id": camera_id,
            "running": running,
            "connection_state": connection_state,
            "stream_healthy": stream_healthy,
            "connection_error": runtime.get("connection_error"),
            "last_frame_at": last_frame_at,
            "last_frame_age_ms": last_frame_age_ms,
            "consecutive_failures": int(
                runtime.get(
                    "consecutive_failures",
                    0,
                )
            ),
        }

    def get_ai_status(self, camera_id):
        with self._lock:
            state = self._ai_states.get(camera_id)

            if state is None:
                return {
                    "camera_id": camera_id,
                    "person_count": 0,
                    "vehicle_count": 0,
                    "animal_count": 0,
                    "animal_species_counts": {},
                    "object_count": 0,
                    "updated_at": None,
                    "overlay_available": False,
                    "error": None,
                }

            return dict(state)

    @staticmethod
    def _draw_ai_overlay(frame, detections):
        import cv2

        output = frame.copy()

        frame_height, frame_width = output.shape[:2]

        person_count = 0
        vehicle_count = 0
        animal_count = 0

        for detection in detections:
            object_type = str(
                detection.get("object_type") or "OBJECT"
            )

            label = str(
                detection.get("label") or object_type
            )

            confidence = float(
                detection.get("confidence") or 0
            )

            x = float(
                detection.get("bbox_x") or 0
            )

            y = float(
                detection.get("bbox_y") or 0
            )

            width = float(
                detection.get("bbox_width") or 0
            )

            height = float(
                detection.get("bbox_height") or 0
            )

            x1 = max(
                0,
                min(
                    frame_width - 1,
                    int(x * frame_width),
                ),
            )

            y1 = max(
                0,
                min(
                    frame_height - 1,
                    int(y * frame_height),
                ),
            )

            x2 = max(
                x1 + 1,
                min(
                    frame_width - 1,
                    int((x + width) * frame_width),
                ),
            )

            y2 = max(
                y1 + 1,
                min(
                    frame_height - 1,
                    int((y + height) * frame_height),
                ),
            )

            if object_type == "PERSON":
                color = (0, 0, 255)
                person_count += 1

            elif object_type == "VEHICLE":
                color = (255, 100, 0)
                vehicle_count += 1

            elif object_type == "ANIMAL":
                color = (0, 220, 100)
                animal_count += 1

            else:
                color = (0, 220, 255)

            cv2.rectangle(
                output,
                (x1, y1),
                (x2, y2),
                color,
                2,
            )

            text = (
                f"{label.upper()}"
            )
            tracking_id = detection.get("tracking_id")
            if tracking_id:
                text += f" #{tracking_id}"
            text += f" {confidence * 100:.0f}%"

            cv2.putText(
                output,
                text,
                (
                    x1,
                    max(20, y1 - 8),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )

        hud = (
            f"PERSONS: {person_count}   "
            f"VEHICLES: {vehicle_count}   "
            f"ANIMALS: {animal_count}   "
            f"OBJECTS: {len(detections)}"
        )

        cv2.rectangle(
            output,
            (10, 10),
            (440, 46),
            (0, 0, 0),
            -1,
        )

        cv2.putText(
            output,
            hud,
            (18, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        return output

    def stop_all(self):
        with self._lock:
            for worker in self._workers.values():
                worker["stop_event"].set()

    @staticmethod
    def _build_authenticated_stream_url(
        camera,
        stream_url,
    ):
        if stream_url.lower().startswith("local://"):
            return stream_url

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

    @staticmethod
    def _offer_latest(
        frame_queue,
        frame,
    ):
        try:
            frame_queue.put_nowait(frame)
            return
        except queue.Full:
            pass

        try:
            frame_queue.get_nowait()
        except queue.Empty:
            pass

        try:
            frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    def _ai_worker(
        self,
        camera,
        service,
        frame_queue,
        stop_event,
    ):
        close_old_connections()

        last_cleanup = 0.0
        last_inference = 0.0

        # AI runs independently from RTSP capture.
        # ~5 FPS keeps live video responsive.
        ai_interval = 0.20

        try:
            while (
                not stop_event.is_set()
                or not frame_queue.empty()
            ):
                try:
                    frame = frame_queue.get(
                        timeout=0.25
                    )
                except queue.Empty:
                    continue

                now_monotonic = time.monotonic()

                if (
                    now_monotonic - last_inference
                    < ai_interval
                ):
                    continue

                last_inference = now_monotonic

                try:
                    result = service.process_frame(
                        camera=camera,
                        frame=frame,
                    )

                    detection_models = result.get(
                        "detections",
                        [],
                    )

                    detections = [
                        {
                            "object_type": detection.object_type,
                            "label": detection.label,
                            "confidence": detection.confidence,
                            "tracking_id": detection.tracking_id,
                            "bbox_x": detection.bbox_x,
                            "bbox_y": detection.bbox_y,
                            "bbox_width": detection.bbox_width,
                            "bbox_height": detection.bbox_height,
                        }
                        for detection in detection_models
                    ]

                    annotated = self._draw_ai_overlay(
                        frame,
                        detections,
                    )

                    camera_ai_frame_hub.publish(
                        camera.id,
                        annotated,
                    )

                    person_count = sum(
                        1
                        for detection in detections
                        if detection["object_type"]
                        == "PERSON"
                    )

                    vehicle_count = sum(
                        1
                        for detection in detections
                        if detection["object_type"]
                        == "VEHICLE"
                    )
                    animal_detections = [
                        detection
                        for detection in detections
                        if detection["object_type"] == "ANIMAL"
                    ]
                    animal_species_counts = {}
                    for detection in animal_detections:
                        species = (
                            str(detection.get("label") or "animal")
                            .strip()
                            .lower()
                        )
                        animal_species_counts[species] = (
                            animal_species_counts.get(species, 0) + 1
                        )

                    with self._lock:
                        self._ai_states[
                            camera.id
                        ] = {
                            "camera_id": camera.id,
                            "person_count": person_count,
                            "vehicle_count": vehicle_count,
                            "animal_count": len(animal_detections),
                            "animal_species_counts": (
                                animal_species_counts
                            ),
                            "object_count": len(
                                detections
                            ),
                            "updated_at": timezone.now(),
                            "overlay_available": True,
                            "error": None,
                        }

                except CameraInferenceError as exc:
                    # AI failure must never stop camera capture.
                    camera_ai_frame_hub.publish(
                        camera.id,
                        frame,
                    )
                    self._set_ai_error(camera.id, exc)

                except Exception as exc:
                    # AI/database failure must never stop camera capture.
                    camera_ai_frame_hub.publish(
                        camera.id,
                        frame,
                    )
                    self._set_ai_error(camera.id, exc)

                now = timezone.now().timestamp()

                if (
                    now - last_cleanup
                    >= self.tracking_cleanup_interval
                ):
                    try:
                        service.cleanup_stale_tracking()
                    except Exception:
                        pass

                    last_cleanup = now

                close_old_connections()

        finally:
            close_old_connections()

    def _set_ai_error(self, camera_id, error):
        with self._lock:
            state = self._ai_states.get(camera_id, {})
            self._ai_states[camera_id] = {
                **state,
                "camera_id": camera_id,
                "person_count": 0,
                "vehicle_count": 0,
                "animal_count": 0,
                "animal_species_counts": {},
                "object_count": 0,
                "updated_at": timezone.now(),
                "overlay_available": False,
                "error": str(error),
            }

    def _recording_worker(
        self,
        recorder,
        frame_queue,
        stop_event,
    ):
        close_old_connections()

        try:
            while (
                not stop_event.is_set()
                or not frame_queue.empty()
            ):
                try:
                    frame = frame_queue.get(
                        timeout=0.25
                    )
                except queue.Empty:
                    continue

                try:
                    recorder.write(frame)
                except Exception:
                    break

        finally:
            try:
                recorder.close()
            except Exception:
                pass

            close_old_connections()

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

                # Global stop_event controls the lifetime of the
                # camera worker. cycle_stop_event controls only
                # the current RTSP/AI/recording connection cycle.
                cycle_stop_event = threading.Event()

                ai_queue = queue.Queue(
                    maxsize=self.frame_queue_size
                )
                recording_queue = queue.Queue(
                    maxsize=max(
                        self.frame_queue_size,
                        4,
                    )
                )

                ai_thread = None
                recording_thread = None

                try:
                    stream_url = (
                        self._build_authenticated_stream_url(
                            camera,
                            main_stream.url,
                        )
                    )

                    service = CameraInferenceService(
                        source=stream_url,
                        confidence=0.20,
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

                    if camera.ai_supported:
                        ai_thread = threading.Thread(
                            target=self._ai_worker,
                            args=(
                                camera,
                                service,
                                ai_queue,
                                cycle_stop_event,
                            ),
                            daemon=True,
                            name=(
                                f"camera-ai-{camera_id}"
                            ),
                        )

                        ai_thread.start()
                    else:
                        with self._lock:
                            self._ai_states.pop(camera_id, None)
                        camera_ai_frame_hub.clear(camera_id)

                    if camera.recording_enabled:
                        recorder = self._build_recorder(
                            camera,
                            main_stream,
                            service,
                        )

                    if recorder is not None:
                        recording_thread = (
                            threading.Thread(
                                target=(
                                    self._recording_worker
                                ),
                                args=(
                                    recorder,
                                    recording_queue,
                                    cycle_stop_event,
                                ),
                                daemon=True,
                                name=(
                                    f"camera-recording-"
                                    f"{camera_id}"
                                ),
                            )
                        )

                        recording_thread.start()

                    last_status_update = 0.0

                    # -------------------------------------------------
                    # CAPTURE-CRITICAL LOOP
                    #
                    # This loop performs only:
                    #   1. RTSP read
                    #   2. immediate live-frame publish
                    #   3. non-blocking handoff to AI/recording
                    #
                    # No AI inference, recorder.write() or tracking
                    # cleanup is allowed to block the live feed.
                    # -------------------------------------------------
                    while not stop_event.is_set():
                        try:
                            frame = service.read_frame()

                            if frame is None:
                                with self._lock:
                                    failures = (
                                        self._camera_failures.get(
                                            camera_id,
                                            0,
                                        )
                                        + 1
                                    )

                                    self._camera_failures[
                                        camera_id
                                    ] = failures

                                    runtime = (
                                        self._camera_runtime.setdefault(
                                            camera_id,
                                            {},
                                        )
                                    )

                                    runtime[
                                        "consecutive_failures"
                                    ] = failures

                                    runtime[
                                        "stream_healthy"
                                    ] = False

                                # A few consecutive empty frames
                                # indicate that this connection cycle
                                # should reconnect. Do NOT mark the
                                # camera permanently ERROR here.
                                if (
                                    failures
                                    >= 5
                                ):
                                    with self._lock:
                                        runtime = (
                                            self._camera_runtime.setdefault(
                                                camera_id,
                                                {},
                                            )
                                        )

                                        runtime[
                                            "connection_state"
                                        ] = "RECONNECTING"

                                    break

                                continue

                            # A valid frame means the camera is
                            # alive again.
                            now = timezone.now()

                            with self._lock:
                                self._camera_failures[
                                    camera_id
                                ] = 0

                                runtime = (
                                    self._camera_runtime.setdefault(
                                        camera_id,
                                        {},
                                    )
                                )

                                runtime[
                                    "last_frame_at"
                                ] = now

                                runtime[
                                    "stream_healthy"
                                ] = True

                                runtime[
                                    "consecutive_failures"
                                ] = 0
                                runtime["connection_error"] = None

                            # Publish to live clients FIRST.
                            camera_frame_hub.publish(
                                camera_id,
                                frame,
                            )

                            # Give AI the latest available frame
                            # without ever blocking RTSP capture.
                            if ai_thread is not None:
                                self._offer_latest(
                                    ai_queue,
                                    frame,
                                )

                            # Give recorder a frame without blocking
                            # the live capture loop.
                            if recorder is not None:
                                self._offer_latest(
                                    recording_queue,
                                    frame,
                                )

                            now = (
                                timezone.now().timestamp()
                            )

                            # Avoid a database UPDATE for every frame.
                            if (
                                now - last_status_update
                                >= self.status_update_interval
                            ):
                                self._mark_camera_seen(
                                    camera_id
                                )
                                last_status_update = now

                        except CameraInferenceError as exc:
                            self._set_camera_status(
                                camera,
                                Camera.Status.ERROR,
                            )
                            with self._lock:
                                runtime = self._camera_runtime.setdefault(
                                    camera_id,
                                    {},
                                )
                                runtime["connection_error"] = (
                                    "Camera stream failed. Check the "
                                    "camera source and credentials."
                                )
                            print(
                                f"[CAMERA] stream failed for camera "
                                f"{camera_id}: {type(exc).__name__}",
                                flush=True,
                            )
                            break

                except CameraInferenceError as exc:
                    self._set_camera_status(
                        camera,
                        Camera.Status.OFFLINE,
                    )
                    with self._lock:
                        runtime = self._camera_runtime.setdefault(
                            camera_id,
                            {},
                        )
                        runtime["connection_error"] = (
                            "Camera stream failed. Check the camera "
                            "source and credentials."
                        )
                    print(
                        f"[CAMERA] could not connect camera {camera_id}: "
                        f"{type(exc).__name__}",
                        flush=True,
                    )

                except Exception as exc:
                    self._set_camera_status(
                        camera,
                        Camera.Status.ERROR,
                    )
                    with self._lock:
                        runtime = self._camera_runtime.setdefault(
                            camera_id,
                            {},
                        )
                        runtime["connection_error"] = (
                            "Camera failed to start. Check the device, "
                            "stream URL, and credentials."
                        )
                    print(
                        f"[CAMERA] could not start camera {camera_id}: "
                        f"{type(exc).__name__}",
                        flush=True,
                    )

                finally:
                    # End only the current connection cycle.
                    # The outer worker loop remains alive and can
                    # reconnect the camera automatically.
                    cycle_stop_event.set()

                    if ai_thread is not None:
                        ai_thread.join(
                            timeout=3
                        )

                    if recording_thread is not None:
                        recording_thread.join(
                            timeout=5
                        )

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

            camera_ai_frame_hub.clear(
                camera_id
            )

            with self._lock:
                self._camera_failures.pop(
                    camera_id,
                    None,
                )

                self._camera_runtime.pop(
                    camera_id,
                    None,
                )

            with self._lock:
                self._ai_states.pop(
                    camera_id,
                    None,
                )

            close_old_connections()

    @staticmethod
    def _set_camera_status(
        camera,
        status,
    ):
        """
        Camera status persistence is best-effort.

        A temporary SQLite lock must NEVER terminate
        the camera capture worker.
        """
        for attempt in range(4):
            try:
                close_old_connections()

                Camera.objects.filter(
                    id=camera.id
                ).update(
                    status=status,
                    updated_at=timezone.now(),
                )

                return True

            except Exception as exc:
                message = str(exc).lower()

                if "database is locked" not in message:
                    print(
                        f"[CAMERA-DB] status update failed "
                        f"for camera {camera.id}: {exc!r}",
                        flush=True,
                    )
                    return False

                if attempt < 3:
                    time.sleep(
                        0.20 * (attempt + 1)
                    )

        print(
            f"[CAMERA-DB] status update skipped for "
            f"camera {camera.id}: SQLite remained locked.",
            flush=True,
        )

        return False

    @staticmethod
    def _mark_camera_seen(
        camera_id,
    ):
        """
        last_seen is opportunistic and must never kill
        the capture thread.
        """
        now = timezone.now()

        for attempt in range(4):
            try:
                close_old_connections()

                Camera.objects.filter(
                    id=camera_id
                ).update(
                    status=Camera.Status.ONLINE,
                    last_seen=now,
                    updated_at=now,
                )

                return True

            except Exception as exc:
                message = str(exc).lower()

                if "database is locked" not in message:
                    print(
                        f"[CAMERA-DB] last_seen update failed "
                        f"for camera {camera_id}: {exc!r}",
                        flush=True,
                    )
                    return False

                if attempt < 3:
                    time.sleep(
                        0.20 * (attempt + 1)
                    )

        print(
            f"[CAMERA-DB] last_seen update skipped for "
            f"camera {camera_id}: SQLite remained locked.",
            flush=True,
        )

        return False


camera_monitor_manager = CameraMonitorManager()
