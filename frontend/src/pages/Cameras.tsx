import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import {
  createCamera,
  deleteCamera,
  getCameraLiveToken,
  getCameraStatus,
  getCameras,
  startCamera,
  stopCamera,
  testCameraConnection,
  updateCamera,
  moveCameraPTZ,
  stopCameraPTZ,
  homeCameraPTZ,
  gotoCameraPTZPreset,
  type CameraPayload,
  type PTZPreset,
} from '../services/cameraService'
import type { Camera } from '../types/camera'
import './Cameras.css'

type Rotation = 0 | 90 | 180 | 270

type DigitalView = {
  zoom: number
  panX: number
  panY: number
}

type PTZState = {
  supported: boolean
  onvif_supported: boolean
  ptz_supported: boolean
  pan?: number | null
  tilt?: number | null
  zoom?: number | null
}

const DEFAULT_DIGITAL_VIEW: DigitalView = {
  zoom: 1,
  panX: 0,
  panY: 0,
}

type CameraFormState = CameraPayload & {
  password: string
}

const emptyCameraForm: CameraFormState = {
  name: '',
  main_stream_url: '',
  username: '',
  password: '',
  connection_type: 'RTSP',
  description: '',
  location: '',
  enabled: true,
  recording_enabled: true,
  ai_supported: true,
  rtsp_supported: true,
}

