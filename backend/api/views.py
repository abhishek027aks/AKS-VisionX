from rest_framework import status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
)
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
    DetectionSerializer,
    TrackingPointSerializer,
    TrackingLocationSerializer,
    TrackingCameraVisitSerializer,
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

from streaming.camera_monitor_manager import CameraMonitorManager, camera_monitor_manager

from ai_engine.camera_inference_service import (
    CameraInferenceError,
    CameraInferenceService,
)

from cameras.models import Camera, CameraStream
from recordings.models import Recording
from events.models import (
    PersonProfile,
    VehicleProfile,
    IdentityMatch,
    Detection,
    TrackingSession,
    TrackingPoint,
    TrackingLocation,
    TrackingCameraVisit,
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

        elif self.action in [
            "create",
            "partial_update",
            "update",
            "process_frame",
            "test_connection",
            "start_monitoring",
            "stop_monitoring",
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

    def destroy(self, request, *args, **kwargs):
        camera = self.get_object()

        if camera.recordings.exists() or camera.events.exists():
            camera_monitor_manager.stop_camera(camera.id)
            camera.enabled = False
            camera.status = Camera.Status.OFFLINE
            camera.save(
                update_fields=[
                    "enabled",
                    "status",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "status": "disabled",
                    "detail": (
                        "Camera has recordings or events, so it "
                        "was disabled instead of deleted."
                    ),
                    "camera_id": camera.id,
                },
                status=status.HTTP_200_OK,
            )

        camera_monitor_manager.stop_camera(camera.id)
        return super().destroy(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        url_path="test-connection",
    )
    def test_connection(self, request, pk=None):
        camera = self.get_object()

        stream_url = request.data.get("stream_url")

        main_stream = (
            camera.streams
            .filter(
                stream_type=CameraStream.StreamType.MAIN,
                enabled=True,
            )
            .first()
        )

        if not stream_url and main_stream is not None:
            stream_url = main_stream.url

        stream_url = str(stream_url or "").strip()

        if not stream_url:
            return Response(
                {
                    "status": "invalid_url",
                    "detail": "A stream URL is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not stream_url.lower().startswith(
            ("rtsp://", "http://", "https://")
        ):
            return Response(
                {
                    "status": "invalid_url",
                    "detail": (
                        "Stream URL must start with rtsp://, "
                        "http://, or https://."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import cv2

            stream_url = CameraMonitorManager._build_authenticated_stream_url(
                camera,
                stream_url,
            )

            capture = cv2.VideoCapture(stream_url)
            capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

            try:
                opened = capture.isOpened()
                ok, frame = capture.read() if opened else (False, None)
                fps = capture.get(cv2.CAP_PROP_FPS) if opened else 0
                width = capture.get(cv2.CAP_PROP_FRAME_WIDTH) if opened else 0
                height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT) if opened else 0
            finally:
                capture.release()

            if not opened:
                return Response(
                    {
                        "status": "failed",
                        "detail": (
                            "Camera stream could not be opened. "
                            "Check URL, network, and credentials."
                        ),
                    },
                    status=status.HTTP_200_OK,
                )

            if not ok or frame is None:
                return Response(
                    {
                        "status": "timeout",
                        "detail": (
                            "Connected to stream but no frame was "
                            "received before timeout."
                        ),
                    },
                    status=status.HTTP_200_OK,
                )

            if main_stream is not None:
                update_fields = ["updated_at"]

                if width:
                    main_stream.width = int(width)
                    update_fields.append("width")

                if height:
                    main_stream.height = int(height)
                    update_fields.append("height")

                if fps:
                    main_stream.fps = round(float(fps), 2)
                    update_fields.append("fps")

                main_stream.save(update_fields=update_fields)

            return Response(
                {
                    "status": "connected",
                    "detail": "Camera stream connected successfully.",
                    "fps": round(float(fps or 0), 2),
                    "width": int(width or 0),
                    "height": int(height or 0),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            message = str(exc).lower()
            connection_status = (
                "authentication_failed"
                if "auth" in message or "401" in message
                else "failed"
            )

            return Response(
                {
                    "status": connection_status,
                    "detail": (
                        "Camera connection test failed. "
                        "Check URL, network, and credentials."
                    ),
                },
                status=status.HTTP_200_OK,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="start",
    )
    def start_monitoring(self, request, pk=None):
        camera = self.get_object()

        if not camera.enabled:
            return Response(
                {"detail": "Camera is disabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        started = camera_monitor_manager.start_camera(camera.id)

        return Response(
            {
                "status": (
                    "started"
                    if started
                    else "already_running"
                ),
                "camera_id": camera.id,
                "running": camera_monitor_manager.is_running(
                    camera.id
                ),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="stop",
    )
    def stop_monitoring(self, request, pk=None):
        camera = self.get_object()

        stopped = camera_monitor_manager.stop_camera(
            camera.id
        )

        return Response(
            {
                "status": (
                    "stopping"
                    if stopped
                    else "not_running"
                ),
                "camera_id": camera.id,
                "running": camera_monitor_manager.is_running(
                    camera.id
                ),
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="status",
    )
    def monitoring_status(self, request, pk=None):
        camera = self.get_object()

        monitor_status = camera_monitor_manager.get_status(
            camera.id
        )

        camera.refresh_from_db()

        active_recording = (
            Recording.objects
            .filter(
                camera=camera,
                status=Recording.Status.RECORDING,
            )
            .order_by("-started_at", "-id")
            .first()
        )

        main_stream = (
            camera.streams
            .filter(
                stream_type=CameraStream.StreamType.MAIN,
                enabled=True,
            )
            .first()
        )

        return Response(
            {
                "camera_id": camera.id,
                "name": camera.name,
                "running": monitor_status["running"],
                "status": camera.status,
                "last_seen": camera.last_seen,
                "enabled": camera.enabled,
                "recording": active_recording is not None,
                "recording_id": (
                    active_recording.id
                    if active_recording is not None
                    else None
                ),
                "recording_started_at": (
                    active_recording.started_at
                    if active_recording is not None
                    else None
                ),
                "ai_supported": camera.ai_supported,
                "recording_enabled": camera.recording_enabled,
                "fps": (
                    main_stream.fps
                    if main_stream is not None
                    else None
                ),
                "width": (
                    main_stream.width
                    if main_stream is not None
                    else None
                ),
                "height": (
                    main_stream.height
                    if main_stream is not None
                    else None
                ),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="process-frame",
    )
    def process_frame(self, request, pk=None):
        """
        Process one frame from the camera through the
        camera streaming and AI inference pipeline.
        """

        camera = self.get_object()

        # ----------------------------------------------------
        # Camera state validation
        # ----------------------------------------------------

        if not camera.enabled:
            return Response(
                {
                    "detail": "Camera is disabled.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not camera.ai_supported:
            return Response(
                {
                    "detail": (
                        "AI processing is not supported "
                        "for this camera."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Main stream validation
        # ----------------------------------------------------

        main_stream = (
            camera.streams
            .filter(
                stream_type=CameraStream.StreamType.MAIN,
                enabled=True,
            )
            .first()
        )

        if main_stream is None:
            return Response(
                {
                    "detail": (
                        "No enabled main camera "
                        "stream is available."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Optional request data
        # ----------------------------------------------------

        zone = request.data.get(
            "zone",
            "",
        )

        # ----------------------------------------------------
        # Camera AI service
        # ----------------------------------------------------

        stream_url = CameraMonitorManager._build_authenticated_stream_url(
            camera,
            main_stream.url,
        )

        service = CameraInferenceService(
            source=stream_url,
        )

        try:
            service.connect()

            result = service.process_frame(
                camera=camera,
                zone=zone,
            )

            ended_tracking_sessions = (
                service.cleanup_stale_tracking()
            )

        except CameraInferenceError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        detections = result.get(
            "detections",
            [],
        )

        sessions = result.get(
            "sessions",
            [],
        )

        return Response(
            {
                "status": "processed",
                "camera_id": camera.id,
                "zone": zone,
                "detection_count": len(detections),
                "session_count": len(sessions),
                "ended_tracking_sessions": (
                    ended_tracking_sessions
                ),
            },
            status=status.HTTP_200_OK,
        )


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
        serializer.save(
            organization=self.request.user.organization,
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
        serializer.save(
            organization=self.request.user.organization,
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
        tracking_session = serializer.validated_data[
            "tracking_session"
        ]

        serializer.save(
            organization=tracking_session.organization,
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
        camera = serializer.validated_data["camera"]

        serializer.save(
            organization=camera.organization,
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


class DetectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DetectionSerializer

    def get_queryset(self):
        queryset = (
            Detection.objects
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
        return [IsViewerOrAbove()]


class TrackingPointViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackingPointSerializer

    def get_queryset(self):
        queryset = (
            TrackingPoint.objects
            .select_related(
                "tracking_session",
                "camera",
                "tracking_session__organization",
            )
            .all()
        )

        if self.request.user.groups.filter(
            name="Super Admin"
        ).exists():
            return queryset

        return queryset.filter(
            tracking_session__organization_id=(
                self.request.user.organization_id
            )
        )

    def get_permissions(self):
        return [IsViewerOrAbove()]


class TrackingLocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackingLocationSerializer

    def get_queryset(self):
        queryset = (
            TrackingLocation.objects
            .select_related(
                "tracking_session",
                "camera",
                "tracking_session__organization",
            )
            .all()
        )

        if self.request.user.groups.filter(
            name="Super Admin"
        ).exists():
            return queryset

        return queryset.filter(
            tracking_session__organization_id=(
                self.request.user.organization_id
            )
        )

    def get_permissions(self):
        return [IsViewerOrAbove()]


class TrackingCameraVisitViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackingCameraVisitSerializer

    def get_queryset(self):
        queryset = (
            TrackingCameraVisit.objects
            .select_related(
                "tracking_session",
                "camera",
                "tracking_session__organization",
            )
            .all()
        )

        if self.request.user.groups.filter(
            name="Super Admin"
        ).exists():
            return queryset

        return queryset.filter(
            tracking_session__organization_id=(
                self.request.user.organization_id
            )
        )

    def get_permissions(self):
        return [IsViewerOrAbove()]
