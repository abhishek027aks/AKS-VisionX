Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

cd "E:\AKS VisionX\frontend"

Copy-Item ".\src\pages\Overview.tsx" ".\src\pages\Overview.tsx.professional_v2_backup" -Force
Copy-Item ".\src\App.css" ".\src\App.css.professional_v2_backup" -Force

@'
from pathlib import Path

root = Path(r"E:\AKS VisionX\frontend")

overview = root / "src" / "pages" / "Overview.tsx"
css = root / "src" / "pages" / "Overview.css"

overview.write_text(r'''import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  getCameraLiveToken,
} from '../services/cameraService'

import {
  getDashboardSummary,
} from '../services/dashboardService'

import {
  getRecordings,
  type Recording,
} from '../services/recordingService'

import './Overview.css'

type OverviewProps = {
  token: string
}

type CameraSummary = {
  id: number
  name: string
  status?: string
  running?: boolean
  recording?: boolean
  last_seen?: string | null
}

type DashboardSummary = {
  cameras: CameraSummary[]
  counts: {
    cameras: number
    online_cameras: number
    running_cameras: number
    recording_cameras: number
    detections: number
    persons: number
    vehicles: number
    events: number
    alerts: number
    active_alerts: number
    tracking_sessions: number
    tracking_points: number
    tracking_locations: number
    camera_visits: number
    active_tracking: number
    recordings: number
  }
  recent_events: any[]
  recent_alerts: any[]
  recent_detections: any[]
}

function formatDate(value?: string | null) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleString()
}

function formatTime(value?: string | null) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusClass(
  camera: CameraSummary,
) {
  if (camera.status === 'ONLINE') {
    return camera.running
      ? 'online running'
      : 'online'
  }

  return 'offline'
}

function Overview({
  token,
}: OverviewProps) {
  const [data, setData] =
    useState<DashboardSummary | null>(null)

  const [recordings, setRecordings] =
    useState<Recording[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [lastUpdated, setLastUpdated] =
    useState<string | null>(null)

  const [primaryCameraId, setPrimaryCameraId] =
    useState<number | null>(null)

  const [liveToken, setLiveToken] =
    useState('')

  const [liveError, setLiveError] =
    useState(false)

  const [search, setSearch] =
    useState('')

  const loadDashboard =
    useCallback(async () => {
      setError('')

      try {
        const [
          summary,
          recordingData,
        ] = await Promise.all([
          getDashboardSummary(token),
          getRecordings(token),
        ])

        const dashboard =
          summary as DashboardSummary

        setData(dashboard)

        setRecordings(
          recordingData
            .filter(
              (item) =>
                item.status === 'COMPLETED',
            )
            .slice(0, 5),
        )

        setLastUpdated(
          new Date().toISOString(),
        )

        const primary =
          dashboard.cameras.find(
            (camera) =>
              camera.status === 'ONLINE' &&
              camera.running,
          ) ||
          dashboard.cameras.find(
            (camera) =>
              camera.status === 'ONLINE',
          ) ||
          dashboard.cameras[0]

        if (primary) {
          setPrimaryCameraId(
            primary.id,
          )
        }
      } catch (err: any) {
        console.error(
          'DASHBOARD LOAD ERROR:',
          err,
        )

        setError(
          err?.response?.data?.detail ||
            'Unable to load dashboard data.',
        )
      } finally {
        setLoading(false)
      }
    }, [token])

  const loadLiveToken =
    useCallback(async () => {
      if (!token || !primaryCameraId) {
        return
      }

      const camera =
        data?.cameras.find(
          (item) =>
            item.id === primaryCameraId,
        )

      if (
        !camera ||
        camera.status !== 'ONLINE' ||
        !camera.running
      ) {
        setLiveToken('')
        return
      }

      try {
        setLiveError(false)

        const result =
          await getCameraLiveToken(
            token,
            primaryCameraId,
          )

        setLiveToken(result.token)
      } catch (err) {
        console.warn(
          'DASHBOARD LIVE TOKEN ERROR:',
          err,
        )

        setLiveToken('')
        setLiveError(true)
      }
    }, [
      data?.cameras,
      primaryCameraId,
      token,
    ])

  useEffect(() => {
    void loadDashboard()

    const interval =
      window.setInterval(
        () => {
          void loadDashboard()
        },
        5000,
      )

    return () =>
      window.clearInterval(
        interval,
      )
  }, [loadDashboard])

  useEffect(() => {
    void loadLiveToken()

    const interval =
      window.setInterval(
        () => {
          void loadLiveToken()
        },
        30000,
      )

    return () =>
      window.clearInterval(
        interval,
      )
  }, [loadLiveToken])

  const counts =
    data?.counts

  const cameras =
    useMemo(() => {
      const list =
        data?.cameras || []

      const query =
        search.trim().toLowerCase()

      if (!query) {
        return list
      }

      return list.filter(
        (camera) =>
          camera.name
            .toLowerCase()
            .includes(query) ||
          String(camera.id).includes(
            query,
          ),
      )
    }, [data, search])

  const primaryCamera =
    data?.cameras.find(
      (camera) =>
        camera.id ===
        primaryCameraId,
    ) || null

  const backendConnected =
    Boolean(data)

  const healthItems = [
    {
      label: 'Backend API',
      value: backendConnected
        ? 'CONNECTED'
        : 'UNAVAILABLE',
      state: backendConnected
        ? 'good'
        : 'bad',
    },
    {
      label: 'Camera Network',
      value: counts
        ? `${counts.online_cameras}/${counts.cameras} ONLINE`
        : '—',
      state:
        counts &&
        counts.cameras > 0 &&
        counts.online_cameras > 0
          ? 'good'
          : 'warn',
    },
    {
      label: 'Monitoring',
      value: counts
        ? `${counts.running_cameras} RUNNING`
        : '—',
      state:
        counts &&
        counts.running_cameras > 0
          ? 'good'
          : 'warn',
    },
    {
      label: 'Recording',
      value: counts
        ? `${counts.recording_cameras} ACTIVE`
        : '—',
      state:
        counts &&
        counts.recording_cameras > 0
          ? 'good'
          : 'warn',
    },
    {
      label: 'AI Engine',
      value: counts
        ? `${counts.detections} DETECTIONS`
        : '—',
      state:
        counts &&
        counts.detections > 0
          ? 'good'
          : 'warn',
    },
  ]

  if (loading) {
    return (
      <div className="ov-shell ov-loading">
        <div className="ov-loading-card">
          <div className="ov-loading-orb" />
          <h2>
            Loading AKS VisionX
          </h2>
          <p>
            Syncing live security data
            from the backend.
          </p>
        </div>
      </div>
    )
  }

  if (error || !data || !counts) {
    return (
      <div className="ov-shell ov-loading">
        <div className="ov-error-card">
          <span className="ov-error-icon">
            !
          </span>
          <h2>
            Dashboard unavailable
          </h2>
          <p>
            {error ||
              'The dashboard returned no data.'}
          </p>
          <button
            type="button"
            onClick={() =>
              void loadDashboard()
            }
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="ov-shell">
      <div className="ov-header">
        <div>
          <div className="ov-eyebrow">
            SECURITY OPERATIONS CENTER
          </div>
          <h1>
            Dashboard
          </h1>
          <p>
            Real-time monitoring,
            intelligence and system health.
          </p>
        </div>

        <div className="ov-header-actions">
          <div
            className={
              backendConnected
                ? 'ov-connection good'
                : 'ov-connection bad'
            }
          >
            <span />
            {backendConnected
              ? 'Backend Connected'
              : 'Backend Offline'}
          </div>

          <div className="ov-updated">
            Updated{' '}
            {lastUpdated
              ? formatTime(lastUpdated)
              : '—'}
          </div>
        </div>
      </div>

      <div className="ov-kpis">
        <article className="ov-kpi blue">
          <span className="ov-kpi-label">
            Total Cameras
          </span>
          <strong>
            {counts.cameras}
          </strong>
          <small>
            Registered devices
          </small>
        </article>

        <article className="ov-kpi green">
          <span className="ov-kpi-label">
            Online
          </span>
          <strong>
            {counts.online_cameras}
          </strong>
          <small>
            Live network
          </small>
        </article>

        <article className="ov-kpi amber">
          <span className="ov-kpi-label">
            Running
          </span>
          <strong>
            {counts.running_cameras}
          </strong>
          <small>
            Active monitors
          </small>
        </article>

        <article className="ov-kpi red">
          <span className="ov-kpi-label">
            Recording
          </span>
          <strong>
            {counts.recording_cameras}
          </strong>
          <small>
            Active recordings
          </small>
        </article>

        <article className="ov-kpi purple">
          <span className="ov-kpi-label">
            AI Detections
          </span>
          <strong>
            {counts.detections}
          </strong>
          <small>
            Detection records
          </small>
        </article>
      </div>

      <div className="ov-main-grid">
        <section className="ov-panel ov-live-panel">
          <div className="ov-panel-header">
            <div>
              <span className="ov-panel-kicker">
                LIVE MONITOR
              </span>
              <h2>
                {primaryCamera?.name ||
                  'Primary Camera'}
              </h2>
            </div>

            <div className="ov-live-status">
              <span />
              {primaryCamera?.running
                ? 'LIVE'
                : 'OFFLINE'}
            </div>
          </div>

          <div className="ov-live-stage">
            {primaryCamera &&
            liveToken ? (
              <img
                src={`${(
                  import.meta.env
                    .VITE_API_ORIGIN ||
                  'http://127.0.0.1:8000'
                )}/api/cameras/${
                  primaryCamera.id
                }/live/?access_token=${encodeURIComponent(
                  liveToken,
                )}&ai_overlay=1&v=${Date.now()}`}
                alt={`${primaryCamera.name} live stream`}
                onError={() =>
                  setLiveError(true)
                }
              />
            ) : (
              <div className="ov-live-empty">
                <div className="ov-live-empty-orb">
                  CAM
                </div>
                <strong>
                  {primaryCamera
                    ? liveError
                      ? 'Live stream unavailable'
                      : 'Connecting to camera'
                    : 'No active camera'}
                </strong>
                <span>
                  {primaryCamera
                    ? primaryCamera.running
                      ? 'Waiting for live stream token'
                      : 'Start the camera to view live video'
                    : 'Add a camera to begin monitoring'}
                </span>
              </div>
            )}

            {primaryCamera && (
              <div className="ov-live-overlay">
                <span>
                  {primaryCamera.status ||
                    'UNKNOWN'}
                </span>
                <span>
                  {primaryCamera.recording
                    ? 'RECORDING'
                    : 'MONITORING'}
                </span>
                <span>
                  CAMERA #{primaryCamera.id}
                </span>
              </div>
            )}
          </div>

          <div className="ov-live-footer">
            <div>
              <span>STATUS</span>
              <strong>
                {primaryCamera?.running
                  ? 'RUNNING'
                  : 'STOPPED'}
              </strong>
            </div>

            <div>
              <span>RECORDING</span>
              <strong>
                {primaryCamera?.recording
                  ? 'ACTIVE'
                  : 'IDLE'}
              </strong>
            </div>

            <div>
              <span>LAST SEEN</span>
              <strong>
                {formatDate(
                  primaryCamera?.last_seen,
                )}
              </strong>
            </div>
          </div>
        </section>

        <aside className="ov-side">
          <section className="ov-panel">
            <div className="ov-panel-header">
              <div>
                <span className="ov-panel-kicker">
                  INTELLIGENCE
                </span>
                <h2>
                  AI Activity
                </h2>
              </div>
              <strong className="ov-panel-count">
                {counts.detections}
              </strong>
            </div>

            <div className="ov-ai-grid">
              <div className="ov-ai-stat person">
                <span>
                  PERSON PROFILES
                </span>
                <strong>
                  {counts.persons}
                </strong>
              </div>

              <div className="ov-ai-stat vehicle">
                <span>
                  VEHICLE PROFILES
                </span>
                <strong>
                  {counts.vehicles}
                </strong>
              </div>

              <div className="ov-ai-stat tracking">
                <span>
                  ACTIVE TRACKING
                </span>
                <strong>
                  {counts.active_tracking}
                </strong>
              </div>
            </div>

            <div className="ov-list">
              {data.recent_detections
                .slice(0, 5)
                .map(
                  (detection) => (
                    <div
                      className="ov-list-item"
                      key={detection.id}
                    >
                      <div>
                        <strong>
                          {detection.label ||
                            detection.object_type ||
                            'Detection'}
                        </strong>
                        <span>
                          Camera{' '}
                          {detection.camera_id ??
                            '—'}
                        </span>
                      </div>

                      <div className="ov-list-value">
                        {detection.confidence ==
                        null
                          ? '—'
                          : `${(
                              Number(
                                detection.confidence,
                              ) * 100
                            ).toFixed(0)}%`}
                      </div>
                    </div>
                  ),
                )}

              {data.recent_detections
                .length === 0 && (
                <div className="ov-empty-row">
                  No recent detections.
                </div>
              )}
            </div>
          </section>

          <section className="ov-panel">
            <div className="ov-panel-header">
              <div>
                <span className="ov-panel-kicker">
                  SECURITY
                </span>
                <h2>
                  Alert Center
                </h2>
              </div>
              <strong className="ov-danger-count">
                {counts.active_alerts}
              </strong>
            </div>

            <div className="ov-list">
              {data.recent_alerts
                .slice(0, 4)
                .map(
                  (alert) => (
                    <div
                      className="ov-list-item"
                      key={alert.id}
                    >
                      <div>
                        <strong>
                          {alert.title ||
                            'Alert'}
                        </strong>
                        <span>
                          {alert.message ||
                            'No message'}
                        </span>
                      </div>

                      <div
                        className={`ov-severity ${
                          String(
                            alert.severity ||
                              'INFO',
                          ).toLowerCase()
                        }`}
                      >
                        {alert.severity ||
                          'INFO'}
                      </div>
                    </div>
                  ),
                )}

              {data.recent_alerts
                .length === 0 && (
                <div className="ov-empty-row">
                  No recent alerts.
                </div>
              )}
            </div>
          </section>
        </aside>
      </div>

      <div className="ov-secondary-grid">
        <section className="ov-panel">
          <div className="ov-panel-header">
            <div>
              <span className="ov-panel-kicker">
                CAMERAS
              </span>
              <h2>
                Camera Fleet
              </h2>
            </div>

            <input
              className="ov-search"
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value,
                )
              }
              placeholder="Search cameras..."
            />
          </div>

          <div className="ov-camera-grid">
            {cameras
              .slice(0, 8)
              .map((camera) => (
                <div
                  className="ov-camera-row"
                  key={camera.id}
                >
                  <div className="ov-camera-dot" />

                  <div className="ov-camera-info">
                    <strong>
                      {camera.name ||
                        `Camera ${camera.id}`}
                    </strong>
                    <span>
                      ID {camera.id}
                      {' • '}
                      {camera.last_seen
                        ? formatTime(
                            camera.last_seen,
                          )
                        : 'No last-seen data'}
                    </span>
                  </div>

                  <div
                    className={`ov-camera-state ${statusClass(
                      camera,
                    )}`}
                  >
                    {camera.running
                      ? 'RUNNING'
                      : camera.status ||
                        'OFFLINE'}
                  </div>
                </div>
              ))}

            {cameras.length === 0 && (
              <div className="ov-empty-row">
                No matching cameras.
              </div>
            )}
          </div>
        </section>

        <section className="ov-panel">
          <div className="ov-panel-header">
            <div>
              <span className="ov-panel-kicker">
                RECORDINGS
              </span>
              <h2>
                Recent Recordings
              </h2>
            </div>

            <strong className="ov-panel-count">
              {counts.recordings}
            </strong>
          </div>

          <div className="ov-recording-list">
            {recordings.map(
              (recording) => (
                <div
                  className="ov-recording-row"
                  key={recording.id}
                >
                  <div className="ov-recording-thumb">
                    REC
                  </div>

                  <div className="ov-recording-info">
                    <strong>
                      {recording.camera_name ||
                        `Camera ${recording.camera}`}
                    </strong>
                    <span>
                      {formatDate(
                        recording.started_at,
                      )}
                    </span>
                  </div>

                  <div className="ov-recording-meta">
                    <strong>
                      {recording.status}
                    </strong>
                    <span>
                      {Number(
                        recording.file_size_bytes ||
                          0,
                      ) > 0
                        ? `${(
                            Number(
                              recording.file_size_bytes,
                            ) /
                            1024 /
                            1024
                          ).toFixed(0)} MB`
                        : '—'}
                    </span>
                  </div>
                </div>
              ),
            )}

            {recordings.length === 0 && (
              <div className="ov-empty-row">
                No completed recordings.
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="ov-panel ov-events-panel">
        <div className="ov-panel-header">
          <div>
            <span className="ov-panel-kicker">
              ACTIVITY
            </span>
            <h2>
              Recent Events
            </h2>
          </div>
          <strong className="ov-panel-count">
            {counts.events}
          </strong>
        </div>

        <div className="ov-event-grid">
          {data.recent_events
            .slice(0, 6)
            .map((event) => (
              <div
                className="ov-event-card"
                key={event.id}
              >
                <span className="ov-event-dot" />
                <div>
                  <strong>
                    {event.title ||
                      event.event_type ||
                      'Event'}
                  </strong>
                  <p>
                    {event.description ||
                      'No description'}
                  </p>
                  <small>
                    {event.status ||
                      'NEW'}
                    {' • '}
                    {formatDate(
                      event.occurred_at,
                    )}
                  </small>
                </div>
              </div>
            ))}

          {data.recent_events.length ===
            0 && (
            <div className="ov-empty-row">
              No security events recorded.
            </div>
          )}
        </div>
      </section>

      <section className="ov-panel ov-health-panel">
        <div className="ov-panel-header">
          <div>
            <span className="ov-panel-kicker">
              SYSTEM
            </span>
            <h2>
              System Health
            </h2>
          </div>

          <span
            className={
              backendConnected
                ? 'ov-health-badge good'
                : 'ov-health-badge bad'
            }
          >
            {backendConnected
              ? 'OPERATIONAL'
              : 'DEGRADED'}
          </span>
        </div>

        <div className="ov-health-grid">
          {healthItems.map(
            (item) => (
              <div
                className="ov-health-item"
                key={item.label}
              >
                <div
                  className={`ov-health-light ${item.state}`}
                />
                <div>
                  <strong>
                    {item.label}
                  </strong>
                  <span>
                    {item.value}
                  </span>
                </div>
              </div>
            ),
          )}
        </div>
      </section>

      <div className="ov-footer-strip">
        <div>
          <strong>
            AKS VisionX
          </strong>
          <span>
            Intelligent Camera Monitoring
            &amp; AI Surveillance
          </span>
        </div>

        <div>
          <span>
            Events {counts.events}
          </span>
          <span>
            Alerts {counts.alerts}
          </span>
          <span>
            Tracking {counts.active_tracking}
          </span>
          <span>
            Recordings {counts.recordings}
          </span>
        </div>
      </div>
    </div>
  )
}

export default Overview
''', encoding="utf-8")
css.write_text(r'''.ov-shell {
  --ov-bg: #050a12;
  --ov-panel: rgba(9, 18, 31, 0.94);
  --ov-panel-2: rgba(12, 25, 42, 0.96);
  --ov-border: rgba(117, 164, 205, 0.16);
  --ov-border-strong: rgba(42, 157, 255, 0.35);
  --ov-text: #eff7ff;
  --ov-muted: #758a9e;
  --ov-soft: #aabccc;
  --ov-blue: #2ca5ff;
  --ov-green: #21d17a;
  --ov-red: #ff5566;
  --ov-amber: #ffbc3d;
  --ov-purple: #a86cff;
  --ov-shadow: 0 18px 45px rgba(0, 0, 0, 0.24);

  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  color: var(--ov-text);
}

.ov-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 2px;
}

.ov-eyebrow,
.ov-panel-kicker {
  color: var(--ov-blue);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.ov-header h1 {
  margin: 5px 0 0;
  font-size: 28px;
  line-height: 1.05;
  letter-spacing: -0.035em;
}

.ov-header p {
  margin: 7px 0 0;
  color: var(--ov-soft);
  font-size: 12px;
}

.ov-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ov-connection,
.ov-updated {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border-radius: 9px;
  border: 1px solid var(--ov-border);
  background: rgba(255,255,255,.025);
  color: var(--ov-soft);
  font-size: 10px;
  font-weight: 700;
}

.ov-connection span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 10px currentColor;
}

.ov-connection.good {
  color: var(--ov-green);
}

.ov-connection.bad {
  color: var(--ov-red);
}

.ov-updated {
  color: var(--ov-muted);
}

.ov-kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 10px;
}

.ov-kpi {
  position: relative;
  overflow: hidden;
  min-height: 96px;
  padding: 15px;
  border: 1px solid var(--ov-border);
  border-radius: 13px;
  background:
    linear-gradient(145deg, var(--ov-panel-2), #07111e);
  box-shadow: var(--ov-shadow);
}

.ov-kpi::after {
  content: "";
  position: absolute;
  width: 100px;
  height: 100px;
  right: -42px;
  bottom: -45px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(44,165,255,.18), transparent 68%);
}

.ov-kpi-label {
  display: block;
  color: var(--ov-muted);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.ov-kpi strong {
  display: block;
  margin-top: 7px;
  font-size: 28px;
  line-height: 1;
  letter-spacing: -.04em;
}

.ov-kpi small {
  display: block;
  margin-top: 6px;
  color: var(--ov-soft);
  font-size: 10px;
}

.ov-kpi.blue strong { color: var(--ov-blue); }
.ov-kpi.green strong { color: var(--ov-green); }
.ov-kpi.amber strong { color: var(--ov-amber); }
.ov-kpi.red strong { color: var(--ov-red); }
.ov-kpi.purple strong { color: var(--ov-purple); }

.ov-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(320px, .78fr);
  gap: 14px;
}

.ov-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.ov-panel {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--ov-border);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(10,23,38,.97), rgba(6,14,24,.97));
  box-shadow: var(--ov-shadow);
}

.ov-panel-header {
  min-height: 59px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--ov-border);
}

.ov-panel-header h2 {
  margin: 4px 0 0;
  font-size: 15px;
  letter-spacing: -.015em;
}

.ov-panel-count {
  color: var(--ov-blue);
  font-size: 19px;
}

.ov-live-stage {
  position: relative;
  min-height: 390px;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 45%, #17314a, #02070d 70%);
}

.ov-live-stage img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ov-live-empty {
  height: 100%;
  min-height: 390px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 6px;
  text-align: center;
  color: var(--ov-muted);
}

.ov-live-empty-orb {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  margin-bottom: 5px;
  border-radius: 18px;
  border: 1px solid var(--ov-border-strong);
  color: var(--ov-blue);
  background: rgba(44,165,255,.08);
  box-shadow: 0 0 30px rgba(44,165,255,.09);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: .08em;
}

.ov-live-empty strong {
  color: var(--ov-text);
  font-size: 14px;
}

.ov-live-empty span {
  font-size: 11px;
}

.ov-live-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(33,209,122,.10);
  color: var(--ov-green);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .08em;
}

.ov-live-status span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 10px currentColor;
}

.ov-live-overlay {
  position: absolute;
  top: 11px;
  left: 11px;
  right: 11px;
  display: flex;
  justify-content: space-between;
  gap: 6px;
  pointer-events: none;
}

.ov-live-overlay span {
  padding: 5px 8px;
  border-radius: 7px;
  border: 1px solid rgba(255,255,255,.09);
  background: rgba(4,10,18,.72);
  backdrop-filter: blur(10px);
  color: #dceaff;
  font-size: 9px;
  font-weight: 800;
}

.ov-live-footer {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  border-top: 1px solid var(--ov-border);
}

.ov-live-footer > div {
  padding: 10px 12px;
  border-right: 1px solid var(--ov-border);
}

.ov-live-footer > div:last-child {
  border-right: 0;
}

.ov-live-footer span {
  display: block;
  color: var(--ov-muted);
  font-size: 8px;
  font-weight: 800;
  letter-spacing: .08em;
}

.ov-live-footer strong {
  display: block;
  margin-top: 4px;
  color: var(--ov-text);
  font-size: 10px;
}

.ov-ai-grid {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 8px;
  padding: 10px 12px;
}

.ov-ai-stat {
  padding: 10px;
  border-radius: 9px;
  background: rgba(255,255,255,.025);
  border: 1px solid rgba(255,255,255,.06);
}

.ov-ai-stat span {
  display: block;
  color: var(--ov-muted);
  font-size: 8px;
  font-weight: 800;
  line-height: 1.3;
}

.ov-ai-stat strong {
  display: block;
  margin-top: 5px;
  font-size: 20px;
}

.ov-ai-stat.person strong { color: var(--ov-green); }
.ov-ai-stat.vehicle strong { color: var(--ov-red); }
.ov-ai-stat.tracking strong { color: var(--ov-purple); }

.ov-list {
  padding: 0 12px 10px;
}

.ov-list-item {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid rgba(255,255,255,.055);
}

.ov-list-item:last-child {
  border-bottom: 0;
}

.ov-list-item strong {
  display: block;
  color: var(--ov-text);
  font-size: 11px;
}

.ov-list-item span {
  display: block;
  margin-top: 3px;
  color: var(--ov-muted);
  font-size: 9px;
}

.ov-list-value {
  color: var(--ov-blue);
  font-size: 10px;
  font-weight: 800;
}

.ov-danger-count {
  min-width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(255,85,102,.10);
  color: var(--ov-red);
  font-size: 12px;
}

.ov-severity {
  padding: 4px 7px;
  border-radius: 6px;
  font-size: 8px;
  font-weight: 800;
  text-transform: uppercase;
}

.ov-severity.critical,
.ov-severity.high {
  background: rgba(255,85,102,.11);
  color: var(--ov-red);
}

.ov-severity.medium {
  background: rgba(255,188,61,.11);
  color: var(--ov-amber);
}

.ov-severity.low,
.ov-severity.info {
  background: rgba(44,165,255,.10);
  color: var(--ov-blue);
}

.ov-secondary-grid {
  display: grid;
  grid-template-columns: 1.1fr .9fr;
  gap: 14px;
}

.ov-search {
  width: 190px;
  min-height: 31px;
  padding: 0 9px;
  border-radius: 8px;
  border: 1px solid var(--ov-border);
  background: rgba(2,8,15,.65);
  color: var(--ov-text);
  outline: none;
  font-size: 10px;
}

.ov-search:focus {
  border-color: rgba(44,165,255,.42);
  box-shadow: 0 0 0 3px rgba(44,165,255,.08);
}

.ov-camera-grid {
  padding: 6px 12px 10px;
}

.ov-camera-row {
  display: grid;
  grid-template-columns: 8px minmax(0,1fr) auto;
  gap: 9px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,.05);
}

.ov-camera-row:last-child {
  border-bottom: 0;
}

.ov-camera-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ov-blue);
}

.ov-camera-info {
  min-width: 0;
}

.ov-camera-info strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.ov-camera-info span {
  display: block;
  margin-top: 3px;
  color: var(--ov-muted);
  font-size: 9px;
}

.ov-camera-state {
  padding: 5px 7px;
  border-radius: 6px;
  font-size: 8px;
  font-weight: 800;
}

.ov-camera-state.online,
.ov-camera-state.running {
  background: rgba(33,209,122,.10);
  color: var(--ov-green);
}

.ov-camera-state.offline {
  background: rgba(255,85,102,.10);
  color: var(--ov-red);
}

.ov-recording-list {
  padding: 3px 12px 10px;
}

.ov-recording-row {
  display: grid;
  grid-template-columns: 50px minmax(0,1fr) auto;
  gap: 9px;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid rgba(255,255,255,.05);
}

.ov-recording-row:last-child {
  border-bottom: 0;
}

.ov-recording-thumb {
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  border: 1px solid rgba(255,85,102,.18);
  background: rgba(255,85,102,.07);
  color: var(--ov-red);
  font-size: 8px;
  font-weight: 900;
}

.ov-recording-info {
  min-width: 0;
}

.ov-recording-info strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
}

.ov-recording-info span {
  display: block;
  margin-top: 3px;
  color: var(--ov-muted);
  font-size: 8px;
}

.ov-recording-meta {
  text-align: right;
}

.ov-recording-meta strong {
  display: block;
  color: var(--ov-green);
  font-size: 8px;
}

.ov-recording-meta span {
  display: block;
  margin-top: 3px;
  color: var(--ov-muted);
  font-size: 8px;
}

.ov-events-panel {
  margin-top: 0;
}

.ov-event-grid {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 0;
  padding: 0 12px 10px;
}

.ov-event-card {
  display: grid;
  grid-template-columns: 7px 1fr;
  gap: 8px;
  padding: 11px 8px;
  border-right: 1px solid rgba(255,255,255,.05);
}

.ov-event-card:nth-child(3n) {
  border-right: 0;
}

.ov-event-dot {
  width: 7px;
  height: 7px;
  margin-top: 4px;
  border-radius: 50%;
  background: var(--ov-blue);
  box-shadow: 0 0 10px rgba(44,165,255,.5);
}

.ov-event-card strong {
  font-size: 10px;
}

.ov-event-card p {
  margin: 4px 0 0;
  color: var(--ov-soft);
  font-size: 9px;
  line-height: 1.45;
}

.ov-event-card small {
  display: block;
  margin-top: 5px;
  color: var(--ov-muted);
  font-size: 8px;
}

.ov-health-panel {
  margin-top: 0;
}

.ov-health-badge {
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 8px;
  font-weight: 800;
}

.ov-health-badge.good {
  background: rgba(33,209,122,.1);
  color: var(--ov-green);
}

.ov-health-badge.bad {
  background: rgba(255,85,102,.1);
  color: var(--ov-red);
}

.ov-health-grid {
  display: grid;
  grid-template-columns: repeat(5,1fr);
  gap: 0;
  padding: 8px 12px 10px;
}

.ov-health-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px;
  border-right: 1px solid rgba(255,255,255,.05);
}

.ov-health-item:last-child {
  border-right: 0;
}

.ov-health-light {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--ov-muted);
}

.ov-health-light.good {
  background: var(--ov-green);
  box-shadow: 0 0 10px rgba(33,209,122,.55);
}

.ov-health-light.warn {
  background: var(--ov-amber);
}

.ov-health-light.bad {
  background: var(--ov-red);
}

.ov-health-item strong {
  display: block;
  font-size: 9px;
}

.ov-health-item span {
  display: block;
  margin-top: 3px;
  color: var(--ov-muted);
  font-size: 8px;
}

.ov-footer-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 11px 14px;
  border-radius: 11px;
  border: 1px solid var(--ov-border);
  background: rgba(8,17,29,.72);
}

.ov-footer-strip strong {
  font-size: 10px;
}

.ov-footer-strip span {
  margin-left: 13px;
  color: var(--ov-muted);
  font-size: 8px;
}

.ov-empty-row {
  padding: 18px 6px;
  color: var(--ov-muted);
  font-size: 10px;
  text-align: center;
}

.ov-loading {
  min-height: 65vh;
  display: grid;
  place-items: center;
}

.ov-loading-card,
.ov-error-card {
  width: min(430px,100%);
  padding: 30px;
  text-align: center;
  border-radius: 16px;
  border: 1px solid var(--ov-border);
  background: var(--ov-panel);
  box-shadow: var(--ov-shadow);
}

.ov-loading-orb,
.ov-error-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 13px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  border: 1px solid var(--ov-border-strong);
  color: var(--ov-blue);
  background: rgba(44,165,255,.08);
  font-size: 12px;
  font-weight: 900;
}

.ov-loading-card h2,
.ov-error-card h2 {
  margin: 0;
  font-size: 18px;
}

.ov-loading-card p,
.ov-error-card p {
  margin: 7px 0 0;
  color: var(--ov-muted);
  font-size: 11px;
}

.ov-error-icon {
  color: var(--ov-red);
  border-color: rgba(255,85,102,.35);
  background: rgba(255,85,102,.07);
  font-size: 20px;
}

.ov-error-card button {
  margin-top: 16px;
  min-height: 35px;
  padding: 0 14px;
  border: 1px solid var(--ov-border-strong);
  border-radius: 8px;
  background: rgba(44,165,255,.12);
  color: var(--ov-text);
  font-size: 10px;
  font-weight: 800;
  cursor: pointer;
}

@media (max-width: 1280px) {
  .ov-kpis {
    grid-template-columns: repeat(3,1fr);
  }

  .ov-main-grid,
  .ov-secondary-grid {
    grid-template-columns: 1fr;
  }

  .ov-health-grid {
    grid-template-columns: repeat(3,1fr);
  }
}

@media (max-width: 850px) {
  .ov-event-grid {
    grid-template-columns: 1fr 1fr;
  }

  .ov-health-grid {
    grid-template-columns: 1fr 1fr;
  }

  .ov-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .ov-header-actions {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 620px) {
  .ov-kpis {
    grid-template-columns: 1fr 1fr;
  }

  .ov-ai-grid,
  .ov-live-footer,
  .ov-event-grid,
  .ov-health-grid {
    grid-template-columns: 1fr;
  }

  .ov-event-card,
  .ov-health-item {
    border-right: 0;
    border-bottom: 1px solid rgba(255,255,255,.05);
  }

  .ov-event-card:last-child,
  .ov-health-item:last-child {
    border-bottom: 0;
  }

  .ov-search {
    width: 140px;
  }

  .ov-footer-strip {
    align-items: flex-start;
    flex-direction: column;
  }
}
''', encoding="utf-8")

print("PROFESSIONAL DASHBOARD V2 INSTALLED")
print("Overview.tsx + Overview.css updated.")
'@ | python

npm run build