function getMainStreamUrl(camera: Camera) {
  return camera.main_stream?.url || ''
}

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
  const [editingCamera, setEditingCamera] = useState<
    Camera | null
  >(null)
  const [showCameraForm, setShowCameraForm] = useState(false)
  const [form, setForm] = useState<CameraFormState>(
    emptyCameraForm,
  )
  const [savingCamera, setSavingCamera] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [testResults, setTestResults] = useState<
    Record<number, string>
  >({})

  const [digitalView, setDigitalView] = useState<
    Record<number, DigitalView>
  >({})

  const [ptzStatus] = useState<
    Record<number, PTZState>
  >({})

  const [ptzPresets] = useState<
    Record<number, PTZPreset[]>
  >({})

  const [ptzBusy, setPtzBusy] = useState<
    Record<number, boolean>
  >({})

  const previewRefs = useRef<
    Record<number, HTMLDivElement | null>
  >({})

  const dragRefs = useRef<
    Record<
      number,
      {
        startX: number
        startY: number
        panX: number
        panY: number
      }
    >
  >({})

  const clamp = (
    value: number,
    min: number,
    max: number,
  ) => Math.max(min, Math.min(max, value))

  const getDigitalView = (cameraId: number) =>
    digitalView[cameraId] || DEFAULT_DIGITAL_VIEW

  const setCameraDigitalView = (
    cameraId: number,
    next: Partial<DigitalView>,
  ) => {
    setDigitalView((current) => ({
      ...current,
      [cameraId]: {
        ...getDigitalView(cameraId),
        ...next,
      },
    }))
  }

  const zoomIn = (cameraId: number) => {
    const view = getDigitalView(cameraId)

    setCameraDigitalView(cameraId, {
      zoom: clamp(view.zoom + 0.25, 1, 4),
    })
  }

  const zoomOut = (cameraId: number) => {
    const view = getDigitalView(cameraId)

    const zoom = clamp(view.zoom - 0.25, 1, 4)

    setCameraDigitalView(cameraId, {
      zoom,
      panX:
        zoom === 1
          ? 0
          : view.panX,
      panY:
        zoom === 1
          ? 0
          : view.panY,
    })
  }

  const resetDigitalView = (cameraId: number) => {
    setCameraDigitalView(
      cameraId,
      DEFAULT_DIGITAL_VIEW,
    )
  }

  const moveDigital = (
    cameraId: number,
    x: number,
    y: number,
  ) => {
    const view = getDigitalView(cameraId)

    setCameraDigitalView(cameraId, {
      panX: clamp(view.panX + x, -35, 35),
      panY: clamp(view.panY + y, -35, 35),
    })
  }

  const ptzMove = async (
    cameraId: number,
    pan: number,
    tilt: number,
    zoom: number,
  ) => {
    setPtzBusy((current) => ({
      ...current,
      [cameraId]: true,
    }))

    try {
      await moveCameraPTZ(
        token,
        cameraId,
        pan,
        tilt,
        zoom,
        0.8,
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'PTZ movement failed.',
      )
    } finally {
      setPtzBusy((current) => ({
        ...current,
        [cameraId]: false,
      }))
    }
  }

  const ptzStop = async (
    cameraId: number,
  ) => {
    try {
      await stopCameraPTZ(
        token,
        cameraId,
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to stop PTZ.',
      )
    }
  }

  const ptzHome = async (
    cameraId: number,
  ) => {
    try {
      await homeCameraPTZ(
        token,
        cameraId,
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to move camera home.',
      )
    }
  }

  const ptzPreset = async (
    cameraId: number,
    presetToken: string,
  ) => {
    try {
      await gotoCameraPTZPreset(
        token,
        cameraId,
        presetToken,
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to move to preset.',
      )
    }
  }

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

  const handlePreviewWheel = (
    event: React.WheelEvent,
    cameraId: number,
  ) => {
    event.preventDefault()

    const view =
      digitalView[cameraId] ||
      DEFAULT_DIGITAL_VIEW

    const delta =
      event.deltaY < 0
        ? 0.15
        : -0.15

    const zoom = clamp(
      view.zoom + delta,
      1,
      4,
    )

    setCameraDigitalView(
      cameraId,
      {
        zoom,
        panX:
          zoom === 1
            ? 0
            : view.panX,
        panY:
          zoom === 1
            ? 0
            : view.panY,
      },
    )
  }

  const handlePreviewPointerDown = (
    event: React.PointerEvent,
    cameraId: number,
  ) => {
    const view =
      digitalView[cameraId] ||
      DEFAULT_DIGITAL_VIEW

    if (view.zoom <= 1) {
      return
    }

    ;(
      event.currentTarget as HTMLElement
    ).setPointerCapture(event.pointerId)

    dragRefs.current[cameraId] = {
      startX: event.clientX,
      startY: event.clientY,
      panX: view.panX,
      panY: view.panY,
    }
  }

  const handlePreviewPointerMove = (
    event: React.PointerEvent,
    cameraId: number,
  ) => {
    const drag =
      dragRefs.current[cameraId]

    if (!drag) {
      return
    }

    const element =
      previewRefs.current[cameraId]

    if (!element) {
      return
    }

    const rect =
      element.getBoundingClientRect()

    const sensitivity =
      Math.max(
        0.35,
        (digitalView[cameraId]?.zoom || 1) *
          0.6,
      )

    const dx =
      ((event.clientX - drag.startX) /
        Math.max(rect.width, 1)) *
      100 *
      sensitivity

    const dy =
      ((event.clientY - drag.startY) /
        Math.max(rect.height, 1)) *
      100 *
      sensitivity

    setCameraDigitalView(
      cameraId,
      {
        panX: clamp(
          drag.panX + dx,
          -35,
          35,
        ),
        panY: clamp(
          drag.panY + dy,
          -35,
          35,
        ),
      },
    )
  }

  const handlePreviewPointerUp = (
    event: React.PointerEvent,
    cameraId: number,
  ) => {
    delete dragRefs.current[cameraId]

    try {
      ;(
        event.currentTarget as HTMLElement
      ).releasePointerCapture(event.pointerId)
    } catch {
      // Pointer may already have been released.
    }
  }

  const handlePreviewDoubleClick = (
    event: React.MouseEvent,
    cameraId: number,
  ) => {
    event.preventDefault()
    resetDigitalView(cameraId)
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

  const openAddForm = () => {
    setEditingCamera(null)
    setForm(emptyCameraForm)
    setShowCameraForm(true)
    setMessage('')
    setError('')
  }

  const openEditForm = (camera: Camera) => {
    setEditingCamera(camera)
    setForm({
      name: camera.name || '',
      main_stream_url: getMainStreamUrl(camera),
      username: camera.username || '',
      password: '',
      connection_type: camera.connection_type || 'RTSP',
      description: camera.description || '',
      location: camera.location || '',
      enabled: camera.enabled !== false,
      recording_enabled: camera.recording_enabled !== false,
      ai_supported: camera.ai_supported === true,
      rtsp_supported: true,
    })
    setShowCameraForm(true)
    setMessage('')
    setError('')
  }

  const validateForm = () => {
    if (!form.name.trim()) {
      return 'Camera name is required.'
    }

    if (!form.main_stream_url.trim()) {
      return 'RTSP/stream URL is required.'
    }

    if (
      !/^((rtsp|http|https):\/\/).+/i.test(
        form.main_stream_url.trim(),
      )
    ) {
      return 'Stream URL must start with rtsp://, http://, or https://.'
    }

    return ''
  }

  const cameraPayload = () => {
    const streamUrl = form.main_stream_url.trim()
    const payload: CameraPayload = {
      name: form.name.trim(),
      main_stream_url: streamUrl,
      username: form.username.trim(),
      connection_type: form.connection_type,
      description: form.description.trim(),
      location: form.location.trim(),
      enabled: form.enabled,
      recording_enabled: form.recording_enabled,
      ai_supported: form.ai_supported,
      rtsp_supported:
        form.connection_type === 'RTSP' ||
        streamUrl.toLowerCase().startsWith('rtsp://'),
    }

    if (form.password) {
      payload.credential_encrypted = form.password
    }

    return payload
  }

  const saveCamera = async (event: FormEvent) => {
    event.preventDefault()

    const validationError = validateForm()

    if (validationError) {
      setError(validationError)
      return
    }

    setSavingCamera(true)
    setMessage('')
    setError('')

    try {
      const saved = editingCamera
        ? await updateCamera(
            token,
            editingCamera.id,
            cameraPayload(),
          )
        : await createCamera(token, cameraPayload())

      setMessage(
        `${saved.name || 'Camera'} ${
          editingCamera ? 'updated' : 'added'
        } successfully.`,
      )
      setShowCameraForm(false)
      setEditingCamera(null)
      setForm(emptyCameraForm)
      await loadCameras()
    } catch (err: any) {
      const data = err?.response?.data
      setError(
        data?.detail ||
          data?.name?.[0] ||
          data?.main_stream_url?.[0] ||
          data?.organization?.[0] ||
          'Unable to save camera.',
      )
    } finally {
      setSavingCamera(false)
    }
  }

  const handleTestConnection = async (
    camera: Camera,
    streamUrl?: string,
  ) => {
    setTestingId(camera.id)
    setError('')
    setTestResults((current) => ({
      ...current,
      [camera.id]: 'Testing...',
    }))

    try {
      const result = await testCameraConnection(
        token,
        camera.id,
        streamUrl,
      )

      setTestResults((current) => ({
        ...current,
        [camera.id]: `${result.status}: ${result.detail}`,
      }))

      await refreshStatus([camera])
    } catch (err: any) {
      setTestResults((current) => ({
        ...current,
        [camera.id]:
          err?.response?.data?.detail ||
          'Connection test failed.',
      }))
    } finally {
      setTestingId(null)
    }
  }

  const handleDeleteCamera = async (camera: Camera) => {
    if (
      !window.confirm(
        `Remove "${camera.name}"? Existing recordings and events will remain in history.`,
      )
    ) {
      return
    }

    setActionId(camera.id)
    setMessage('')
    setError('')

    try {
      if (camera.running) {
        await stopCamera(token, camera.id)
      }

      await deleteCamera(token, camera.id)
      setMessage(`${camera.name} removed. Recordings were not deleted.`)
      await loadCameras()
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to delete camera.',
      )
    } finally {
      setActionId(null)
    }
  }

  const online = cameras.filter(
    (camera) => camera.status === 'ONLINE',
  ).length

  const running = cameras.filter(
    (camera) => camera.running === true,
  ).length

  const recording = cameras.filter(
    (camera) => camera.recording === true,
  ).length

  const getLiveUrl = (
    cameraId: number,
    liveToken: string,
  ) => {
    const version = streamVersion[cameraId] || 0
    const backendOrigin =
      import.meta.env.VITE_API_ORIGIN ||
      'http://127.0.0.1:8000'

    return `${backendOrigin}/api/cameras/${cameraId}/live/?access_token=${encodeURIComponent(
      liveToken,
    )}&ai_overlay=1&v=${version}`
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

        <div className="camera-header-actions">
          <button
            className="camera-refresh-button"
            onClick={loadCameras}
            disabled={loading}
          >
            Refresh
          </button>

          <button
            className="camera-add-button"
            onClick={openAddForm}
          >
            + Add Camera
          </button>
        </div>
      </div>

      {showCameraForm && (
        <form className="camera-form" onSubmit={saveCamera}>
          <div className="camera-form-header">
            <div>
              <h3>
                {editingCamera ? 'Edit Camera' : 'Add Camera'}
              </h3>
              <p>
                Configure camera details and its main stream.
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowCameraForm(false)}
            >
              Close
            </button>
          </div>

          <div className="camera-form-grid">
            <label>
              Camera name
              <input
                value={form.name}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
                required
              />
            </label>

            <label>
              Protocol/type
              <select
                value={form.connection_type}
                onChange={(event) =>
                  setForm({
                    ...form,
                    connection_type: event.target.value,
                  })
                }
              >
                <option value="RTSP">RTSP</option>
                <option value="ONVIF">ONVIF</option>
                <option value="NVR">NVR</option>
                <option value="LOCAL">Local</option>
                <option value="OTHER">Other</option>
              </select>
            </label>

            <label className="wide">
              RTSP/stream URL
              <input
                value={form.main_stream_url}
                onChange={(event) =>
                  setForm({
                    ...form,
                    main_stream_url: event.target.value,
                  })
                }
                placeholder="rtsp://camera-host/stream"
                required
              />
            </label>

            <label>
              Username
              <input
                value={form.username}
                onChange={(event) =>
                  setForm({
                    ...form,
                    username: event.target.value,
                  })
                }
                autoComplete="off"
              />
            </label>

            <label>
              Password
              <input
                value={form.password}
                onChange={(event) =>
                  setForm({
                    ...form,
                    password: event.target.value,
                  })
                }
                placeholder={
                  editingCamera
                    ? 'Leave blank to keep saved password'
                    : ''
                }
                type="password"
                autoComplete="new-password"
              />
            </label>

            <label>
              Location
              <input
                value={form.location}
                onChange={(event) =>
                  setForm({
                    ...form,
                    location: event.target.value,
                  })
                }
              />
            </label>

            <label className="wide">
              Description
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm({
                    ...form,
                    description: event.target.value,
                  })
                }
                rows={3}
              />
            </label>
          </div>

          <div className="camera-form-toggles">
            <label>
              <input
                checked={form.enabled}
                type="checkbox"
                onChange={(event) =>
                  setForm({
                    ...form,
                    enabled: event.target.checked,
                  })
                }
              />
              Enabled
            </label>

            <label>
              <input
                checked={form.recording_enabled}
                type="checkbox"
                onChange={(event) =>
                  setForm({
                    ...form,
                    recording_enabled: event.target.checked,
                  })
                }
              />
              Recording
            </label>

            <label>
              <input
                checked={form.ai_supported}
                type="checkbox"
                onChange={(event) =>
                  setForm({
                    ...form,
                    ai_supported: event.target.checked,
                  })
                }
              />
              AI processing
            </label>
          </div>

          <div className="camera-form-actions">
            <button disabled={savingCamera} type="submit">
              {savingCamera ? 'Saving...' : 'Save Camera'}
            </button>
          </div>
        </form>
      )}

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

        <div>
          <span>Recording</span>
          <strong className="summary-recording">
            {recording}
          </strong>
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
            Add a camera to start live monitoring.
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

            const view =
              digitalView[camera.id] ||
              DEFAULT_DIGITAL_VIEW

            const cameraPTZ =
              ptzStatus[camera.id]

            const hasPhysicalPTZ =
              cameraPTZ?.ptz_supported === true

            const cameraPTZBusy =
              ptzBusy[camera.id] === true

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
                  onWheel={(event) =>
                    handlePreviewWheel(
                      event,
                      camera.id,
                    )
                  }
                  onPointerDown={(event) =>
                    handlePreviewPointerDown(
                      event,
                      camera.id,
                    )
                  }
                  onPointerMove={(event) =>
                    handlePreviewPointerMove(
                      event,
                      camera.id,
                    )
                  }
                  onPointerUp={(event) =>
                    handlePreviewPointerUp(
                      event,
                      camera.id,
                    )
                  }
                  onPointerCancel={(event) =>
                    handlePreviewPointerUp(
                      event,
                      camera.id,
                    )
                  }
                  onDoubleClick={(event) =>
                    handlePreviewDoubleClick(
                      event,
                      camera.id,
                    )
                  }
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
                        transform:
                          `translate(${view.panX}%, ${view.panY}%) ` +
                          `rotate(${cameraRotation}deg) ` +
                          `scale(${view.zoom})`,
                        transformOrigin: 'center center',
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
                      LEFT
                    </button>

                    <span>
                      {cameraRotation} deg
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
                      RIGHT
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
                      RETRY
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
                        ? 'FULL'
                        : 'FULL'}
                    </button>
                  </div>

                  <div className="camera-digital-controls">
                    <div className="camera-control-group">
                      <strong>DIGITAL VIEW</strong>

                      <button
                        type="button"
                        onClick={() =>
                          moveDigital(
                            camera.id,
                            0,
                            -6,
                          )
                        }
                      >
                        UP
                      </button>

                      <div>
                        <button
                          type="button"
                          onClick={() =>
                            moveDigital(
                              camera.id,
                              -6,
                              0,
                            )
                          }
                        >
                          LEFT
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            resetDigitalView(
                              camera.id,
                            )
                          }
                        >
                          RESET
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            moveDigital(
                              camera.id,
                              6,
                              0,
                            )
                          }
                        >
                          RIGHT
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          moveDigital(
                            camera.id,
                            0,
                            6,
                          )
                        }
                      >
                        DOWN
                      </button>

                      <div className="camera-zoom-row">
                        <button
                          type="button"
                          onClick={() =>
                            zoomOut(camera.id)
                          }
                        >
                          ZOOM -
                        </button>

                        <span>
                          {Math.round(
                            view.zoom * 100,
                          )}%
                        </span>

                        <button
                          type="button"
                          onClick={() =>
                            zoomIn(camera.id)
                          }
                        >
                          ZOOM +
                        </button>
                      </div>
                    </div>

                    <div
                      className={`camera-control-group camera-ptz-group ${
                        hasPhysicalPTZ
                          ? 'ptz-supported'
                          : 'ptz-unavailable'
                      }`}
                    >
                      <strong>
                        {hasPhysicalPTZ
                          ? 'PHYSICAL PTZ'
                          : 'PTZ'}
                      </strong>

                      {hasPhysicalPTZ ? (
                        <>
                          <button
                            type="button"
                            disabled={
                              cameraPTZBusy
                            }
                            onClick={() =>
                              void ptzMove(
                                camera.id,
                                0,
                                0.7,
                                0,
                              )
                            }
                          >
                            UP
                          </button>

                          <div>
                            <button
                              type="button"
                              disabled={
                                cameraPTZBusy
                              }
                              onClick={() =>
                                void ptzMove(
                                  camera.id,
                                  -0.7,
                                  0,
                                  0,
                                )
                              }
                            >
                              LEFT
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                void ptzStop(
                                  camera.id,
                                )
                              }
                            >
                              STOP
                            </button>

                            <button
                              type="button"
                              disabled={
                                cameraPTZBusy
                              }
                              onClick={() =>
                                void ptzMove(
                                  camera.id,
                                  0.7,
                                  0,
                                  0,
                                )
                              }
                            >
                              RIGHT
                            </button>
                          </div>

                          <button
                            type="button"
                            disabled={
                              cameraPTZBusy
                            }
                            onClick={() =>
                              void ptzMove(
                                camera.id,
                                0,
                                -0.7,
                                0,
                              )
                            }
                          >
                            DOWN
                          </button>

                          <div className="camera-zoom-row">
                            <button
                              type="button"
                              disabled={
                                cameraPTZBusy
                              }
                              onClick={() =>
                                void ptzMove(
                                  camera.id,
                                  0,
                                  0,
                                  -0.7,
                                )
                              }
                            >
                              ZOOM -
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                void ptzHome(
                                  camera.id,
                                )
                              }
                            >
                              HOME
                            </button>

                            <button
                              type="button"
                              disabled={
                                cameraPTZBusy
                              }
                              onClick={() =>
                                void ptzMove(
                                  camera.id,
                                  0,
                                  0,
                                  0.7,
                                )
                              }
                            >
                              ZOOM +
                            </button>
                          </div>

                          {(
                            ptzPresets[
                              camera.id
                            ] || []
                          ).length > 0 && (
                            <select
                              defaultValue=""
                              onChange={(
                                event,
                              ) => {
                                const value =
                                  event.target
                                    .value

                                if (value) {
                                  void ptzPreset(
                                    camera.id,
                                    value,
                                  )

                                  event.target.value =
                                    ''
                                }
                              }}
                            >
                              <option value="">
                                PRESET
                              </option>

                              {(
                                ptzPresets[
                                  camera.id
                                ] || []
                              ).map(
                                (preset) => (
                                  <option
                                    key={
                                      preset.token
                                    }
                                    value={
                                      preset.token
                                    }
                                  >
                                    {preset.name ||
                                      preset.token}
                                  </option>
                                ),
                              )}
                            </select>
                          )}
                        </>
                      ) : (
                        <span className="camera-ptz-unavailable">
                          Physical PTZ not supported
                        </span>
                      )}
                    </div>
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

                  <div
                    className={`recording-state ${
                      camera.recording
                        ? 'recording'
                        : 'idle'
                    }`}
                  >
                    <span />
                    {camera.recording
                      ? `Recording${camera.recording_id ? ` #${camera.recording_id}` : ''}`
                      : isRunning
                        ? 'Waiting for storage/frame'
                        : 'Recording idle'}
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

                    <div>
                      <span>Recording Since</span>

                      <strong>
                        {camera.recording_started_at
                          ? new Date(
                              camera.recording_started_at,
                            ).toLocaleString()
                          : 'Not active'}
                      </strong>
                    </div>

                    <div>
                      <span>Stream</span>

                      <strong>
                        {camera.width && camera.height
                          ? `${camera.width}x${camera.height}`
                          : 'Unknown'}
                        {camera.fps
                          ? ` @ ${Number(camera.fps).toFixed(1)} FPS`
                          : ''}
                      </strong>
                    </div>

                    <div>
                      <span>AI</span>

                      <strong>
                        {camera.ai_supported
                          ? 'Enabled'
                          : 'Disabled'}
                      </strong>
                    </div>
                  </div>

                  {testResults[camera.id] && (
                    <div className="camera-test-result">
                      {testResults[camera.id]}
                    </div>
                  )}

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

                    <button
                      className="camera-status-button"
                      disabled={testingId === camera.id}
                      onClick={() =>
                        void handleTestConnection(camera)
                      }
                    >
                      {testingId === camera.id
                        ? 'Testing...'
                        : 'Test'}
                    </button>

                    <button
                      className="camera-status-button"
                      onClick={() => openEditForm(camera)}
                    >
                      Edit
                    </button>

                    <button
                      className="camera-delete"
                      disabled={busy}
                      onClick={() =>
                        void handleDeleteCamera(camera)
                      }
                    >
                      Delete
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
