from django.utils import timezone
from events.models import Detection
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from pathlib import Path

from django.http import FileResponse, Http404

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cameras.models import Camera
from recordings.models import Recording
from storage.models import StorageLocation
from storage.storage_service import (
    delete_recording_for_storage_cleanup,
    ensure_storage_directory,
    refresh_storage_size,
)

from .organization import organization_queryset
from .permissions import (
    IsAdminOrSuperAdmin,
    IsOperatorOrAbove,
    IsViewerOrAbove,
)
from .recording_serializers import (
    RecordingSerializer,
    StorageLocationSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recording_ai_detections(request, pk):
    """
    Return AI detections associated with one recording.

    Detection timestamps are matched against the recording's
    camera and recording time window.
    """

    recording = get_object_or_404(
        Recording.objects.select_related("camera"),
        pk=pk,
    )

    user = request.user

    if not user.groups.filter(
        name="Super Admin"
    ).exists():
        if (
<<<<<<< HEAD
            recording.camera.organization_id
=======
            recording.organization_id
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
            != user.organization_id
        ):
            return Response(
                {"detail": "Recording not found."},
                status=404,
            )

    start_time = recording.started_at

    end_time = (
        recording.ended_at
        or timezone.now()
    )

    detections = (
        Detection.objects
        .filter(
            camera_id=recording.camera_id,
            first_seen_at__lte=end_time,
            last_seen_at__gte=start_time,
        )
        .order_by(
            "first_seen_at",
            "id",
        )
    )

    data = []

    for detection in detections:
        timestamp = (
            detection.first_seen_at
            or detection.last_seen_at
        )

        if timestamp is None:
            continue

        data.append(
            {
                "id": detection.id,
                "timestamp": timestamp,
                "object_type": detection.object_type,
                "label": detection.label,
                "confidence": (
                    float(detection.confidence)
                    if detection.confidence is not None
                    else None
                ),
                "tracking_id": detection.tracking_id or "",
                "bbox_x": float(detection.bbox_x or 0),
                "bbox_y": float(detection.bbox_y or 0),
                "bbox_width": float(
                    detection.bbox_width or 0
                ),
                "bbox_height": float(
                    detection.bbox_height or 0
                ),
            }
        )

    return Response(
        {
            "recording_id": recording.id,
            "started_at": recording.started_at,
            "ended_at": recording.ended_at,
            "detections": data,
        }
    )


class RecordingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecordingSerializer

    def get_queryset(self):
        queryset = (
            Recording.objects
            .select_related(
                "camera",
                "stream",
                "storage_location",
            )
            .all()
        )

        user = self.request.user

        if user.groups.filter(
            name="Super Admin"
        ).exists():
            return queryset

        return queryset.filter(
            camera__organization_id=user.organization_id
        )

    def get_permissions(self):
        if self.action in [
            "list",
            "retrieve",
            "download",
        ]:
            return [IsViewerOrAbove()]

        if self.action in [
            "protect",
            "unprotect",
        ]:
            return [IsOperatorOrAbove()]

        if self.action == "destroy":
            return [IsAdminOrSuperAdmin()]

        return [IsAuthenticated()]

    @action(
        detail=True,
        methods=["get"],
        url_path="download",
    )
    def download(self, request, pk=None):
        recording = self.get_object()

        if recording.status == Recording.Status.DELETED:
            raise Http404(
                "Recording is no longer available."
            )

        file_path = Path(recording.file_path)

        if not file_path.is_file():
            raise Http404(
                "Recording file does not exist."
            )

        response = FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=recording.file_name,
        )

        response["Cache-Control"] = (
            "private, no-store"
        )

        return response

    @action(
        detail=True,
        methods=["post"],
        url_path="protect",
    )
    def protect(self, request, pk=None):
        recording = self.get_object()

        reason = str(
            request.data.get(
                "reason",
                "",
            )
        ).strip()

        recording.protected = True
        recording.protection_reason = reason
        recording.save(
            update_fields=[
                "protected",
                "protection_reason",
                "updated_at",
            ]
        )

        return Response(
            RecordingSerializer(
                recording,
                context={
                    "request": request,
                },
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="unprotect",
    )
    def unprotect(self, request, pk=None):
        recording = self.get_object()

        recording.protected = False
        recording.protection_reason = ""
        recording.save(
            update_fields=[
                "protected",
                "protection_reason",
                "updated_at",
            ]
        )

        return Response(
            RecordingSerializer(
                recording,
                context={
                    "request": request,
                },
            ).data
        )

    def destroy(self, request, *args, **kwargs):
        recording = self.get_object()

        if recording.protected:
            return Response(
                {
                    "detail": (
                        "Protected recordings cannot be deleted. "
                        "Unprotect the recording first."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if recording.status == Recording.Status.DELETED:
            return Response(
                {
                    "detail": "Recording is already deleted."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        storage = recording.storage_location

        try:
            if storage is not None:
                delete_recording_for_storage_cleanup(
                    recording,
                    storage,
                )
            else:
                recording.status = (
                    Recording.Status.DELETED
                )
                recording.file_size_bytes = 0
                recording.save(
                    update_fields=[
                        "status",
                        "file_size_bytes",
                        "updated_at",
                    ]
                )

        except Exception as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if storage is not None:
            try:
                refresh_storage_size(storage)
            except Exception:
                pass

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class StorageLocationViewSet(
    viewsets.ModelViewSet
):
    serializer_class = StorageLocationSerializer

    def get_queryset(self):
        return organization_queryset(
            StorageLocation.objects.all(),
            self.request.user,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsViewerOrAbove()]

        return [IsOperatorOrAbove()]

    def perform_create(self, serializer):
        organization = self.request.user.organization

        if organization is None:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "User must belong to an organization "
                        "to create storage settings."
                    )
                }
            )

        storage_location = serializer.save(
            organization=organization
        )
        ensure_storage_directory(storage_location)
        refresh_storage_size(storage_location)

    def perform_update(self, serializer):
        storage_location = serializer.save()
        ensure_storage_directory(storage_location)
        refresh_storage_size(storage_location)

    @action(
        detail=True,
        methods=["post"],
        url_path="refresh",
    )
    def refresh(self, request, pk=None):
        storage_location = self.get_object()
        refresh_storage_size(storage_location)

        return Response(
            self.get_serializer(storage_location).data
        )
