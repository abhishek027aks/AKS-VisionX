import {
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
<<<<<<< HEAD
    animal_tracks: number
=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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

<<<<<<< HEAD
              <div className="ov-ai-stat animal">
                <span>ANIMAL TRACKS</span>
                <strong>
                  {counts.animal_tracks}
                </strong>
              </div>

=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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
