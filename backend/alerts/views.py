from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from api.organization import organization_queryset
from api.permissions import (
    IsAdminOrSuperAdmin,
    IsOperatorOrAbove,
    IsViewerOrAbove,
)

from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer

    def get_queryset(self):
        queryset = (
            Alert.objects
            .select_related(
                "organization",
                "camera",
                "event",
            )
            .all()
        )

        return organization_queryset(
            queryset,
            self.request.user,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [
                IsViewerOrAbove,
            ]

        elif self.action in [
            "create",
            "partial_update",
            "update",
        ]:
            permission_classes = [
                IsOperatorOrAbove,
            ]

        elif self.action == "destroy":
            permission_classes = [
                IsAdminOrSuperAdmin,
            ]

        else:
            permission_classes = [
                IsAuthenticated,
            ]

        return [
            permission()
            for permission in permission_classes
        ]

    def perform_create(self, serializer):
        camera = serializer.validated_data.get("camera")
        event = serializer.validated_data.get("event")

        if camera is not None:
            organization = camera.organization
        elif event is not None:
            organization = event.organization
        else:
            organization = self.request.user.organization

        serializer.save(
            organization=organization,
        )
