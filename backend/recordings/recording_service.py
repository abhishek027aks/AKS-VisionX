from pathlib import Path

from django.utils import timezone

from recordings.models import Recording
from storage.models import StorageLocation
from storage.storage_service import (
    ensure_storage_directory,
    enforce_storage_limit,
)


class RecordingServiceError(Exception):
    """Raised when recording cannot be started or written."""


class CameraRecordingService:
    """
    Writes frames from the existing camera-monitor pipeline
    into short MP4 segments.

    The recorder does NOT open a second RTSP connection.
    It receives frames already captured by CameraInferenceService.

    Rolling storage cleanup is executed after a segment is completed.
    """

    def __init__(
        self,
        camera,
        stream=None,
        fps=20.0,
        segment_seconds=300,
    ):
        self.camera = camera
        self.stream = stream
        self.fps = max(float(fps or 20.0), 1.0)
        self.segment_seconds = max(
            int(segment_seconds),
            30,
        )

        self.storage_location = None
        self.writer = None
        self.recording = None

        self.segment_started_at = None
        self.file_path = None
        self.file_name = None

        self.frame_width = None
        self.frame_height = None

    def _get_storage_location(self):
        return (
            StorageLocation.objects
            .filter(
                organization_id=self.camera.organization_id,
                enabled=True,
            )
            .order_by("id")
            .first()
        )

    def _create_writer(self, path, frame):
        import cv2

        height, width = frame.shape[:2]

        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            (width, height),
        )

        if not writer.isOpened():
            writer.release()
            raise RecordingServiceError(
                f"Unable to open recording writer: {path}"
            )

        self.frame_width = width
        self.frame_height = height

        return writer

    def _start_segment(self, frame):
        storage = self._get_storage_location()

        if storage is None:
            return False

        directory = ensure_storage_directory(storage)

        camera_directory = (
            directory / f"camera_{self.camera.id}"
        )
        camera_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        started_at = timezone.now()

        filename = (
            f"camera_{self.camera.id}_"
            f"{started_at.strftime('%Y%m%d_%H%M%S')}.mp4"
        )

        path = camera_directory / filename

        writer = self._create_writer(
            path,
            frame,
        )

        try:
            recording = Recording.objects.create(
                camera=self.camera,
                stream=self.stream,
                storage_location=storage,
                file_path=str(path),
                file_name=filename,
                format=Recording.Format.MP4,
                status=Recording.Status.RECORDING,
                started_at=started_at,
            )
        except Exception:
            writer.release()
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
            raise

        self.storage_location = storage
        self.writer = writer
        self.recording = recording
        self.segment_started_at = started_at
        self.file_path = path
        self.file_name = filename

        return True

    def _finish_segment(self):
        if self.writer is not None:
            self.writer.release()

        if self.recording is None:
            self.writer = None
            self.file_path = None
            self.file_name = None
            self.segment_started_at = None
            return

        ended_at = timezone.now()

        try:
            file_size = (
                self.file_path.stat().st_size
                if self.file_path is not None
                and self.file_path.exists()
                else 0
            )
        except OSError:
            file_size = 0

        duration = 0

        if self.segment_started_at is not None:
            duration = int(
                max(
                    0,
                    (
                        ended_at
                        - self.segment_started_at
                    ).total_seconds(),
                )
            )

        self.recording.status = (
            Recording.Status.COMPLETED
        )
        self.recording.ended_at = ended_at
        self.recording.duration_seconds = duration
        self.recording.file_size_bytes = file_size

        self.recording.save(
            update_fields=[
                "status",
                "ended_at",
                "duration_seconds",
                "file_size_bytes",
                "updated_at",
            ]
        )

        if self.storage_location is not None:
            try:
                enforce_storage_limit(
                    self.storage_location
                )
            except Exception:
                # A storage cleanup failure must not kill
                # the live camera-monitor worker.
                pass

        self.writer = None
        self.recording = None
        self.file_path = None
        self.file_name = None
        self.segment_started_at = None

    def write(self, frame):
        if frame is None:
            return

        if self.writer is None:
            started = self._start_segment(frame)

            if not started:
                return

        self.writer.write(frame)

        if self.segment_started_at is None:
            return

        elapsed = (
            timezone.now()
            - self.segment_started_at
        ).total_seconds()

        if elapsed >= self.segment_seconds:
            self._finish_segment()

    def close(self):
        self._finish_segment()

    def stop(self):
        self.close()
