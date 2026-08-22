from pathlib import Path
import tempfile

from django.test import TestCase
from django.utils import timezone

from accounts.models import Organization
from cameras.models import Camera
from recordings.models import Recording
from storage.models import StorageLocation
from storage.storage_service import (
    StorageServiceError,
    enforce_storage_limit,
)


class StorageRollingCleanupTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Rolling Storage Organization",
        )

        self.storage_root = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.storage_root.name)

        self.storage = StorageLocation.objects.create(
            organization=self.organization,
            name="Rolling Storage",
            path=str(self.storage_path),
            max_size_gb=1,
            rolling_enabled=True,
            enabled=True,
            delete_oldest_unprotected=True,
        )

        self.camera = Camera.objects.create(
            organization=self.organization,
            name="Rolling Storage Camera",
        )

    def tearDown(self):
        self.storage_root.cleanup()

    def create_recording(
        self,
        name,
        size,
        started_at,
        protected=False,
    ):
        file_path = self.storage_path / name
        file_path.write_bytes(b"x" * size)

        return Recording.objects.create(
            camera=self.camera,
            storage_location=self.storage,
            file_path=str(file_path),
            file_name=name,
            status=Recording.Status.COMPLETED,
            started_at=started_at,
            file_size_bytes=size,
            protected=protected,
        )

    def test_under_quota_deletes_nothing(self):
        self.storage.max_size_gb = 1
        self.storage.save()

        recording = self.create_recording(
            "normal.mp4",
            100,
            timezone.now(),
        )

        result = enforce_storage_limit(self.storage)

        recording.refresh_from_db()
        self.storage.refresh_from_db()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["deleted_count"], 0)
        self.assertEqual(result["deleted_recording_ids"], [])
        self.assertFalse(result["remaining_over_quota"])
        self.assertEqual(result["initial_size_bytes"], 100)
        self.assertEqual(result["final_size_bytes"], 100)
        self.assertEqual(
            recording.status,
            Recording.Status.COMPLETED,
        )

    def test_oldest_recording_is_deleted_first(self):
        self.storage.max_size_gb = 0
        self.storage.save()

        now = timezone.now()

        oldest = self.create_recording(
            "oldest.mp4",
            100,
            now - timezone.timedelta(hours=3),
        )

        newest = self.create_recording(
            "newest.mp4",
            100,
            now - timezone.timedelta(hours=1),
        )

        result = enforce_storage_limit(self.storage)

        oldest.refresh_from_db()
        newest.refresh_from_db()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["deleted_recording_ids"],
            [oldest.pk, newest.pk],
        )
        self.assertEqual(result["deleted_count"], 2)

        self.assertEqual(
            oldest.status,
            Recording.Status.DELETED,
        )
        self.assertEqual(
            newest.status,
            Recording.Status.DELETED,
        )

        self.assertFalse(
            (self.storage_path / "oldest.mp4").exists()
        )
        self.assertFalse(
            (self.storage_path / "newest.mp4").exists()
        )

    def test_protected_recording_is_never_deleted(self):
        self.storage.max_size_gb = 0
        self.storage.save()

        protected = self.create_recording(
            "protected.mp4",
            100,
            timezone.now() - timezone.timedelta(hours=3),
            protected=True,
        )

        result = enforce_storage_limit(self.storage)

        protected.refresh_from_db()

        self.assertEqual(
            result["status"],
            "quota_unresolved",
        )
        self.assertEqual(result["deleted_count"], 0)
        self.assertTrue(result["remaining_over_quota"])
        self.assertEqual(
            protected.status,
            Recording.Status.COMPLETED,
        )
        self.assertTrue(
            (self.storage_path / "protected.mp4").exists()
        )

    def test_outside_storage_file_is_not_deleted(self):
        self.storage.max_size_gb = 0
        self.storage.save()

        # This file makes the configured storage exceed quota.
        inside_file = self.storage_path / "inside.mp4"
        inside_file.write_bytes(b"x" * 100)

        outside_file = (
            Path(tempfile.gettempdir())
            / "aks_visionx_outside.mp4"
        )

        outside_file.write_bytes(b"x" * 100)

        try:
            recording = Recording.objects.create(
                camera=self.camera,
                storage_location=self.storage,
                file_path=str(outside_file),
                file_name="outside.mp4",
                status=Recording.Status.COMPLETED,
                started_at=timezone.now(),
                file_size_bytes=100,
                protected=False,
            )

            with self.assertRaises(StorageServiceError):
                enforce_storage_limit(self.storage)

            recording.refresh_from_db()

            self.assertEqual(
                recording.status,
                Recording.Status.COMPLETED,
            )

            self.assertTrue(outside_file.exists())

        finally:
            if outside_file.exists():
                outside_file.unlink()

    def test_disabled_storage_does_not_cleanup(self):
        self.storage.max_size_gb = 0
        self.storage.enabled = False
        self.storage.save()

        recording = self.create_recording(
            "disabled.mp4",
            100,
            timezone.now(),
        )

        result = enforce_storage_limit(self.storage)

        recording.refresh_from_db()

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["deleted_count"], 0)
        self.assertEqual(
            recording.status,
            Recording.Status.COMPLETED,
        )
        self.assertTrue(
            (self.storage_path / "disabled.mp4").exists()
        )

    def test_rolling_disabled_does_not_cleanup(self):
        self.storage.max_size_gb = 0
        self.storage.rolling_enabled = False
        self.storage.save()

        recording = self.create_recording(
            "rolling-disabled.mp4",
            100,
            timezone.now(),
        )

        result = enforce_storage_limit(self.storage)

        recording.refresh_from_db()

        self.assertEqual(
            result["status"],
            "rolling_disabled",
        )
        self.assertEqual(result["deleted_count"], 0)
        self.assertEqual(
            recording.status,
            Recording.Status.COMPLETED,
        )
        self.assertTrue(
            (
                self.storage_path
                / "rolling-disabled.mp4"
            ).exists()
        )
