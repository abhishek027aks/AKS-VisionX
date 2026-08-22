from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization, User
from cameras.models import Camera, CameraStream

from api.permissions import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
)


class CameraInferenceAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="Camera Inference API Organization A",
            slug="camera-inference-api-org-a",
        )

        cls.org_b = Organization.objects.create(
            name="Camera Inference API Organization B",
            slug="camera-inference-api-org-b",
        )

        cls.viewer_group = Group.objects.create(
            name=ROLE_VIEWER,
        )

        cls.operator_group = Group.objects.create(
            name=ROLE_OPERATOR,
        )

        cls.admin_group = Group.objects.create(
            name=ROLE_ADMIN,
        )

        cls.viewer = User.objects.create_user(
            username="camera_inference_viewer",
            password="CameraInferencePass123!",
            is_active=True,
        )
        cls.viewer.organization = cls.org_a
        cls.viewer.save(update_fields=["organization"])
        cls.viewer.groups.add(cls.viewer_group)

        cls.operator = User.objects.create_user(
            username="camera_inference_operator",
            password="CameraInferencePass123!",
            is_active=True,
        )
        cls.operator.organization = cls.org_a
        cls.operator.save(update_fields=["organization"])
        cls.operator.groups.add(cls.operator_group)

        cls.admin = User.objects.create_user(
            username="camera_inference_admin",
            password="CameraInferencePass123!",
            is_active=True,
        )
        cls.admin.organization = cls.org_a
        cls.admin.save(update_fields=["organization"])
        cls.admin.groups.add(cls.admin_group)

        cls.other_viewer = User.objects.create_user(
            username="camera_inference_other_viewer",
            password="CameraInferencePass123!",
            is_active=True,
        )
        cls.other_viewer.organization = cls.org_b
        cls.other_viewer.save(update_fields=["organization"])
        cls.other_viewer.groups.add(cls.viewer_group)

        cls.camera_a = Camera.objects.create(
            organization=cls.org_a,
            created_by=cls.operator,
            name="Inference Camera A",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.50.10",
            enabled=True,
            ai_supported=True,
        )

        cls.camera_b = Camera.objects.create(
            organization=cls.org_b,
            created_by=cls.other_viewer,
            name="Inference Camera B",
            connection_type=Camera.ConnectionType.RTSP,
            host="192.168.60.10",
            enabled=True,
            ai_supported=True,
        )

        cls.stream_a = CameraStream.objects.create(
            camera=cls.camera_a,
            name="Main Stream",
            stream_type=CameraStream.StreamType.MAIN,
            protocol=CameraStream.Protocol.RTSP,
            url="rtsp://192.168.50.10/main",
            enabled=True,
        )

        cls.stream_b = CameraStream.objects.create(
            camera=cls.camera_b,
            name="Main Stream",
            stream_type=CameraStream.StreamType.MAIN,
            protocol=CameraStream.Protocol.RTSP,
            url="rtsp://192.168.60.10/main",
            enabled=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    @patch(
        "api.views.CameraInferenceService"
    )
    def test_operator_can_process_own_camera_frame(
        self,
        inference_class,
    ):
        self.authenticate(self.operator)

        service = inference_class.return_value

        service.connect.return_value = True

        service.process_frame.return_value = {
            "frame": MagicMock(),
            "detections": ["detection-1"],
            "sessions": ["session-1"],
        }

        service.cleanup_stale_tracking.return_value = 0

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {
                "zone": "Entrance",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["status"],
            "processed",
        )

        self.assertEqual(
            response.data["camera_id"],
            self.camera_a.id,
        )

        self.assertEqual(
            response.data["zone"],
            "Entrance",
        )

        self.assertEqual(
            response.data["detection_count"],
            1,
        )

        self.assertEqual(
            response.data["session_count"],
            1,
        )

        self.assertEqual(
            response.data["ended_tracking_sessions"],
            0,
        )

        inference_class.assert_called_once()

        service.process_frame.assert_called_once_with(
            camera=self.camera_a,
            zone="Entrance",
        )

        service.cleanup_stale_tracking.assert_called_once()

    @patch(
        "api.views.CameraInferenceService"
    )
    def test_viewer_cannot_process_camera_frame(
        self,
        inference_class,
    ):
        self.authenticate(self.viewer)

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {
                "zone": "Entrance",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        inference_class.assert_not_called()

    @patch(
        "api.views.CameraInferenceService"
    )
    def test_operator_cannot_process_other_organization_camera(
        self,
        inference_class,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            f"/api/cameras/{self.camera_b.id}/process-frame/",
            {
                "zone": "Parking",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        inference_class.assert_not_called()

    @patch(
        "api.views.CameraInferenceService"
    )
    def test_admin_can_process_own_camera_frame(
        self,
        inference_class,
    ):
        self.authenticate(self.admin)

        service = inference_class.return_value

        service.process_frame.return_value = {
            "frame": MagicMock(),
            "detections": [],
            "sessions": [],
        }

        service.cleanup_stale_tracking.return_value = 0

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["detection_count"],
            0,
        )

        self.assertEqual(
            response.data["session_count"],
            0,
        )

    def test_process_frame_requires_authentication(self):
        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_process_frame_rejects_disabled_camera(self):
        self.authenticate(self.operator)

        self.camera_a.enabled = False
        self.camera_a.save(update_fields=["enabled"])

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "Camera is disabled.",
        )

    def test_process_frame_rejects_camera_without_ai_support(self):
        self.authenticate(self.operator)

        self.camera_a.ai_supported = False
        self.camera_a.save(update_fields=["ai_supported"])

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "AI processing is not supported for this camera.",
        )

    def test_process_frame_requires_enabled_main_stream(self):
        self.authenticate(self.operator)

        self.stream_a.enabled = False
        self.stream_a.save(update_fields=["enabled"])

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "No enabled main camera stream is available.",
        )

    @patch(
        "api.views.CameraInferenceService"
    )
    def test_inference_error_returns_bad_request(
        self,
        inference_class,
    ):
        from ai_engine.camera_inference_service import (
            CameraInferenceError,
        )

        self.authenticate(self.operator)

        service = inference_class.return_value

        service.process_frame.side_effect = (
            CameraInferenceError(
                "Unable to read camera frame."
            )
        )

        response = self.client.post(
            f"/api/cameras/{self.camera_a.id}/process-frame/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "Unable to read camera frame.",
        )
