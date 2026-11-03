
$ErrorActionPreference = "Stop"

$Root = "E:\AKS VisionX"
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

if (!(Test-Path $Backend)) { throw "Backend not found: $Backend" }
if (!(Test-Path $Frontend)) { throw "Frontend not found: $Frontend" }

function Backup-File($Path) {
    if (Test-Path $Path) {
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Copy-Item $Path "$Path.bak_$stamp" -Force
    }
}

function Write-Utf8NoBom($Path, $Content) {
    $dir = Split-Path $Path -Parent
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

# --------------------------------------------------------------------
# BACKEND: secure short-lived stream token + MJPEG endpoint
# --------------------------------------------------------------------
$streamViews = Join-Path $Backend "streaming\views.py"
$apiUrls = Join-Path $Backend "api\urls.py"

Backup-File $streamViews
Backup-File $apiUrls

$views = @'
import time

import cv2
from django.core import signing
from django.http import (
    HttpResponseForbidden,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from cameras.models import Camera, CameraStream
from streaming.camera_monitor_manager import CameraMonitorManager


LIVE_TOKEN_SALT = "aks-visionx-live-stream"
LIVE_TOKEN_MAX_AGE = 60


def _camera_access_allowed(request, camera):
    if not request.user.groups.filter(name="Super Admin").exists():
        if (
            not request.user.organization_id
            or camera.organization_id != request.user.organization_id
        ):
            return False
    return True


class CameraLiveTokenView(APIView):
    """
    Create a short-lived signed token for the browser MJPEG viewer.

    The normal JWT is sent in the Authorization header to this endpoint.
    The resulting short-lived signed token is then used only by the
    browser <img> request because browsers do not let <img> add a
    custom Authorization header.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, camera_id):
        camera = get_object_or_404(Camera, id=camera_id)

        if not _camera_access_allowed(request, camera):
            return HttpResponseForbidden(
                "You cannot access this camera."
            )

        stream = (
            camera.streams
            .filter(
                stream_type=CameraStream.StreamType.MAIN,
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


class CameraMJPEGView(APIView):
    """
    Stream a camera as MJPEG to the browser.

    Browser:
        GET /api/cameras/<camera_id>/live/?access_token=<short-lived-token>

    The RTSP credentials remain server-side.
    """

    permission_classes = [AllowAny]

    def get(self, request, camera_id):
        access_token = request.query_params.get("access_token", "")

        if not access_token:
            return JsonResponse(
                {"detail": "Live stream access token is required."},
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
                {"detail": "Invalid or expired live stream token."},
                status=401,
            )

        if int(payload.get("camera_id", -1)) != int(camera_id):
            return JsonResponse(
                {"detail": "Live stream token does not match camera."},
                status=403,
            )

        camera = get_object_or_404(
            Camera.objects.prefetch_related("streams"),
            id=camera_id,
        )

        main_stream = (
            camera.streams
            .filter(
                stream_type=CameraStream.StreamType.MAIN,
                enabled=True,
            )
            .first()
        )

        if main_stream is None:
            return JsonResponse(
                {
                    "detail": (
                        "No enabled main camera "
                        "stream is available."
                    )
                },
                status=400,
            )

        stream_url = (
            CameraMonitorManager
            ._build_authenticated_stream_url(
                camera,
                main_stream.url,
            )
        )

        def generate():
            capture = cv2.VideoCapture(
                stream_url,
                cv2.CAP_FFMPEG,
            )

            # Keep the OpenCV read loop bounded. A failed read ends this
            # HTTP stream; the frontend can request a fresh short-lived
            # token and reconnect.
            try:
                if not capture.isOpened():
                    return

                while True:
                    success, frame = capture.read()

                    if not success or frame is None:
                        break

                    success, encoded = cv2.imencode(
                        ".jpg",
                        frame,
                        [
                            cv2.IMWRITE_JPEG_QUALITY,
                            80,
                        ],
                    )

                    if not success:
                        continue

                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Cache-Control: no-cache\r\n\r\n"
                        + encoded.tobytes()
                        + b"\r\n"
                    )

                    time.sleep(0.03)

            finally:
                capture.release()

        response = StreamingHttpResponse(
            generate(),
            content_type=(
                "multipart/x-mixed-replace; "
                "boundary=frame"
            ),
        )

        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"

        return response
'@

Write-Utf8NoBom $streamViews $views

$urls = @'
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from alerts.views import AlertViewSet
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
'@

Write-Utf8NoBom $apiUrls $urls

# --------------------------------------------------------------------
# FRONTEND: service
# --------------------------------------------------------------------
$cameraService = Join-Path $Frontend "src\services\cameraService.ts"
Backup-File $cameraService

$service = @'
import axios from 'axios'
import type { Camera, CameraStatus } from '../types/camera'

const API = '/api'

const authConfig = (token: string) => ({
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

export async function getCameras(token: string) {
  const response = await axios.get(
    `${API}/cameras/`,
    authConfig(token),
  )

  const data = Array.isArray(response.data)
    ? response.data
    : response.data.results || []

  return data as Camera[]
}

export async function getCameraStatus(
  token: string,
  cameraId: number,
) {
  const response = await axios.get(
    `${API}/cameras/${cameraId}/status/`,
    authConfig(token),
  )

  return response.data as CameraStatus
}

export async function getCameraLiveToken(
  token: string,
  cameraId: number,
) {
  const response = await axios.get(
    `${API}/cameras/${cameraId}/live-token/`,
    authConfig(token),
  )

  return response.data as {
    token: string
    expires_in: number
  }
}

export async function startCamera(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/start/`,
    {},
    authConfig(token),
  )

  return response.data
}

export async function stopCamera(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/stop/`,
    {},
    authConfig(token),
  )

  return response.data
}
'@

Write-Utf8NoBom $cameraService $service

# --------------------------------------------------------------------
# FRONTEND: Cameras page
# --------------------------------------------------------------------
$camerasTsx = Join-Path $Frontend "src\pages\Cameras.tsx"
Backup-File $camerasTsx

$tsx = @'
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import {
  getCameraLiveToken,
  getCameraStatus,
  getCameras,
  startCamera,
  stopCamera,
} from '../services/cameraService'
import type { Camera } from '../types/camera'
import './Cameras.css'

type Rotation = 0 | 90 | 180 | 270

function Cameras() {
  const token = localStorage.getItem('aks_token') || ''

  const [cameras, setCameras] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [streamErrors, setStreamErrors] = useState<
    Record<number, boolean>
  >({})
  const [liveTokens, setLiveTokens] = useState<
    Record<number, string>
  >({})
  const [streamVersion, setStreamVersion] = useState<
    Record<number, number>
  >({})
  const [rotation, setRotation] = useState<
    Record<number, Rotation>
  >({})
  const [fullscreenId, setFullscreenId] = useState<
    number | null
  >(null)

  const previewRefs = useRef<
    Record<number, HTMLDivElement | null>
  >({})

  const loadCameras = useCallback(async () => {
    if (!token) return

    try {
      const data = await getCameras(token)
      setCameras(data)
      setError('')
    } catch (err: any) {
      console.error('CAMERA LOAD ERROR:', err)

      if (err?.response?.status === 401) {
        localStorage.removeItem('aks_token')
        window.location.reload()
        return
      }

      setError('Unable to load cameras.')
    } finally {
      setLoading(false)
    }
  }, [token])

  const refreshStatus = useCallback(
    async (cameraList: Camera[]) => {
      if (!token) return

      const updated = await Promise.all(
        cameraList.map(async (camera) => {
          try {
            const status = await getCameraStatus(
              token,
              camera.id,
            )

            return {
              ...camera,
              ...status,
            }
          } catch {
            return camera
          }
        }),
      )

      setCameras((current) =>
        current.map((camera) => {
          const fresh = updated.find(
            (item) => item.id === camera.id,
          )

          return fresh || camera
        }),
      )
    },
    [token],
  )

  const requestLiveToken = useCallback(
    async (cameraId: number) => {
      if (!token) return false

      try {
        const result = await getCameraLiveToken(
          token,
          cameraId,
        )

        setLiveTokens((current) => ({
          ...current,
          [cameraId]: result.token,
        }))

        setStreamErrors((current) => ({
          ...current,
          [cameraId]: false,
        }))

        setStreamVersion((current) => ({
          ...current,
          [cameraId]: (current[cameraId] || 0) + 1,
        }))

        return true
      } catch (err: any) {
        console.error(
          `LIVE TOKEN ERROR [${cameraId}]:`,
          err,
        )

        setLiveTokens((current) => {
          const next = { ...current }
          delete next[cameraId]
          return next
        })

        setStreamErrors((current) => ({
          ...current,
          [cameraId]: true,
        }))

        return false
      }
    },
    [token],
  )

  useEffect(() => {
    loadCameras()
  }, [loadCameras])

  useEffect(() => {
    if (!cameras.length) return

    refreshStatus(cameras)

    const interval = window.setInterval(() => {
      refreshStatus(cameras)
    }, 5000)

    return () => window.clearInterval(interval)
  }, [cameras, refreshStatus])

  useEffect(() => {
    if (!token) return

    cameras.forEach((camera) => {
      const running =
        camera.running === true &&
        camera.status === 'ONLINE'

      if (
        running &&
        !liveTokens[camera.id] &&
        !streamErrors[camera.id]
      ) {
        void requestLiveToken(camera.id)
      }

      if (!running && liveTokens[camera.id]) {
        setLiveTokens((current) => {
          const next = { ...current }
          delete next[camera.id]
          return next
        })
      }
    })
  }, [
    cameras,
    token,
    liveTokens,
    streamErrors,
    requestLiveToken,
  ])

  useEffect(() => {
    const onFullscreenChange = () => {
      const element = document.fullscreenElement

      if (!element) {
        setFullscreenId(null)
        return
      }

      const cameraId = Number(
        (element as HTMLElement).dataset.cameraId,
      )

      setFullscreenId(
        Number.isFinite(cameraId) ? cameraId : null,
      )
    }

    document.addEventListener(
      'fullscreenchange',
      onFullscreenChange,
    )

    return () => {
      document.removeEventListener(
        'fullscreenchange',
        onFullscreenChange,
      )
    }
  }, [])

  const handleStart = async (cameraId: number) => {
    setActionId(cameraId)
    setMessage('')
    setError('')

    try {
      setStreamErrors((current) => ({
        ...current,
        [cameraId]: false,
      }))

      const response = await startCamera(
        token,
        cameraId,
      )

      setMessage(
        `Camera ${cameraId}: ${
          response?.status || 'started'
        }`,
      )

      await loadCameras()
      await requestLiveToken(cameraId)
    } catch (err: any) {
      console.error('START ERROR:', err)

      setError(
        err?.response?.data?.detail ||
          `Unable to start camera ${cameraId}.`,
      )
    } finally {
      setActionId(null)
    }
  }

  const handleStop = async (cameraId: number) => {
    setActionId(cameraId)
    setMessage('')
    setError('')

    try {
      const response = await stopCamera(
        token,
        cameraId,
      )

      setMessage(
        `Camera ${cameraId}: ${
          response?.status || 'stopping'
        }`,
      )

      setLiveTokens((current) => {
        const next = { ...current }
        delete next[cameraId]
        return next
      })

      setStreamErrors((current) => ({
        ...current,
        [cameraId]: false,
      }))

      if (
        document.fullscreenElement ===
        previewRefs.current[cameraId]
      ) {
        await document.exitFullscreen().catch(() => {})
      }

      await loadCameras()
    } catch (err: any) {
      console.error('STOP ERROR:', err)

      setError(
        err?.response?.data?.detail ||
          `Unable to stop camera ${cameraId}.`,
      )
    } finally {
      setActionId(null)
    }
  }

  const handleFullscreen = async (
    cameraId: number,
  ) => {
    const element = previewRefs.current[cameraId]

    if (!element) return

    try {
      if (document.fullscreenElement === element) {
        await document.exitFullscreen()
      } else {
        await element.requestFullscreen()
      }
    } catch (err) {
      console.error('FULLSCREEN ERROR:', err)
      setError(
        'Fullscreen is not available in this browser.',
      )
    }
  }

  const handleRotate = (
    cameraId: number,
    direction: 1 | -1,
  ) => {
    setRotation((current) => {
      const currentRotation =
        current[cameraId] || 0

      const next =
        (currentRotation + direction * 90 + 360) %
        360

      return {
        ...current,
        [cameraId]: next as Rotation,
      }
    })
  }

  const handleReconnect = async (
    cameraId: number,
  ) => {
    setMessage('')
    setError('')

    setStreamErrors((current) => ({
      ...current,
      [cameraId]: false,
    }))

    const success =
      await requestLiveToken(cameraId)

    if (!success) {
      setError(
        `Unable to reconnect Camera ${cameraId}.`,
      )
    }
  }

  const online = cameras.filter(
    (camera) => camera.status === 'ONLINE',
  ).length

  const running = cameras.filter(
    (camera) => camera.running === true,
  ).length

  const getLiveUrl = (
    cameraId: number,
    liveToken: string,
  ) => {
    const version = streamVersion[cameraId] || 0

    return `/api/cameras/${cameraId}/live/?access_token=${encodeURIComponent(
      liveToken,
    )}&v=${version}`
  }

  return (
    <div className="cameras-page">
      <div className="camera-page-header">
        <div>
          <h2>Camera Monitoring</h2>
          <p>
            Live camera status and monitoring controls.
          </p>
        </div>

        <button
          className="camera-refresh-button"
          onClick={loadCameras}
          disabled={loading}
        >
          Refresh
        </button>
      </div>

      <div className="camera-summary">
        <div>
          <span>Total Cameras</span>
          <strong>{cameras.length}</strong>
        </div>

        <div>
          <span>Online</span>
          <strong className="summary-online">
            {online}
          </strong>
        </div>

        <div>
          <span>Running</span>
          <strong>{running}</strong>
        </div>
      </div>

      {message && (
        <div className="camera-alert success">
          {message}
        </div>
      )}

      {error && (
        <div className="camera-alert error">
          {error}
        </div>
      )}

      {loading ? (
        <div className="camera-empty">
          Loading cameras...
        </div>
      ) : cameras.length === 0 ? (
        <div className="camera-empty">
          <div className="camera-empty-icon">
            CAM
          </div>

          <h3>No cameras found</h3>

          <p>
            Add a camera from the backend before
            starting monitoring.
          </p>
        </div>
      ) : (
        <div className="camera-grid-new">
          {cameras.map((camera) => {
            const isOnline =
              camera.status === 'ONLINE'

            const isRunning =
              camera.running === true

            const busy = actionId === camera.id

            const streamFailed =
              streamErrors[camera.id] === true

            const liveToken =
              liveTokens[camera.id]

            const showLive =
              isOnline &&
              isRunning &&
              Boolean(liveToken) &&
              !streamFailed

            const cameraRotation =
              rotation[camera.id] || 0

            return (
              <article
                className="camera-card-new"
                key={camera.id}
              >
                <div
                  ref={(element) => {
                    previewRefs.current[camera.id] =
                      element
                  }}
                  data-camera-id={camera.id}
                  className={`camera-preview-new ${
                    fullscreenId === camera.id
                      ? 'is-fullscreen'
                      : ''
                  }`}
                >
                  {showLive ? (
                    <img
                      key={`${camera.id}-${streamVersion[camera.id] || 0}`}
                      src={getLiveUrl(
                        camera.id,
                        liveToken,
                      )}
                      alt={`${camera.name || 'Camera'} live stream`}
                      className="camera-live-image"
                      style={{
                        transform: `rotate(${cameraRotation}deg)`,
                      }}
                      onError={() => {
                        setStreamErrors((current) => ({
                          ...current,
                          [camera.id]: true,
                        }))
                      }}
                    />
                  ) : (
                    <div className="camera-no-live">
                      <div className="camera-preview-icon">
                        CAM
                      </div>

                      <span>
                        {streamFailed
                          ? 'LIVE STREAM ERROR'
                          : isOnline
                            ? isRunning
                              ? 'CONNECTING LIVE STREAM'
                              : 'CAMERA ONLINE'
                            : 'NO LIVE STREAM'}
                      </span>
                    </div>
                  )}

                  <div className="camera-view-toolbar">
                    <button
                      type="button"
                      title="Rotate left"
                      onClick={() =>
                        handleRotate(
                          camera.id,
                          -1,
                        )
                      }
                    >
                      ↺
                    </button>

                    <span>
                      {cameraRotation}°
                    </span>

                    <button
                      type="button"
                      title="Rotate right"
                      onClick={() =>
                        handleRotate(
                          camera.id,
                          1,
                        )
                      }
                    >
                      ↻
                    </button>

                    <button
                      type="button"
                      title="Reconnect live stream"
                      onClick={() =>
                        handleReconnect(
                          camera.id,
                        )
                      }
                    >
                      ⟳
                    </button>

                    <button
                      type="button"
                      title={
                        fullscreenId === camera.id
                          ? 'Exit fullscreen'
                          : 'Fullscreen'
                      }
                      onClick={() =>
                        handleFullscreen(
                          camera.id,
                        )
                      }
                    >
                      {fullscreenId === camera.id
                        ? '⛶'
                        : '⛶'}
                    </button>
                  </div>

                  <div
                    className={`camera-status ${
                      isOnline
                        ? 'online'
                        : 'offline'
                    }`}
                  >
                    <span />
                    {camera.status || 'UNKNOWN'}
                  </div>
                </div>

                <div className="camera-card-body">
                  <div className="camera-name-row">
                    <div>
                      <h3>
                        {camera.name ||
                          `Camera ${camera.id}`}
                      </h3>

                      <small>
                        Camera ID: {camera.id}
                      </small>
                    </div>

                    <span
                      className={`running-state ${
                        isRunning
                          ? 'running'
                          : 'stopped'
                      }`}
                    >
                      {isRunning
                        ? 'RUNNING'
                        : 'STOPPED'}
                    </span>
                  </div>

                  <div className="camera-meta">
                    <div>
                      <span>Enabled</span>

                      <strong>
                        {camera.enabled
                          ? 'Yes'
                          : 'No'}
                      </strong>
                    </div>

                    <div>
                      <span>Last Seen</span>

                      <strong>
                        {camera.last_seen
                          ? new Date(
                              camera.last_seen,
                            ).toLocaleString()
                          : 'Never'}
                      </strong>
                    </div>
                  </div>

                  <div className="camera-controls">
                    <button
                      className="camera-start"
                      disabled={
                        isRunning || busy
                      }
                      onClick={() =>
                        handleStart(camera.id)
                      }
                    >
                      {busy
                        ? 'Working...'
                        : 'Start'}
                    </button>

                    <button
                      className="camera-stop"
                      disabled={
                        !isRunning || busy
                      }
                      onClick={() =>
                        handleStop(camera.id)
                      }
                    >
                      Stop
                    </button>

                    <button
                      className="camera-status-button"
                      onClick={() =>
                        refreshStatus([camera])
                      }
                    >
                      Status
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default Cameras
'@

Write-Utf8NoBom $camerasTsx $tsx

# --------------------------------------------------------------------
# FRONTEND: CSS
# --------------------------------------------------------------------
$camerasCss = Join-Path $Frontend "src\pages\Cameras.css"
Backup-File $camerasCss

$css = @'
.cameras-page {
  width: 100%;
  max-width: 1500px;
  margin: 0 auto;
}

.camera-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.camera-page-header h2 {
  margin: 0;
  color: #edf3fa;
  font-size: 21px;
}

.camera-page-header p {
  margin: 6px 0 0;
  color: #69788d;
  font-size: 12px;
}

.camera-refresh-button {
  padding: 9px 14px;
  border: 1px solid #263b54;
  border-radius: 8px;
  background: #0d1724;
  color: #b9c7d8;
  cursor: pointer;
}

.camera-refresh-button:disabled,
.camera-controls button:disabled {
  cursor: not-allowed;
  opacity: .45;
}

.camera-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}

.camera-summary > div {
  padding: 18px;
  border: 1px solid #1b2a3c;
  border-radius: 12px;
  background: #0b121d;
}

.camera-summary span {
  display: block;
  color: #66758a;
  font-size: 11px;
}

.camera-summary strong {
  display: block;
  margin-top: 7px;
  color: #edf3fa;
  font-size: 25px;
}

.summary-online {
  color: #20d486 !important;
}

.camera-alert {
  margin-bottom: 18px;
  padding: 11px 14px;
  border-radius: 8px;
  font-size: 12px;
}

.camera-alert.success {
  border: 1px solid rgba(32, 212, 134, .25);
  background: rgba(32, 212, 134, .07);
  color: #53dc9c;
}

.camera-alert.error {
  border: 1px solid rgba(239, 82, 96, .25);
  background: rgba(239, 82, 96, .07);
  color: #ff8791;
}

.camera-grid-new {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.camera-card-new {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #1b2a3c;
  border-radius: 14px;
  background: #0b121c;
}

.camera-preview-new {
  width: 100%;
  height: 190px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #050b12;
  color: #53677e;
  font-size: 9px;
  letter-spacing: 1.5px;
}

.camera-preview-new:fullscreen {
  width: 100vw;
  height: 100vh;
  min-width: 100vw;
  min-height: 100vh;
  border: 0;
  border-radius: 0;
  background: #000;
}

.camera-preview-new.is-fullscreen {
  background: #000;
}

.camera-live-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #000;
  transform-origin: center center;
  transition: transform .2s ease;
  user-select: none;
  -webkit-user-drag: none;
}

.camera-preview-new:not(:fullscreen) .camera-live-image {
  object-fit: cover;
}

.camera-preview-new.is-fullscreen .camera-live-image {
  object-fit: contain;
}

.camera-no-live {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  height: 100%;
  background:
    linear-gradient(
      rgba(17, 29, 43, .88),
      rgba(5, 11, 18, .98)
    ),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 20px,
      rgba(74, 101, 130, .06) 21px
    );
}

.camera-preview-icon {
  font-size: 31px;
  opacity: .55;
}

.camera-view-toolbar {
  position: absolute;
  left: 10px;
  bottom: 10px;
  z-index: 10;

  display: flex;
  align-items: center;
  gap: 5px;

  padding: 5px;
  border: 1px solid rgba(255, 255, 255, .09);
  border-radius: 9px;
  background: rgba(4, 9, 15, .82);
  backdrop-filter: blur(7px);
}

.camera-view-toolbar button {
  min-width: 28px;
  height: 28px;
  padding: 0 7px;
  border: 1px solid #263448;
  border-radius: 6px;
  background: #111b29;
  color: #d7e2ef;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}

.camera-view-toolbar button:hover {
  background: #182536;
}

.camera-view-toolbar span {
  min-width: 38px;
  color: #b9c7d8;
  font-size: 9px;
  text-align: center;
}

.camera-status {
  position: absolute;
  top: 11px;
  right: 11px;
  z-index: 10;

  display: flex;
  align-items: center;
  gap: 6px;

  padding: 6px 9px;
  border-radius: 7px;

  background: rgba(4, 9, 15, .86);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0;
}

.camera-status span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.camera-status.online {
  color: #20d486;
}

.camera-status.online span {
  background: #20d486;
  box-shadow: 0 0 8px rgba(32, 212, 134, .7);
}

.camera-status.offline {
  color: #ef6674;
}

.camera-status.offline span {
  background: #ef5260;
}

.camera-card-body {
  padding: 17px;
}

.camera-name-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.camera-name-row h3 {
  margin: 0;
  color: #edf3fa;
  font-size: 14px;
}

.camera-name-row small {
  display: block;
  margin-top: 5px;
  color: #5f7085;
  font-size: 9px;
}

.running-state {
  padding: 5px 7px;
  border-radius: 5px;
  font-size: 8px;
  font-weight: 800;
}

.running-state.running {
  color: #20d486;
  background: rgba(32, 212, 134, .09);
}

.running-state.stopped {
  color: #ef7883;
  background: rgba(239, 82, 96, .09);
}

.camera-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 17px 0;
  padding: 13px 0;
  border-top: 1px solid #182434;
  border-bottom: 1px solid #182434;
}

.camera-meta span {
  display: block;
  margin-bottom: 5px;
  color: #607086;
  font-size: 9px;
}

.camera-meta strong {
  display: block;
  overflow: hidden;
  color: #b7c3d2;
  font-size: 10px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.camera-controls {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 7px;
}

.camera-controls button {
  padding: 9px 5px;
  border-radius: 7px;
  font-size: 10px;
  font-weight: 650;
  cursor: pointer;
}

.camera-start {
  border: 1px solid rgba(32, 212, 134, .3);
  background: rgba(32, 212, 134, .08);
  color: #20d486;
}

.camera-stop {
  border: 1px solid rgba(239, 82, 96, .3);
  background: rgba(239, 82, 96, .08);
  color: #ef7a85;
}

.camera-status-button {
  border: 1px solid #263448;
  background: #111b29;
  color: #b9c5d4;
}

.camera-empty {
  min-height: 350px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  border: 1px dashed #263548;
  border-radius: 14px;
  color: #69788d;
  text-align: center;
}

.camera-empty-icon {
  color: #3f536b;
  font-size: 32px;
}

.camera-empty h3 {
  margin: 8px 0 0;
  color: #c4cfdd;
  font-size: 16px;
}

.camera-empty p {
  margin: 0;
  font-size: 11px;
}

@media (max-width: 1100px) {
  .camera-grid-new {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .camera-summary {
    grid-template-columns: 1fr;
  }

  .camera-grid-new {
    grid-template-columns: 1fr;
  }

  .camera-page-header {
    align-items: flex-start;
  }

  .camera-page-header {
    flex-direction: column;
  }

  .camera-refresh-button {
    width: 100%;
  }

  .camera-preview-new {
    height: 220px;
  }

  .camera-controls {
    grid-template-columns: 1fr;
  }
}
'@

Write-Utf8NoBom $camerasCss $css

# --------------------------------------------------------------------
# VALIDATE
# --------------------------------------------------------------------
Write-Host ""
Write-Host "=== AKS VisionX Phase 7 camera live patch applied ===" -ForegroundColor Green
Write-Host ""
Write-Host "Backend checks..." -ForegroundColor Cyan
Set-Location $Backend
& "$Root\.venv\Scripts\python.exe" manage.py check

if ($LASTEXITCODE -ne 0) {
    throw "Django check failed."
}

Write-Host ""
Write-Host "Frontend build..." -ForegroundColor Cyan
Set-Location $Frontend
npm run build

if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed."
}

Write-Host ""
Write-Host "DONE." -ForegroundColor Green
Write-Host "Backups were created next to changed files with .bak_YYYYMMDD_HHMMSS suffix."
Write-Host ""
Write-Host "Start backend:"
Write-Host "  cd `"$Backend`""
Write-Host "  python manage.py runserver 127.0.0.1:8000"
Write-Host ""
Write-Host "Start frontend in another terminal:"
Write-Host "  cd `"$Frontend`""
Write-Host "  npm run dev"
