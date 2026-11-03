from decimal import Decimal
from unittest.mock import patch

import numpy as np

from django.test import TestCase

from cameras.models import Camera
from events.models import Detection, TrackingSession

from ai_engine.inference_service import (
    AIInferenceError,
    AIInferenceService,
)


class AIInferenceServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        from accounts.models import Organization

        cls.organization = Organization.objects.create(
            name="AI Inference Test Organization",
            slug="ai-inference-test-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="AI Inference Test Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

    @patch("ai_engine.inference_service.YOLODetectionService")
    def test_process_frame_creates_detection_and_tracking_session(
        self,
        detector_class,
    ):
        detector = detector_class.return_value

        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8,
        )

        detector.infer.return_value = [
            {
                "object_type": "PERSON",
                "label": "person",
                "confidence": Decimal("0.91"),
                "tracking_id": "7",
                "bbox_x": Decimal("0.100000"),
                "bbox_y": Decimal("0.100000"),
                "bbox_width": Decimal("0.400000"),
                "bbox_height": Decimal("0.400000"),
                "metadata": {
                    "model": "test-model.pt",
                },
            }
        ]

        service = AIInferenceService(
            model_path="test-model.pt",
        )

        result = service.process_frame(
            camera=self.camera,
            frame=frame,
            zone="Zone A",
        )

        detector.infer.assert_called_once_with(frame)

        self.assertEqual(
            len(result["detections"]),
            1,
        )

        detection = result["detections"][0]

        self.assertIsInstance(
            detection,
            Detection,
        )

        self.assertEqual(
            detection.organization,
            self.organization,
        )

        self.assertEqual(
            detection.camera,
            self.camera,
        )

        self.assertEqual(
            detection.object_type,
            "PERSON",
        )

        self.assertEqual(
            detection.label,
            "person",
        )

        self.assertEqual(
            detection.confidence,
            Decimal("0.91"),
        )

        self.assertEqual(
            detection.tracking_id,
            "7",
        )

        self.assertEqual(
            detection.bbox_x,
            Decimal("0.100000"),
        )

        self.assertEqual(
            detection.bbox_y,
            Decimal("0.100000"),
        )

        self.assertEqual(
            detection.bbox_width,
            Decimal("0.400000"),
        )

        self.assertEqual(
            detection.bbox_height,
            Decimal("0.400000"),
        )

        self.assertEqual(
            detection.metadata["model"],
            "test-model.pt",
        )

        self.assertEqual(
            detection.metadata["zone"],
            "Zone A",
        )

        self.assertEqual(
            Detection.objects.count(),
            1,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            1,
        )

        session = TrackingSession.objects.first()

        self.assertEqual(
            session.organization,
            self.organization,
        )

        self.assertEqual(
            session.camera,
            self.camera,
        )

        self.assertEqual(
            session.object_type,
            "PERSON",
        )

        self.assertEqual(
            session.tracking_id,
            "7",
        )

        self.assertEqual(
            session.label,
            "person",
        )

        self.assertEqual(
            session.total_detections,
            1,
        )

        self.assertEqual(
            len(result["sessions"]),
            1,
        )

        self.assertEqual(
            result["sessions"][0],
            session,
        )

    @patch("ai_engine.inference_service.YOLODetectionService")
    def test_process_frame_without_tracking_id_does_not_create_session(
        self,
        detector_class,
    ):
        detector = detector_class.return_value

        detector.infer.return_value = [
            {
                "object_type": "PERSON",
                "label": "person",
                "confidence": Decimal("0.80"),
                "tracking_id": "",
                "bbox_x": Decimal("0.100000"),
                "bbox_y": Decimal("0.100000"),
                "bbox_width": Decimal("0.200000"),
                "bbox_height": Decimal("0.300000"),
                "metadata": {},
            }
        ]

        service = AIInferenceService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        result = service.process_frame(
            camera=self.camera,
            frame=frame,
        )

        self.assertEqual(
            len(result["detections"]),
            1,
        )

        self.assertEqual(
            result["sessions"],
            [],
        )

        self.assertEqual(
            Detection.objects.count(),
            1,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            0,
        )

    @patch("ai_engine.inference_service.YOLODetectionService")
    def test_process_frame_multiple_detections(
        self,
        detector_class,
    ):
        detector = detector_class.return_value

        detector.infer.return_value = [
            {
                "object_type": "PERSON",
                "label": "person",
                "confidence": Decimal("0.90"),
                "tracking_id": "1",
                "bbox_x": Decimal("0.100000"),
                "bbox_y": Decimal("0.100000"),
                "bbox_width": Decimal("0.200000"),
                "bbox_height": Decimal("0.300000"),
                "metadata": {},
            },
            {
                "object_type": "VEHICLE",
                "label": "car",
                "confidence": Decimal("0.85"),
                "tracking_id": "2",
                "bbox_x": Decimal("0.500000"),
                "bbox_y": Decimal("0.200000"),
                "bbox_width": Decimal("0.300000"),
                "bbox_height": Decimal("0.400000"),
                "metadata": {},
            },
        ]

        service = AIInferenceService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        result = service.process_frame(
            camera=self.camera,
            frame=frame,
        )

        self.assertEqual(
            len(result["detections"]),
            2,
        )

        self.assertEqual(
            Detection.objects.count(),
            2,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            2,
        )

        self.assertEqual(
            set(
                Detection.objects.values_list(
                    "tracking_id",
                    flat=True,
                )
            ),
            {"1", "2"},
        )

    @patch("ai_engine.inference_service.YOLODetectionService")
    def test_process_frame_returns_empty_for_no_detections(
        self,
        detector_class,
    ):
        detector = detector_class.return_value
        detector.infer.return_value = []

        service = AIInferenceService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        result = service.process_frame(
            camera=self.camera,
            frame=frame,
        )

        self.assertEqual(
            result["detections"],
            [],
        )

        self.assertEqual(
            result["sessions"],
            [],
        )

        self.assertEqual(
            Detection.objects.count(),
            0,
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            0,
        )

    @patch("ai_engine.inference_service.YOLODetectionService")
    def test_process_frame_wraps_detector_error(
        self,
        detector_class,
    ):
        detector = detector_class.return_value

        detector.infer.side_effect = RuntimeError(
            "YOLO inference failed"
        )

        service = AIInferenceService(
            model_path="test-model.pt",
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        with self.assertRaises(
            AIInferenceError
        ):
            service.process_frame(
                camera=self.camera,
                frame=frame,
            )

        self.assertEqual(
            Detection.objects.count(),
            0,
        )

    def test_process_frame_requires_camera(self):
        service = AIInferenceService.__new__(
            AIInferenceService
        )

        frame = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        with self.assertRaises(
            AIInferenceError
        ):
            service.process_frame(
                camera=None,
                frame=frame,
            )

    def test_process_frame_requires_frame(self):
        service = AIInferenceService.__new__(
            AIInferenceService
        )

        with self.assertRaises(
            AIInferenceError
        ):
            service.process_frame(
                camera=self.camera,
                frame=None,
            )

    def test_real_yolo_process_frame_persists_detection_pipeline(
        self,
    ):
        import os
        import cv2

        model_path = r"E:\AKS VisionX\yolo11n.pt"

        image_path = (
            r"E:\AKS VisionX\.venv-ai"
            r"\Lib\site-packages\ultralytics"
            r"\assets\bus.jpg"
        )

        if not os.path.exists(model_path):
            self.skipTest(
                f"YOLO model not found: {model_path}"
            )

        if not os.path.exists(image_path):
            self.skipTest(
                f"Test image not found: {image_path}"
            )

        frame = cv2.imread(image_path)

        self.assertIsNotNone(frame)

        service = AIInferenceService(
            model_path=model_path,
            tracker="bytetrack.yaml",
            confidence=0.25,
        )

        result = service.process_frame(
            camera=self.camera,
            frame=frame,
            zone="Real YOLO Test Zone",
        )

        detections = result["detections"]
        sessions = result["sessions"]

        self.assertGreaterEqual(
            len(detections),
            1,
        )

        self.assertGreaterEqual(
            len(sessions),
            1,
        )

        self.assertEqual(
            Detection.objects.count(),
            len(detections),
        )

        self.assertEqual(
            TrackingSession.objects.count(),
            len(sessions),
        )

        for detection in detections:
            self.assertEqual(
                detection.organization,
                self.organization,
            )

            self.assertEqual(
                detection.camera,
                self.camera,
            )

            self.assertTrue(
                detection.label
            )

            self.assertIsNotNone(
                detection.confidence
            )

            self.assertGreaterEqual(
                detection.confidence,
                Decimal("0.25"),
            )

            self.assertEqual(
                detection.status,
                Detection.DetectionStatus.ACTIVE,
            )

            self.assertEqual(
                detection.metadata.get("zone"),
                "Real YOLO Test Zone",
            )

            self.assertIsNotNone(
                detection.bbox_x
            )

            self.assertIsNotNone(
                detection.bbox_y
            )

            self.assertIsNotNone(
                detection.bbox_width
            )

            self.assertIsNotNone(
                detection.bbox_height
            )

        for session in sessions:
            self.assertEqual(
                session.organization,
                self.organization,
            )

            self.assertEqual(
                session.camera,
                self.camera,
            )

            self.assertEqual(
                session.status,
                TrackingSession.Status.ACTIVE,
            )

            self.assertGreater(
                session.total_detections,
                0,
            )
