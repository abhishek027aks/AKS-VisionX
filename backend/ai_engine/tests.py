from unittest.mock import MagicMock, patch

import numpy as np
<<<<<<< HEAD
from unittest.mock import patch
=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

from django.test import TestCase

from cameras.models import Camera

from ai_engine.camera_inference_service import (
    CameraInferenceError,
    CameraInferenceService,
)


class CameraInferenceServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        from accounts.models import Organization

        cls.organization = Organization.objects.create(
            name="Camera AI Test Organization",
            slug="camera-ai-test-organization",
        )

        cls.camera = Camera.objects.create(
            organization=cls.organization,
            name="Camera AI Test Camera",
            connection_type=Camera.ConnectionType.LOCAL,
        )

    @patch(
        "ai_engine.camera_inference_service.AIInferenceService"
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_process_frame_reads_frame_and_runs_ai(
        self,
        stream_class,
        ai_service_class,
    ):
        stream = stream_class.return_value
        ai_service = ai_service_class.return_value

        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8,
        )

        stream.read.return_value = frame

        ai_service.process_frame.return_value = {
            "detections": ["detection-1"],
            "sessions": ["session-1"],
        }

        service = CameraInferenceService(
            source=0,
            model_path="test-model.pt",
        )

        result = service.process_frame(
            camera=self.camera,
            zone="Zone A",
        )

        stream.read.assert_called_once()
        ai_service.process_frame.assert_called_once()

        call_kwargs = (
            ai_service.process_frame.call_args.kwargs
        )

        self.assertEqual(
            call_kwargs["camera"],
            self.camera,
        )

        self.assertIs(
            call_kwargs["frame"],
            frame,
        )

        self.assertEqual(
            call_kwargs["zone"],
            "Zone A",
        )

        self.assertEqual(
            result["frame"].shape,
            (480, 640, 3),
        )

        self.assertEqual(
            result["detections"],
            ["detection-1"],
        )

        self.assertEqual(
            result["sessions"],
            ["session-1"],
        )

<<<<<<< HEAD
        ai_service_class.assert_called_once_with(
            model_path="test-model.pt",
            tracker="bytetrack.yaml",
            confidence=0.25,
        )

=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
    @patch(
        "ai_engine.camera_inference_service.AIInferenceService"
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_start_processes_requested_number_of_frames(
        self,
        stream_class,
        ai_service_class,
    ):
        stream = stream_class.return_value
        ai_service = ai_service_class.return_value

        frame = np.zeros(
            (480, 640, 3),
            dtype=np.uint8,
        )

        stream.read.return_value = frame

        ai_service.process_frame.return_value = {
            "detections": [],
            "sessions": [],
        }

        service = CameraInferenceService(
            source=0,
            model_path="test-model.pt",
        )

        processed = service.start(
            camera=self.camera,
            zone="Zone B",
            max_frames=3,
        )

        stream.connect.assert_called_once()

        self.assertEqual(
            processed,
            3,
        )

        self.assertEqual(
            stream.read.call_count,
            3,
        )

        self.assertEqual(
            ai_service.process_frame.call_count,
            3,
        )

        stream.release.assert_called_once()

        self.assertFalse(
            service.running
        )

    @patch(
        "ai_engine.camera_inference_service.AIInferenceService"
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_stop_releases_camera_stream(
        self,
        stream_class,
        ai_service_class,
    ):
        stream = stream_class.return_value

        service = CameraInferenceService(
            source=0,
            model_path="test-model.pt",
        )

        service.running = True

        service.stop()

        self.assertFalse(
            service.running
        )

        stream.release.assert_called_once()

<<<<<<< HEAD
        ai_service_class.assert_not_called()

    @patch(
        "ai_engine.camera_inference_service.AIInferenceService",
        side_effect=RuntimeError("model missing"),
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_stream_connect_does_not_require_ai_model(
        self,
        stream_class,
        ai_service_class,
    ):
        service = CameraInferenceService(source=0)

        self.assertTrue(service.connect())
        service.stop()

        stream_class.return_value.connect.assert_called_once()
        ai_service_class.assert_not_called()

    @patch(
        "ai_engine.camera_inference_service.AIInferenceService",
        side_effect=RuntimeError("model missing"),
    )
    @patch(
        "ai_engine.camera_inference_service.CameraStream"
    )
    def test_failed_ai_model_load_does_not_repeat_for_each_frame(
        self,
        stream_class,
        ai_service_class,
    ):
        service = CameraInferenceService(source=0)
        frame = np.zeros((32, 32, 3), dtype=np.uint8)

        for _ in range(2):
            with self.assertRaises(CameraInferenceError):
                service.process_frame(
                    camera=self.camera,
                    frame=frame,
                )

        ai_service_class.assert_called_once()
=======
        ai_service_class.assert_called_once_with(
            model_path="test-model.pt",
            tracker="bytetrack.yaml",
            confidence=0.25,
        )
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

    def test_process_frame_requires_camera(self):
        service = CameraInferenceService.__new__(
            CameraInferenceService
        )

        with self.assertRaises(
            CameraInferenceError
        ):
            service.process_frame(
                camera=None
            )
