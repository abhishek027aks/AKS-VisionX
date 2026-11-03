from pathlib import Path
import tempfile

from django.test import TestCase
from django.utils import timezone

from accounts.models import Organization
from cameras.models import Camera
from recordings.models import Recording
from storage.models import StorageLocation

from recordings.recording_service import (
    CameraRecordingService,
)


class CameraRecordingServiceTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Recording Test Organization",
        )

        self.storage_root = tempfile.TemporaryDirectory()
        self.storage_path = Path(
            self.storage_root.name
        )

        self.storage = StorageLocation.objects.create(
            organization=self.organization,
            name="Recording Test Storage",
            path=str(self.storage_path),
            enabled=True,
            rolling_enabled=True,
            max_size_gb=6,
            delete_oldest_unprotected=True,
        )

        self.camera = Camera.objects.create(
            organization=self.organization,
            name="Recording Test Camera",
            enabled=True,
        )

    def tearDown(self):
        self.storage_root.cleanup()

    def test_no_storage_does_not_create_recording(self):
        self.storage.delete()

        service = CameraRecordingService(
            self.camera,
            fps=5,
        )

        import numpy as np

        frame = np.zeros(
            (120, 160, 3),
            dtype=np.uint8,
        )

        service.write(frame)

        self.assertEqual(
            Recording.objects.count(),
            0,
        )

        service.close()

    def test_recording_segment_creates_completed_file(self):
        import numpy as np

        frame = np.zeros(
            (120, 160, 3),
            dtype=np.uint8,
        )

        service = CameraRecordingService(
            self.camera,
            fps=5,
            segment_seconds=300,
        )

        service.write(frame)
        service.close()

        self.assertEqual(
            Recording.objects.count(),
            1,
        )

        recording = Recording.objects.first()

        self.assertEqual(
            recording.status,
            Recording.Status.COMPLETED,
        )

        self.assertTrue(
            Path(recording.file_path).exists()
        )

        self.assertGreaterEqual(
            recording.file_size_bytes,
            0,
        )

    def test_recording_stores_camera_reference(self):
        import numpy as np

        frame = np.zeros(
            (120, 160, 3),
            dtype=np.uint8,
        )

        service = CameraRecordingService(
            self.camera,
            fps=5,
        )

        service.write(frame)
        service.close()

        recording = Recording.objects.first()

        self.assertEqual(
            recording.camera_id,
            self.camera.id,
        )

        self.assertEqual(
            recording.storage_location_id,
            self.storage.id,
        )
