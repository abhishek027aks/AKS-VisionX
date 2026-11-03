from pathlib import Path

from django.db import transaction

from recordings.models import Recording


class StorageServiceError(Exception):
    """Base exception for storage service errors."""


def get_storage_path(storage_location):
    path = Path(storage_location.path).expanduser()

    if not path.is_absolute():
        raise StorageServiceError(
            "Storage location path must be absolute."
        )

    return path


def ensure_storage_directory(storage_location):
    path = get_storage_path(storage_location)

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StorageServiceError(
            f"Unable to create storage directory: {exc}"
        ) from exc

    if not path.is_dir():
        raise StorageServiceError(
            "Configured storage path is not a directory."
        )

    return path


def calculate_directory_size(path):
    path = Path(path)

    if not path.exists():
        return 0

    if not path.is_dir():
        raise StorageServiceError(
            "Storage path is not a directory."
        )

    total = 0

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            total += file_path.stat().st_size
        except OSError:
            continue

    return total


@transaction.atomic
def refresh_storage_size(storage_location):
    path = ensure_storage_directory(storage_location)
    size = calculate_directory_size(path)

    storage_location.current_size_bytes = size
    storage_location.save(
        update_fields=[
            "current_size_bytes",
            "updated_at",
        ]
    )

    return size


def max_size_bytes(storage_location):
    return int(
        float(storage_location.max_size_gb)
        * 1024
        * 1024
        * 1024
    )


def find_oldest_unprotected_recording(storage_location):
    return (
        Recording.objects
        .filter(
            storage_location=storage_location,
            protected=False,
            status=Recording.Status.COMPLETED,
        )
        .order_by("started_at", "id")
        .first()
    )


def delete_recording_file(recording):
    file_path = Path(recording.file_path)

    try:
        if file_path.exists():
            if not file_path.is_file():
                raise StorageServiceError(
                    "Recording file path is not a regular file."
                )

            file_path.unlink()
    except OSError as exc:
        raise StorageServiceError(
            f"Unable to delete recording file: {exc}"
        ) from exc

    recording.status = Recording.Status.DELETED
    recording.file_size_bytes = 0
    recording.save(
        update_fields=[
            "status",
            "file_size_bytes",
            "updated_at",
        ]
    )

    return recording


def is_path_inside_storage(storage_location, file_path):
    storage_path = get_storage_path(storage_location).resolve()
    target_path = Path(file_path).expanduser().resolve()

    try:
        target_path.relative_to(storage_path)
    except ValueError:
        return False

    return True


def delete_recording_for_storage_cleanup(
    recording,
    storage_location,
):
    if recording.storage_location_id != storage_location.id:
        raise StorageServiceError(
            "Recording does not belong to the supplied storage location."
        )

    if recording.protected:
        raise StorageServiceError(
            "Protected recordings cannot be automatically deleted."
        )

    if recording.status != Recording.Status.COMPLETED:
        raise StorageServiceError(
            "Only completed recordings can be automatically deleted."
        )

    if not is_path_inside_storage(
        storage_location,
        recording.file_path,
    ):
        raise StorageServiceError(
            "Recording file is outside the configured storage directory."
        )

    return delete_recording_file(recording)


@transaction.atomic
def enforce_storage_limit(storage_location):
    """
    Delete oldest completed, unprotected recordings until the
    configured rolling-storage quota is satisfied.
    """
    quota = max_size_bytes(storage_location)

    if not storage_location.enabled:
        return {
            "status": "disabled",
            "initial_size_bytes": storage_location.current_size_bytes,
            "final_size_bytes": storage_location.current_size_bytes,
            "max_size_bytes": quota,
            "deleted_count": 0,
            "deleted_recording_ids": [],
            "remaining_over_quota": False,
        }

    if not storage_location.rolling_enabled:
        return {
            "status": "rolling_disabled",
            "initial_size_bytes": storage_location.current_size_bytes,
            "final_size_bytes": storage_location.current_size_bytes,
            "max_size_bytes": quota,
            "deleted_count": 0,
            "deleted_recording_ids": [],
            "remaining_over_quota": False,
        }

    storage_path = ensure_storage_directory(storage_location)

    initial_size = calculate_directory_size(storage_path)

    storage_location.current_size_bytes = initial_size
    storage_location.save(
        update_fields=[
            "current_size_bytes",
            "updated_at",
        ]
    )

    current_size = initial_size
    deleted_ids = []

    while current_size > quota:
        recording = find_oldest_unprotected_recording(
            storage_location
        )

        if recording is None:
            break

        delete_recording_for_storage_cleanup(
            recording,
            storage_location,
        )

        deleted_ids.append(recording.pk)

        current_size = calculate_directory_size(
            storage_path
        )

        storage_location.current_size_bytes = current_size
        storage_location.save(
            update_fields=[
                "current_size_bytes",
                "updated_at",
            ]
        )

    final_size = current_size

    return {
        "status": (
            "completed"
            if final_size <= quota
            else "quota_unresolved"
        ),
        "initial_size_bytes": initial_size,
        "final_size_bytes": final_size,
        "max_size_bytes": quota,
        "deleted_count": len(deleted_ids),
        "deleted_recording_ids": deleted_ids,
        "remaining_over_quota": final_size > quota,
    }
