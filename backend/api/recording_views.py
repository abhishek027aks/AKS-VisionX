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
