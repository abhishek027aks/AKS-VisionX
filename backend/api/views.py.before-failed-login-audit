from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .organization import organization_queryset
from .permissions import (
    IsAdminOrSuperAdmin,
    IsOperatorOrAbove,
    IsSuperAdmin,
    IsViewerOrAbove,
)
from audit.models import AuditLog

from .serializers import (
    CameraSerializer,
    CameraStreamSerializer,
    CurrentUserSerializer,
    PersonProfileSerializer,
    VehicleProfileSerializer,
    IdentityMatchSerializer,
    EventSerializer,
    PasswordChangeSerializer,
)


from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import LoginTokenObtainPairSerializer


class LoginTokenObtainPairView(TokenObtainPairView):
    """
    JWT login endpoint with successful-login audit logging.
    """

    serializer_class = LoginTokenObtainPairSerializer
from cameras.models import Camera, CameraStream
from events.models import (
    PersonProfile,
    VehicleProfile,
    IdentityMatch,
    TrackingSession,
    Event,
)
from events.tracking_summary_service import get_tracking_session_summary


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response(
        {
            "status": "ok",
            "service": "AKS VisionX API",
            "version": "1.0.0",
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    return Response(CurrentUserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsViewerOrAbove])
def viewer_test(request):
    return Response(
        {
            "status": "ok",
            "permission": "viewer_or_above",
            "user": request.user.username,
        }
    )


@api_view(["GET"])
@permission_classes([IsOperatorOrAbove])
def operator_test(request):
    return Response(
        {
            "status": "ok",
            "permission": "operator_or_above",
            "user": request.user.username,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminOrSuperAdmin])
def admin_test(request):
    return Response(
        {
            "status": "ok",
            "permission": "admin_or_super_admin",
            "user": request.user.username,
        }
    )


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def super_admin_test(request):
    return Response(
        {
            "status": "ok",
            "permission": "super_admin",
            "user": request.user.username,
        }
    )


class CameraViewSet(viewsets.ModelViewSet):
    serializer_class = CameraSerializer

    def get_queryset(self):
        queryset = (
            Camera.objects
            .select_related("organization", "created_by")
            .prefetch_related("streams")
            .all()
        )

        return organization_queryset(
            queryset,
            self.request.user,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsViewerOrAbove]
        elif self.action in ["create", "partial_update", "update"]:
            permission_classes = [IsOperatorOrAbove]
        elif self.action == "destroy":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]


class CameraStreamViewSet(viewsets.ModelViewSet):
    serializer_class = CameraStreamSerializer

    def get_queryset(self):
        queryset = (
            CameraStream.objects
            .select_related("camera", "camera__organization")
            .all()
        )

        if self.request.user.groups.filter(
            name="Super Admin"
        ).exists():
            return queryset

        return queryset.filter(
            camera__organization_id=self.request.user.organization_id
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsViewerOrAbove]
        elif self.action in ["create", "partial_update", "update"]:
            permission_classes = [IsOperatorOrAbove]
        elif self.action == "destroy":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]


class PersonProfileViewSet(viewsets.ModelViewSet):
    serializer_class = PersonProfileSerializer

    def get_queryset(self):
        queryset = (
            PersonProfile.objects
            .select_related("organization")
            .all()
        )

        return organization_queryset(
            queryset,
            self.request.user,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsViewerOrAbove]
        elif self.action in ["create", "partial_update", "update"]:
            permission_classes = [IsOperatorOrAbove]
        elif self.action == "destroy":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user

        if user.groups.filter(name="Super Admin").exists():
            serializer.save()
            return

        serializer.save(
            organization=user.organization,
        )


class VehicleProfileViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleProfileSerializer

    def get_queryset(self):
        queryset = (
            VehicleProfile.objects
            .select_related("organization")
            .all()
        )

        return organization_queryset(
            queryset,
            self.request.user,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsViewerOrAbove]
        elif self.action in ["create", "partial_update", "update"]:
            permission_classes = [IsOperatorOrAbove]
        elif self.action == "destroy":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user

        if user.groups.filter(name="Super Admin").exists():
            serializer.save()
            return

        serializer.save(
            organization=user.organization,
        )


