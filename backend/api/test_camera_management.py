from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization
from api.permissions import ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER
from cameras.models import Camera, CameraStream
from recordings.models import Recording


User = get_user_model()


class CameraManagementAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Camera Management Organization",
            slug="camera-management-organization",
        )

        self.admin_group = Group.objects.create(name=ROLE_ADMIN)
        self.operator_group = Group.objects.create(name=ROLE_OPERATOR)
        self.viewer_group = Group.objects.create(name=ROLE_VIEWER)

        self.operator = User.objects.create_user(
            username="camera_operator",
            password="CameraPass123!",
            organization=self.organization,
        )
        self.operator.groups.add(self.operator_group)

        self.viewer = User.objects.create_user(
            username="camera_viewer",
            password="CameraPass123!",
            organization=self.organization,
        )
        self.viewer.groups.add(self.viewer_group)

        self.admin = User.objects.create_user(
            username="camera_admin",
            password="CameraPass123!",
            organization=self.organization,
        )
        self.admin.groups.add(self.admin_group)

        self.client = APIClient()
        self.client.defaults["HTTP_HOST"] = "localhost"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def camera_payload(self, **overrides):
        payload = {
            "name": "Front Gate",
            "connection_type": Camera.ConnectionType.RTSP,
            "main_stream_url": "rtsp://192.168.1.50/live",
            "username": "operator",
            "credential_encrypted": "secret-password",
            "description": "Primary gate camera",
            "location": "Front Gate",
            "enabled": True,
            "recording_enabled": True,
            "ai_supported": True,
            "rtsp_supported": True,
        }
        payload.update(overrides)
        return payload

    def create_camera(self):
        camera = Camera.objects.create(
            organization=self.organization,
            created_by=self.operator,
            name="Existing Camera",
            connection_type=Camera.ConnectionType.RTSP,
            username="existing",
            description="Existing description",
            location="Lobby",
            recording_enabled=True,
            ai_supported=True,
        )
        camera.set_credential("old-password")
        camera.save()
        CameraStream.objects.create(
            camera=camera,
            name="Main Stream",
            stream_type=CameraStream.StreamType.MAIN,
            protocol=CameraStream.Protocol.RTSP,
            url="rtsp://192.168.1.51/live",
            enabled=True,
        )
        return camera

    def test_operator_can_create_camera_with_main_stream(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/cameras/",
            self.camera_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Front Gate")
        self.assertNotIn("credential_encrypted", response.data)
        self.assertEqual(
            response.data["main_stream"]["url"],
            "rtsp://192.168.1.50/live",
        )

        camera = Camera.objects.get(id=response.data["id"])
        self.assertEqual(camera.get_credential(), "secret-password")
        self.assertTrue(camera.recording_enabled)

    def test_operator_can_create_local_camera_with_ai_enabled(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/cameras/",
            self.camera_payload(
                name="USB Webcam",
                connection_type=Camera.ConnectionType.LOCAL,
                main_stream_url="local://0",
                rtsp_supported=False,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["main_stream"]["url"], "local://0")
        camera = Camera.objects.get(id=response.data["id"])
        self.assertTrue(camera.ai_supported)
        self.assertEqual(
            camera.streams.get(stream_type=CameraStream.StreamType.MAIN).protocol,
            CameraStream.Protocol.OTHER,
        )

    def test_operator_can_edit_camera_without_replacing_password(self):
        camera = self.create_camera()
        self.authenticate(self.operator)

        response = self.client.put(
            f"/api/cameras/{camera.id}/",
            self.camera_payload(
                name="Updated Camera",
                main_stream_url="rtsp://192.168.1.52/main",
                username="new-user",
                credential_encrypted="",
                recording_enabled=False,
                ai_supported=False,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        camera.refresh_from_db()
        self.assertEqual(camera.name, "Updated Camera")
        self.assertEqual(camera.get_credential(), "old-password")
        self.assertFalse(camera.recording_enabled)
        self.assertFalse(camera.ai_supported)
        self.assertEqual(
            camera.streams.get(
                stream_type=CameraStream.StreamType.MAIN
            ).url,
            "rtsp://192.168.1.52/main",
        )

    def test_invalid_stream_url_is_rejected(self):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/cameras/",
            self.camera_payload(main_stream_url="not-a-url"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("main_stream_url", response.data)

    @patch(
        "api.views.camera_connection_discovery_service.test",
        return_value={
            "success": True,
            "reachable": True,
            "stream_url": "rtsp://192.168.1.50/live",
            "message": "Camera connected successfully.",
        },
    )
    def test_operator_can_test_connection_before_creating_camera(
        self,
        discover_connection,
    ):
        self.authenticate(self.operator)

        response = self.client.post(
            "/api/cameras/test-connection/",
            {
                "camera_type": "ONVIF",
                "host": "192.168.1.50",
                "username": "camera-user",
                "password": "camera-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["stream_url"],
            "rtsp://192.168.1.50/live",
        )
        discover_connection.assert_called_once()

    @patch(
        "api.views.camera_connection_discovery_service.discover_local_cameras",
        return_value={"devices": [{"device_index": 0}], "message": "Found 1."},
    )
    def test_operator_can_discover_local_cameras(self, discover_local):
        self.authenticate(self.operator)

        response = self.client.post("/api/cameras/discover-local/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["devices"], [{"device_index": 0}])
        discover_local.assert_called_once()

    @patch(
        "api.views.camera_connection_discovery_service.discover_onvif_devices",
        return_value={"devices": [{"host": "192.0.2.40"}], "message": "Found 1."},
    )
    def test_operator_can_discover_onvif_cameras(self, discover_onvif):
        self.authenticate(self.operator)

        response = self.client.post("/api/cameras/discover-onvif/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["devices"], [{"host": "192.0.2.40"}])
        discover_onvif.assert_called_once()

    def test_viewer_cannot_discover_local_cameras(self):
        self.authenticate(self.viewer)

        response = self.client.post("/api/cameras/discover-local/")

        self.assertEqual(response.status_code, 403)

    def test_operator_can_delete_camera_without_history(self):
        camera = self.create_camera()
        self.authenticate(self.operator)

        response = self.client.delete(f"/api/cameras/{camera.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Camera.objects.filter(pk=camera.id).exists())

    def test_viewer_cannot_delete_camera(self):
        camera = self.create_camera()
        self.authenticate(self.viewer)

        response = self.client.delete(f"/api/cameras/{camera.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Camera.objects.filter(pk=camera.id).exists())

    @patch("api.views.camera_monitor_manager.is_running", return_value=True)
    @patch("api.views.camera_monitor_manager.start_camera", return_value=True)
    def test_operator_can_start_camera_monitoring(
        self,
        start_camera,
        is_running,
    ):
        camera = self.create_camera()
        self.authenticate(self.operator)

        response = self.client.post(
            f"/api/cameras/{camera.id}/start/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["running"])
        self.assertEqual(response.data["status"], "started")
        start_camera.assert_called_once_with(camera.id)
        is_running.assert_called_once_with(camera.id)

    @patch("cv2.VideoCapture")
    def test_connection_success_returns_stream_metadata(self, video_capture):
        camera = self.create_camera()
        self.authenticate(self.operator)

        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.read.return_value = (True, object())
        capture.get.side_effect = [25.0, 1920.0, 1080.0]
        video_capture.return_value = capture

        response = self.client.post(
            f"/api/cameras/{camera.id}/test-connection/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "connected")
        self.assertEqual(response.data["fps"], 25.0)
        self.assertEqual(response.data["width"], 1920)
        self.assertEqual(response.data["height"], 1080)

    @patch("api.views.CameraStream")
    def test_local_camera_connection_test_opens_device_index(
        self,
        stream_class,
    ):
        camera = self.create_camera()
        self.authenticate(self.operator)

        stream = stream_class.return_value
        stream.read.return_value = object()
        stream.get_properties.return_value = {
            "width": 1280,
            "height": 720,
            "fps": 30,
        }

        response = self.client.post(
            f"/api/cameras/{camera.id}/test-connection/",
            {"stream_url": "local://1"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "connected")
        self.assertEqual(response.data["width"], 1280)
        stream_class.assert_called_once_with(
            source="local://1",
            reconnect_attempts=1,
            reconnect_delay=0,
        )
        stream.connect.assert_called_once()
        stream.release.assert_called_once()

    @patch("cv2.VideoCapture")
    def test_connection_failure_is_reported_without_crash(self, video_capture):
        camera = self.create_camera()
        self.authenticate(self.operator)

        capture = MagicMock()
        capture.isOpened.return_value = False
        video_capture.return_value = capture

        response = self.client.post(
            f"/api/cameras/{camera.id}/test-connection/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "failed")

    def test_status_includes_recording_state(self):
        camera = self.create_camera()
        Recording.objects.create(
            camera=camera,
            stream=camera.streams.first(),
            file_path="E:/AKS_VisionX_Recordings/test.mp4",
            file_name="test.mp4",
            status=Recording.Status.RECORDING,
            started_at=timezone.now() - timedelta(minutes=2),
        )

        self.authenticate(self.viewer)

        response = self.client.get(
            f"/api/cameras/{camera.id}/status/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["recording"])
        self.assertIsNotNone(response.data["recording_id"])
        self.assertTrue(response.data["recording_enabled"])
        self.assertTrue(response.data["ai_supported"])

    def test_viewer_cannot_create_camera(self):
        self.authenticate(self.viewer)

        response = self.client.post(
            "/api/cameras/",
            self.camera_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_delete_camera_with_recordings_disables_not_deletes(self):
        camera = self.create_camera()
        recording = Recording.objects.create(
            camera=camera,
            stream=camera.streams.first(),
            file_path="E:/AKS_VisionX_Recordings/keep.mp4",
            file_name="keep.mp4",
            status=Recording.Status.COMPLETED,
            started_at=timezone.now() - timedelta(minutes=5),
        )

        self.authenticate(self.admin)

        response = self.client.delete(
            f"/api/cameras/{camera.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "disabled")

        camera.refresh_from_db()
        recording.refresh_from_db()

        self.assertFalse(camera.enabled)
        self.assertEqual(recording.camera_id, camera.id)
