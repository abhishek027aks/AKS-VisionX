from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from alerts.views import AlertViewSet
from api.recording_views import RecordingViewSet, StorageLocationViewSet
from streaming.views import (
    CameraLiveTokenView,
    CameraMJPEGView,
)

from .views import (
    CameraStreamViewSet,
    CameraViewSet,
    DetectionViewSet,
    TrackingPointViewSet,
    TrackingLocationViewSet,
    TrackingCameraVisitViewSet,
    EventViewSet,
    IdentityMatchViewSet,
    PersonProfileViewSet,
    VehicleProfileViewSet,
    admin_test,
    current_user,
    change_password,
    health_check,
    logout,
    LoginTokenObtainPairView,
    operator_test,
    super_admin_test,
    tracking_session_summary,
    viewer_test,
)


router = DefaultRouter()

router.register(r'recordings', RecordingViewSet, basename='recording')
router.register(r'storage-locations', StorageLocationViewSet, basename='storage-location')

router.register(
    "cameras",
    CameraViewSet,
    basename="camera",
)

router.register(
    "streams",
    CameraStreamViewSet,
    basename="camera-stream",
)

router.register(
    "persons",
    PersonProfileViewSet,
    basename="person-profile",
)

router.register(
    "vehicles",
    VehicleProfileViewSet,
    basename="vehicle-profile",
)

router.register(
    "identity-matches",
    IdentityMatchViewSet,
    basename="identity-match",
)

router.register(
    "events",
    EventViewSet,
    basename="event",
)

router.register(
    "alerts",
    AlertViewSet,
    basename="alert",
)

router.register(
    "detections",
    DetectionViewSet,
    basename="detection",
)

router.register(
    "tracking-points",
    TrackingPointViewSet,
    basename="tracking-point",
)

router.register(
    "tracking-locations",
    TrackingLocationViewSet,
    basename="tracking-location",
)

router.register(
    "tracking-camera-visits",
    TrackingCameraVisitViewSet,
    basename="tracking-camera-visit",
)


urlpatterns = [
    path(
        "tracking/<str:tracking_id>/",
        tracking_session_summary,
        name="tracking-session-summary",
    ),

    path(
        "health/",
        health_check,
        name="api-health",
    ),

    path(
        "auth/token/",
        LoginTokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),

    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),

    path(
        "auth/logout/",
        logout,
        name="auth-logout",
    ),

    path(
        "auth/change-password/",
        change_password,
        name="auth-change-password",
    ),

    path(
        "me/",
        current_user,
        name="current-user",
    ),

    path(
        "rbac/viewer-test/",
        viewer_test,
        name="rbac-viewer-test",
    ),

    path(
        "rbac/operator-test/",
        operator_test,
        name="rbac-operator-test",
    ),

    path(
        "rbac/admin-test/",
        admin_test,
        name="rbac-admin-test",
    ),

    path(
        "rbac/super-admin-test/",
        super_admin_test,
        name="rbac-super-admin-test",
    ),

    path(
        "cameras/<int:camera_id>/live-token/",
        CameraLiveTokenView.as_view(),
        name="camera-live-token",
    ),

    path(
        "cameras/<int:camera_id>/live/",
        CameraMJPEGView.as_view(),
        name="camera-live",
    ),

    path(
        "",
        include(router.urls),
    ),
]
