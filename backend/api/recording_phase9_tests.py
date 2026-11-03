from pathlib import Path
import tempfile

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Organization, User
from cameras.models import Camera
from recordings.models import Recording
from storage.models import StorageLocation


class RecordingApiBasicTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Phase 9 Test Organization",
        )

        self.user = User.objects.create_user(
            username="phase9user",
            password="Phase9Password123!",
            organization=self.organization,
        )

        self.storage_root = tempfile.TemporaryDirectory()
        self.storage_path = Path(
            self.storage_root.name
        )

        self.storage = StorageLocation.objects.create(
            organization=self.organization,
            name="Phase 9 Storage",
            path=str(self.storage_path),
            enabled=True,
            rolling_enabled=True,
            max_size_gb=6,
        )

        self.camera = Camera.objects.create(
            organization=self.organization,
            name="Phase 9 Camera",
        )

    def tearDown(self):
        self.storage_root.cleanup()

    def test_recording_serializer_supports_file_state(self):
        from api.recording_serializers import (
            RecordingSerializer,
        )

        path = (
            self.storage_path
            / "phase9.mp4"
        )

        path.write_bytes(
            b"phase9-test"
        )

        recording = Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(path),
            file_name="phase9.mp4",
            status=Recording.Status.COMPLETED,
            started_at="2026-08-22T08:00:00Z",
            file_size_bytes=11,
        )

        data = RecordingSerializer(
            recording
        ).data

        self.assertTrue(
            data["file_exists"]
        )

        self.assertEqual(
            data["camera"],
            self.camera.id,
        )