class IdentityMatchViewSet(viewsets.ModelViewSet):
    serializer_class = IdentityMatchSerializer

    def get_queryset(self):
        queryset = (
            IdentityMatch.objects
            .select_related(
                "organization",
                "tracking_session",
                "person_profile",
                "vehicle_profile",
            )
            .all()
        )

        return organization_queryset(
            queryset,
            self.request.user,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsViewerOrAbove]
        elif self.action in ["create", "partial_update", "update"]:
            permission_classes = [IsOperatorOrAbove]
        elif self.action == "destroy":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user

        if user.groups.filter(name="Super Admin").exists():
            serializer.save()
            return

        serializer.save(
            organization=user.organization,
        )


@api_view(["GET"])
@permission_classes([IsViewerOrAbove])
def tracking_session_summary(request, tracking_id):
    """
    Return the latest tracking session history for a tracking identity.

    A tracking_id can have multiple sessions because a new session is
    created after a previous session has ended.

    Normal users can only access sessions belonging to their organization.
    Super Admin can access sessions across organizations.
    """

    queryset = TrackingSession.objects.select_related(
        "organization",
        "camera",
        "person_profile",
        "vehicle_profile",
    )

    if not request.user.groups.filter(
        name="Super Admin"
    ).exists():
        queryset = queryset.filter(
            organization_id=request.user.organization_id,
        )

    session = (
        queryset
        .filter(tracking_id=tracking_id)
        .order_by("-created_at", "-id")
        .first()
    )

    if session is None:
        from django.http import Http404
        raise Http404

    return Response(
        get_tracking_session_summary(session)
    )


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        queryset = (
            Event.objects
            .select_related(
                "organization",
                "camera",
                "recording",
            )
            .all()
        )

        # Organization isolation first
        queryset = organization_queryset(
            queryset,
            self.request.user,
        )

        params = self.request.query_params

        # Filter by event type
        event_type = params.get("event_type")
        if event_type:
            queryset = queryset.filter(
                event_type=event_type.upper()
            )

        # Filter by event status
        event_status = params.get("status")
        if event_status:
            queryset = queryset.filter(
                status=event_status.upper()
            )

        # Filter by camera
        camera = params.get("camera")
        if camera:
            try:
                queryset = queryset.filter(
                    camera_id=int(camera)
                )
            except (TypeError, ValueError):
                queryset = queryset.none()

        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsViewerOrAbove]

        elif self.action in [
            "create",
            "partial_update",
            "update",
        ]:
            permission_classes = [IsOperatorOrAbove]

        elif self.action == "destroy":
            permission_classes = [IsAdminOrSuperAdmin]

        else:
            permission_classes = [IsAuthenticated]

        return [
            permission()
            for permission in permission_classes
        ]

    def perform_create(self, serializer):
        user = self.request.user

        if user.groups.filter(
            name="Super Admin"
        ).exists():
            serializer.save()
            return

        serializer.save(
            organization=user.organization,
        )

    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change the authenticated user's password.

    Existing refresh tokens are blacklisted after a successful password
    change so previously issued sessions cannot obtain new access tokens.
    """
    serializer = PasswordChangeSerializer(
        data=request.data,
        context={"request": request},
    )

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    user.set_password(serializer.validated_data["new_password"])
    user.save(update_fields=["password"])

    blacklisted = 0

    outstanding_tokens = OutstandingToken._default_manager.filter(
        user=user
    )

    for outstanding in outstanding_tokens:
        try:
            BlacklistedToken._default_manager.get_or_create(
                token=outstanding
            )
            blacklisted += 1
        except Exception:
            continue

    AuditLog.objects.create(
        organization=user.organization,
        user=user,
        action=AuditLog.Action.PASSWORD_CHANGED,
        result=AuditLog.Result.SUCCESS,
        description="User password changed successfully.",
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        metadata={
            "tokens_blacklisted": blacklisted,
        },
    )

    return Response(
        {
            "detail": "Password changed successfully.",
            "refresh_tokens_blacklisted": blacklisted,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Blacklist the supplied refresh token and record the logout event.
    """
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return Response(
            {"detail": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception:
        return Response(
            {"detail": "Invalid or already blacklisted refresh token."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user

    AuditLog.objects.create(
        organization=user.organization,
        user=user,
        action=AuditLog.Action.LOGOUT,
        result=AuditLog.Result.SUCCESS,
        description="User logged out successfully.",
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        metadata={
            "refresh_token_blacklisted": True,
        },
    )

    return Response(
        {"detail": "Logout successful."},
        status=status.HTTP_200_OK,
    )

