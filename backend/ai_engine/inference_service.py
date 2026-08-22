from django.utils import timezone

from events.models import Detection
from events.tracking_service import update_tracking_session

from ai_engine.detection_service import (
    YOLODetectionService,
)


class AIInferenceError(Exception):
    """Raised when AI frame processing fails."""
    pass


class AIInferenceService:
    """
    Connects YOLO inference with the Django detection/tracking pipeline.

    Pipeline:

        Frame
            -> YOLO
            -> Detection
            -> TrackingSession
            -> TrackingPoint
            -> TrackingLocation
            -> TrackingCameraVisit
    """

    def __init__(
        self,
        model_path="yolo11n.pt",
        tracker="bytetrack.yaml",
        confidence=0.25,
    ):
        self.detector = YOLODetectionService(
            model_path=model_path,
            tracker=tracker,
            confidence=confidence,
        )

    def process_frame(
        self,
        camera,
        frame,
        occurred_at=None,
        zone="",
    ):
        """
        Run AI inference on one frame and persist detections.

        Returns:
            {
                "detections": [...],
                "sessions": [...],
            }
        """

        if camera is None:
            raise AIInferenceError(
                "Camera is required."
            )

        if frame is None:
            raise AIInferenceError(
                "Frame is required."
            )

        occurred_at = occurred_at or timezone.now()

        try:
            ai_detections = self.detector.infer(
                frame
            )
        except Exception as exc:
            raise AIInferenceError(
                "AI frame inference failed."
            ) from exc

        saved_detections = []
        sessions = []

        for ai_detection in ai_detections:
            metadata = dict(
                ai_detection.get(
                    "metadata",
                    {},
                )
            )

            if zone:
                metadata["zone"] = zone

            detection = Detection.objects.create(
                organization=camera.organization,
                camera=camera,
                object_type=ai_detection[
                    "object_type"
                ],
                label=ai_detection.get(
                    "label",
                    "",
                ),
                confidence=ai_detection.get(
                    "confidence"
                ),
                tracking_id=ai_detection.get(
                    "tracking_id",
                    "",
                ),
                status=Detection.DetectionStatus.ACTIVE,
                first_seen_at=occurred_at,
                last_seen_at=occurred_at,
                bbox_x=ai_detection.get(
                    "bbox_x"
                ),
                bbox_y=ai_detection.get(
                    "bbox_y"
                ),
                bbox_width=ai_detection.get(
                    "bbox_width"
                ),
                bbox_height=ai_detection.get(
                    "bbox_height"
                ),
                metadata=metadata,
            )

            saved_detections.append(
                detection
            )

            session = update_tracking_session(
                detection
            )

            if session is not None:
                sessions.append(session)

        return {
            "detections": saved_detections,
            "sessions": sessions,
        }
