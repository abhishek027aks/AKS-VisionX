from django.utils import timezone

from streaming.camera_stream_service import (
    CameraStream,
    CameraStreamError,
)

from ai_engine.inference_service import (
    AIInferenceService,
    AIInferenceError,
)

from events.tracking_end_service import (
    end_stale_tracking_sessions,
)


class CameraInferenceError(Exception):
    """Raised when camera AI processing fails."""
    pass


class CameraInferenceService:
    """
    Connects camera frames to the AI pipeline.

    The caller may supply an already-read frame.
    This allows the monitor to share one RTSP frame with
    live streaming, recording and AI.
    """

    def __init__(
        self,
        source,
        model_path="yolo11n.pt",
        tracker="bytetrack.yaml",
        confidence=0.25,
        reconnect_attempts=3,
        reconnect_delay=2,
        tracking_timeout_seconds=30,
    ):
        self.source = source
        self.tracking_timeout_seconds = (
            tracking_timeout_seconds
        )

        self.stream = CameraStream(
            source=source,
            reconnect_attempts=reconnect_attempts,
            reconnect_delay=reconnect_delay,
        )

        self.ai_service = AIInferenceService(
            model_path=model_path,
            tracker=tracker,
            confidence=confidence,
        )

        self.running = False

    def connect(self):
        try:
            return self.stream.connect()
        except CameraStreamError as exc:
            raise CameraInferenceError(
                "Unable to connect to camera."
            ) from exc

    def read_frame(self):
        try:
            return self.stream.read()
        except CameraStreamError as exc:
            raise CameraInferenceError(
                "Unable to read camera frame."
            ) from exc

    def process_frame(
        self,
        camera,
        zone="",
        frame=None,
    ):
        if camera is None:
            raise CameraInferenceError(
                "Camera is required."
            )

        if frame is None:
            frame = self.read_frame()

        if frame is None:
            raise CameraInferenceError(
                "Camera frame is empty."
            )

        try:
            result = self.ai_service.process_frame(
                camera=camera,
                frame=frame,
                occurred_at=timezone.now(),
                zone=zone,
            )
        except AIInferenceError as exc:
            raise CameraInferenceError(
                "Camera AI inference failed."
            ) from exc

        return {
            "frame": frame,
            "detections": result["detections"],
            "sessions": result["sessions"],
        }

    def cleanup_stale_tracking(self):
        return end_stale_tracking_sessions(
            timeout_seconds=self.tracking_timeout_seconds
        )

    def start(
        self,
        camera,
        zone="",
        max_frames=None,
    ):
        if camera is None:
            raise CameraInferenceError(
                "Camera is required."
            )

        self.connect()
        self.running = True
        processed_frames = 0

        try:
            while self.running:
                self.process_frame(
                    camera=camera,
                    zone=zone,
                )

                processed_frames += 1
                self.cleanup_stale_tracking()

                if (
                    max_frames is not None
                    and processed_frames >= max_frames
                ):
                    break

        except CameraInferenceError:
            raise

        finally:
            self.running = False
            self.stream.release()

        return processed_frames

    def stop(self):
        self.running = False
        self.stream.release()

    def get_stream_properties(self):
        return self.stream.get_properties()
