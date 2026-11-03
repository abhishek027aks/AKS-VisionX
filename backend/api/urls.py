from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from alerts.views import AlertViewSet
from api.recording_views import RecordingViewSet, StorageLocationViewSet, recording_ai_detections
from streaming.views import (
    CameraLiveTokenView,
    camera_mjpeg_view,
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
    dashboard_summary,
    LoginTokenObtainPairView,
    operator_test,
    super_admin_test,
    tracking_session_summary,
<<<<<<< HEAD
    tracking_analytics,
    viewer_test,
)
from .auth_views import google_auth, google_auth_config, register
=======
    viewer_test,
)
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d


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
        "recordings/<int:pk>/ai-detections/",
        recording_ai_detections,
        name="recording-ai-detections",
    ),

    path(
        "dashboard/summary/",
        dashboard_summary,
        name="dashboard-summary",
    ),

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
<<<<<<< HEAD
        "analytics/tracking/",
        tracking_analytics,
        name="tracking-analytics",
    ),

    path(
=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
        "auth/token/",
        LoginTokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),

    path(
<<<<<<< HEAD
        "auth/register/",
        register,
        name="auth-register",
    ),

    path(
        "auth/google/",
        google_auth,
        name="auth-google",
    ),

    path(
        "auth/google/config/",
        google_auth_config,
        name="auth-google-config",
    ),

    path(
=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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
        "cameras/<int:pk>/ptz/detect/",
        CameraViewSet.as_view({"post": "ptz_detect"}),
        name="camera-ptz-detect",
    ),

    path(
        "cameras/<int:pk>/ptz/status/",
        CameraViewSet.as_view({"get": "ptz_status"}),
        name="camera-ptz-status",
    ),

    path(
        "cameras/<int:pk>/ptz/move/",
        CameraViewSet.as_view({"post": "ptz_move"}),
        name="camera-ptz-move",
    ),

    path(
        "cameras/<int:pk>/ptz/stop/",
        CameraViewSet.as_view({"post": "ptz_stop"}),
        name="camera-ptz-stop",
    ),

    path(
        "cameras/<int:pk>/ptz/home/",
        CameraViewSet.as_view({"post": "ptz_home"}),
        name="camera-ptz-home",
    ),

    path(
        "cameras/<int:pk>/ptz/presets/",
        CameraViewSet.as_view({"get": "ptz_presets"}),
        name="camera-ptz-presets",
    ),

    path(
        "cameras/<int:pk>/ptz/preset/",
        CameraViewSet.as_view({"post": "ptz_preset"}),
        name="camera-ptz-preset",
    ),

    path(
        "cameras/health/",
        CameraViewSet.as_view({
            "get": "health",
        }),
        name="camera-health",
    ),

    path(
        "cameras/<int:camera_id>/live-token/",
        CameraLiveTokenView.as_view(),
        name="camera-live-token",
    ),

    path(
        "cameras/<int:camera_id>/live/",
        camera_mjpeg_view,
        name="camera-live",
    ),

    path(
        "",
        include(router.urls),
    ),
]
