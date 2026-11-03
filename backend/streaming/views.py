import time

from django.core import signing
from django.http import (
    HttpResponseForbidden,
    JsonResponse,
    StreamingHttpResponse,
)
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.views import APIView

from cameras.models import Camera, CameraStream

from streaming.camera_frame_hub import (
    camera_frame_hub,
)

from streaming.camera_ai_frame_hub import (
    camera_ai_frame_hub,
)

from streaming.camera_monitor_manager import (
    camera_monitor_manager,
)


LIVE_TOKEN_SALT = "aks-visionx-live-stream"
LIVE_TOKEN_MAX_AGE = 60


def _camera_access_allowed(
    request,
    camera,
):
    if not request.user.groups.filter(
        name="Super Admin"
    ).exists():
        if (
            not request.user.organization_id
            or camera.organization_id
            != request.user.organization_id
        ):
            return False

    return True


class CameraLiveTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        camera_id,
    ):
        camera = get_object_or_404(
            Camera,
            id=camera_id,
        )

        if not _camera_access_allowed(
            request,
            camera,
        ):
            return HttpResponseForbidden(
                "You cannot access this camera."
            )

        stream = (
            camera.streams
            .filter(
                stream_type=(
                    CameraStream.StreamType.MAIN
                ),
                enabled=True,
            )
            .first()
        )

        if stream is None:
            return JsonResponse(
                {
                    "detail": (
                        "No enabled main camera "
                        "stream is available."
                    )
                },
                status=400,
            )

        token = signing.dumps(
            {
                "user_id": request.user.id,
                "camera_id": camera.id,
            },
            salt=LIVE_TOKEN_SALT,
        )

        return JsonResponse(
            {
                "token": token,
                "expires_in": LIVE_TOKEN_MAX_AGE,
            }
        )


@require_GET
def camera_mjpeg_view(request, camera_id):
    """
    Plain Django MJPEG streaming endpoint.

    RTSP is handled by CameraMonitorManager.
    This endpoint only reads JPEG packets from the
    process-local CameraFrameHub.
    """

    access_token = request.GET.get(
        "access_token",
        "",
    )

    if not access_token:
        return JsonResponse(
            {
                "detail": (
                    "Live stream access token "
                    "is required."
                )
            },
            status=401,
        )

    try:
        payload = signing.loads(
            access_token,
            salt=LIVE_TOKEN_SALT,
            max_age=LIVE_TOKEN_MAX_AGE,
        )
    except signing.BadSignature:
        return JsonResponse(
            {
                "detail": (
                    "Invalid or expired live "
                    "stream token."
                )
            },
            status=401,
        )

    if int(
        payload.get("camera_id", -1)
    ) != int(camera_id):
        return JsonResponse(
            {
                "detail": (
                    "Live stream token does "
                    "not match camera."
                )
            },
            status=403,
        )

    camera = get_object_or_404(
        Camera,
        id=camera_id,
    )

    if not camera_monitor_manager.is_running(
        camera_id
    ):
        return JsonResponse(
            {
                "detail": (
                    "Camera monitor is not running."
                )
            },
            status=409,
        )

    ai_overlay = request.GET.get(
        "ai_overlay",
        "0",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    selected_hub = (
        camera_ai_frame_hub
        if ai_overlay
        else camera_frame_hub
    )

    def generate():
        sequence = 0

        while True:
            try:
                packet = selected_hub.wait_for_frame(
                    camera_id,
                    last_sequence=sequence,
                    timeout=1.0,
                )

                if packet is None:
                    if not camera_monitor_manager.is_running(
                        camera_id
                    ):
                        break
                    continue

                if packet.sequence == sequence:
                    if not camera_monitor_manager.is_running(
                        camera_id
                    ):
                        break
                    continue

                sequence = packet.sequence

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: "
                    + str(len(packet.jpeg)).encode("ascii")
                    + b"\r\n"
                    b"Cache-Control: no-cache, no-store, "
                    b"must-revalidate\r\n"
                    b"Pragma: no-cache\r\n\r\n"
                    + packet.jpeg
                    + b"\r\n"
                )

            except GeneratorExit:
                break

            except Exception as exc:
                print(
                    "LIVE STREAM GENERATOR ERROR:",
                    repr(exc),
                    flush=True,
                )
                break

    response = StreamingHttpResponse(
        generate(),
        content_type=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        ),
    )

    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response["Pragma"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["X-Content-Type-Options"] = "nosniff"

    return response


