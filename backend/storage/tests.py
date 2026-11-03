import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Organization
from cameras.models import Camera
from recordings.models import Recording
from storage.models import StorageLocation
from storage.storage_service import (
    StorageServiceError,
    calculate_directory_size,
    delete_recording_file,
    ensure_storage_directory,
    find_oldest_unprotected_recording,
    get_storage_path,
    max_size_bytes,
    refresh_storage_size,
)


class StorageServiceTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Storage Test Organization",
        )

        self.storage_root = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.storage_root.name)

        self.storage = StorageLocation.objects.create(
            organization=self.organization,
            name="Test Storage",
            path=str(self.storage_path),
            max_size_gb=6,
        )

        self.camera = Camera.objects.create(
            organization=self.organization,
            name="Storage Test Camera",
        )

    def tearDown(self):
        self.storage_root.cleanup()

    def test_get_storage_path_requires_absolute_path(self):
        self.storage.path = "relative/storage/path"

        with self.assertRaises(StorageServiceError):
            get_storage_path(self.storage)

    def test_ensure_storage_directory_creates_directory(self):
        new_path = self.storage_path / "recordings"

        self.storage.path = str(new_path)

        result = ensure_storage_directory(self.storage)

        self.assertEqual(result, new_path)
        self.assertTrue(new_path.exists())
        self.assertTrue(new_path.is_dir())

    def test_calculate_directory_size(self):
        first_file = self.storage_path / "one.bin"
        second_file = self.storage_path / "two.bin"

        first_file.write_bytes(b"a" * 100)
        second_file.write_bytes(b"b" * 250)

        self.assertEqual(
            calculate_directory_size(self.storage_path),
            350,
        )

    def test_refresh_storage_size_updates_database(self):
        recording_file = self.storage_path / "recording.mp4"
        recording_file.write_bytes(b"x" * 512)

        size = refresh_storage_size(self.storage)

        self.storage.refresh_from_db()

        self.assertEqual(size, 512)
        self.assertEqual(
            self.storage.current_size_bytes,
            512,
        )

    def test_max_size_bytes(self):
        expected = 6 * 1024 * 1024 * 1024

        self.assertEqual(
            max_size_bytes(self.storage),
            expected,
        )

    def test_find_oldest_unprotected_recording(self):
        now = timezone.now()

        oldest = Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(self.storage_path / "oldest.mp4"),
            file_name="oldest.mp4",
            status=Recording.Status.COMPLETED,
            started_at=now - timedelta(hours=3),
            file_size_bytes=100,
            protected=False,
        )

        newest = Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(self.storage_path / "newest.mp4"),
            file_name="newest.mp4",
            status=Recording.Status.COMPLETED,
            started_at=now - timedelta(hours=1),
            file_size_bytes=200,
            protected=False,
        )

        result = find_oldest_unprotected_recording(
            self.storage
        )

        self.assertEqual(result, oldest)
        self.assertNotEqual(result, newest)

    def test_protected_recording_is_not_selected(self):
        now = timezone.now()

        Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(self.storage_path / "protected.mp4"),
            file_name="protected.mp4",
            status=Recording.Status.COMPLETED,
            started_at=now - timedelta(hours=3),
            file_size_bytes=100,
            protected=True,
        )

        result = find_oldest_unprotected_recording(
            self.storage
        )

        self.assertIsNone(result)

    def test_delete_recording_file(self):
        recording_file = self.storage_path / "delete-me.mp4"
        recording_file.write_bytes(b"recording-data")

        recording = Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(recording_file),
            file_name="delete-me.mp4",
            status=Recording.Status.COMPLETED,
            started_at=timezone.now(),
            file_size_bytes=14,
            protected=False,
        )

        result = delete_recording_file(recording)

        recording.refresh_from_db()

        self.assertEqual(result.pk, recording.pk)
        self.assertFalse(recording_file.exists())
        self.assertEqual(
            recording.status,
            Recording.Status.DELETED,
        )
        self.assertEqual(
            recording.file_size_bytes,
            0,
        )

    def test_delete_missing_file_marks_recording_deleted(self):
        recording_file = self.storage_path / "missing.mp4"

        recording = Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(recording_file),
            file_name="missing.mp4",
            status=Recording.Status.COMPLETED,
            started_at=timezone.now(),
            file_size_bytes=500,
            protected=False,
        )

        delete_recording_file(recording)

        recording.refresh_from_db()

        self.assertEqual(
            recording.status,
            Recording.Status.DELETED,
        )
        self.assertEqual(
            recording.file_size_bytes,
            0,
        )
