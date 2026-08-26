import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

import {
  deleteRecording,
  getRecordingDownloadUrl,
  getRecordingAIDetections,
  getRecordingVideoBlob,
  getRecordings,
  getStorageLocations,
  protectRecording,
  unprotectRecording,
  type Recording,
  type StorageLocation,
  type RecordingDetection,
} from '../services/recordingService'

import './Recordings.css'

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']

  let value = bytes
  let unit = 0

  while (
    value >= 1024 &&
    unit < units.length - 1
  ) {
    value /= 1024
    unit += 1
  }

  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`
}

function formatDuration(seconds: number | null) {
  if (
    seconds === null ||
    seconds === undefined
  ) {
    return '--'
  }

  const hours = Math.floor(
    seconds / 3600,
  )

  const minutes = Math.floor(
    (seconds % 3600) / 60,
  )

  const secs = Math.floor(
    seconds % 60,
  )

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(
      2,
      '0',
    )}:${String(secs).padStart(2, '0')}`
  }

  return `${String(minutes).padStart(
    2,
    '0',
  )}:${String(secs).padStart(2, '0')}`
}

function Recordings() {
  const token =
    localStorage.getItem('aks_token') || ''

  const [recordings, setRecordings] =
    useState<Recording[]>([])

  const [storage, setStorage] =
    useState<StorageLocation[]>([])

  const [loading, setLoading] =
    useState(true)

  const [busyId, setBusyId] =
    useState<number | null>(null)

  const [message, setMessage] =
    useState('')

  const [error, setError] =
    useState('')

  const [playerRecording, setPlayerRecording] =
    useState<Recording | null>(null)

  const [videoUrl, setVideoUrl] =
    useState('')

  const [detections, setDetections] =
    useState<RecordingDetection[]>([])

  const [aiOverlay, setAiOverlay] =
    useState(true)

  const [
    currentPersons,
    setCurrentPersons,
  ] = useState(0)

  const [
    currentVehicles,
    setCurrentVehicles,
  ] = useState(0)

  const videoRef =
    useRef<HTMLVideoElement | null>(null)

  const canvasRef =
    useRef<HTMLCanvasElement | null>(null)

  const animationRef =
    useRef<number | null>(null)

  const load = useCallback(
    async () => {
      if (!token) return

      setLoading(true)
      setError('')

      try {
        const [
          recordingData,
          storageData,
        ] = await Promise.all([
          getRecordings(token),
          getStorageLocations(token),
        ])

        setRecordings(recordingData)
        setStorage(storageData)
      } catch (err: any) {
        console.error(
          'RECORDINGS LOAD ERROR:',
          err,
        )

        if (
          err?.response?.status === 401
        ) {
          localStorage.removeItem(
            'aks_token',
          )

          window.location.reload()
          return
        }

        setError(
          err?.response?.data?.detail ||
            'Unable to load recordings.',
        )
      } finally {
        setLoading(false)
      }
    },
    [token],
  )

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(
          videoUrl,
        )
      }

      if (
        animationRef.current !== null
      ) {
        cancelAnimationFrame(
          animationRef.current,
        )
      }
    }
  }, [videoUrl])

  const drawOverlay =
    useCallback(() => {
      const video = videoRef.current
      const canvas = canvasRef.current

      if (!video || !canvas) return

      const context =
        canvas.getContext('2d')

      if (!context) return

      const width =
        video.videoWidth

      const height =
        video.videoHeight

      if (!width || !height) {
        return
      }

      canvas.width = width
      canvas.height = height

      context.clearRect(
        0,
        0,
        width,
        height,
      )

      if (!aiOverlay) {
        setCurrentPersons(0)
        setCurrentVehicles(0)
        return
      }

      if (!playerRecording) {
        return
      }

      const targetTime =
        new Date(
          playerRecording.started_at,
        ).getTime() +
        video.currentTime * 1000

      const windowMs = 800

      const nearby =
        detections.filter(
          (detection) => {
            const timestamp =
              new Date(
                detection.timestamp,
              ).getTime()

            return (
              Math.abs(
                timestamp -
                  targetTime,
              ) <= windowMs
            )
          },
        )

      const selected =
        new Map<string, RecordingDetection>()

      for (
        const detection of nearby
      ) {
        const key =
          detection.tracking_id
            ? `track:${detection.tracking_id}`
            : `id:${detection.id}`

        const existing =
          selected.get(key)

        if (!existing) {
          selected.set(
            key,
            detection,
          )
          continue
        }

        const currentDistance =
          Math.abs(
            new Date(
              existing.timestamp,
            ).getTime() -
              targetTime,
          )

        const nextDistance =
          Math.abs(
            new Date(
              detection.timestamp,
            ).getTime() -
              targetTime,
          )

        if (
          nextDistance <
          currentDistance
        ) {
          selected.set(
            key,
            detection,
          )
        }
      }

      const visible =
        Array.from(
          selected.values(),
        )

      let persons = 0
      let vehicles = 0

      for (
        const detection of visible
      ) {
        if (
          detection.object_type ===
          'PERSON'
        ) {
          persons += 1
        }

        if (
          detection.object_type ===
          'VEHICLE'
        ) {
          vehicles += 1
        }

        const x =
          detection.bbox_x *
          width

        const y =
          detection.bbox_y *
          height

        const boxWidth =
          detection.bbox_width *
          width

        const boxHeight =
          detection.bbox_height *
          height

        const isPerson =
          detection.object_type ===
          'PERSON'

        const isVehicle =
          detection.object_type ===
          'VEHICLE'

        const stroke =
          isPerson
            ? '#ff3030'
            : isVehicle
              ? '#38a8ff'
              : '#ffd34d'

        context.strokeStyle = stroke
        context.lineWidth = 3

        context.strokeRect(
          x,
          y,
          boxWidth,
          boxHeight,
        )

        const confidence =
          detection.confidence ===
          null
            ? ''
            : ` ${(
                detection.confidence *
                100
              ).toFixed(0)}%`

        const tracking =
          detection.tracking_id
            ? ` #${detection.tracking_id}`
            : ''

        const label =
          `${detection.label || detection.object_type}${confidence}${tracking}`

        context.font =
          'bold 16px Arial'

        const textWidth =
          context.measureText(
            label,
          ).width

        const labelHeight = 24

        context.fillStyle =
          stroke

        context.fillRect(
          x,
          Math.max(
            0,
            y - labelHeight,
          ),
          textWidth + 12,
          labelHeight,
        )

        context.fillStyle =
          '#ffffff'

        context.fillText(
          label,
          x + 6,
          Math.max(
            17,
            y - 7,
          ),
        )
      }

      setCurrentPersons(persons)
      setCurrentVehicles(
        vehicles,
      )
    }, [
      aiOverlay,
      detections,
      playerRecording,
    ])

  const animationLoop =
    useCallback(() => {
      drawOverlay()

      animationRef.current =
        requestAnimationFrame(
          animationLoop,
        )
    }, [drawOverlay])

  const handlePlay = () => {
    if (
      animationRef.current ===
      null
    ) {
      animationRef.current =
        requestAnimationFrame(
          animationLoop,
        )
    }
  }

  const handlePause = () => {
    if (
      animationRef.current !==
      null
    ) {
      cancelAnimationFrame(
        animationRef.current,
      )

      animationRef.current = null
    }

    drawOverlay()
  }

  const closePlayer = () => {
    if (
      animationRef.current !==
      null
    ) {
      cancelAnimationFrame(
        animationRef.current,
      )

      animationRef.current = null
    }

    if (videoUrl) {
      URL.revokeObjectURL(videoUrl)
    }

    setVideoUrl('')
    setDetections([])
    setPlayerRecording(null)
    setCurrentPersons(0)
    setCurrentVehicles(0)
  }

  const openPlayer =
    async (recording: Recording) => {
      setError('')
      setMessage('')

      try {
        closePlayer()

        const [
          blob,
          detectionData,
        ] = await Promise.all([
          getRecordingVideoBlob(
            token,
            recording.id,
          ),
          getRecordingAIDetections(
            token,
            recording.id,
          ),
        ])

        const url =
          URL.createObjectURL(blob)

        setPlayerRecording(
          recording,
        )

        setVideoUrl(url)

        setDetections(
          detectionData.detections,
        )
      } catch (err: any) {
        console.error(
          'RECORDING PLAYER ERROR:',
          err,
        )

        setError(
          err?.response?.data?.detail ||
            'Unable to open recording.',
        )
      }
    }

  const handleProtect =
    async (recording: Recording) => {
      setBusyId(recording.id)
      setError('')
      setMessage('')

      try {
        const updated =
          await protectRecording(
            token,
            recording.id,
            'Protected from Recording Manager',
          )

        setRecordings((current) =>
          current.map((item) =>
            item.id === updated.id
              ? updated
              : item,
          ),
        )

        setMessage(
          `Recording ${recording.id} protected.`,
        )
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            'Unable to protect recording.',
        )
      } finally {
        setBusyId(null)
      }
    }

  const handleUnprotect =
    async (recording: Recording) => {
      setBusyId(recording.id)
      setError('')
      setMessage('')

      try {
        const updated =
          await unprotectRecording(
            token,
            recording.id,
          )

        setRecordings((current) =>
          current.map((item) =>
            item.id === updated.id
              ? updated
              : item,
          ),
        )

        setMessage(
          `Recording ${recording.id} unprotected.`,
        )
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            'Unable to unprotect recording.',
        )
      } finally {
        setBusyId(null)
      }
    }

  const handleDelete =
    async (recording: Recording) => {
      if (recording.protected) {
        setError(
          'Unprotect the recording before deleting it.',
        )
        return
      }

      if (
        !window.confirm(
          `Delete "${recording.file_name}" permanently?`,
        )
      ) {
        return
      }

      setBusyId(recording.id)
      setError('')
      setMessage('')

      try {
        await deleteRecording(
          token,
          recording.id,
        )

        setRecordings((current) =>
          current.filter(
            (item) =>
              item.id !== recording.id,
          ),
        )

        if (
          playerRecording?.id ===
          recording.id
        ) {
          closePlayer()
        }

        setMessage(
          `Recording ${recording.id} deleted.`,
        )

        void load()
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ||
            'Unable to delete recording.',
        )
      } finally {
        setBusyId(null)
      }
    }

  const completed =
    recordings.filter(
      (item) =>
        item.status ===
        'COMPLETED',
    ).length

  const protectedCount =
    recordings.filter(
      (item) => item.protected,
    ).length

  const totalBytes =
    recordings.reduce(
      (sum, item) =>
        sum +
        Number(
          item.file_size_bytes || 0,
        ),
      0,
    )

  return (
    <div className="recordings-page">
      <div className="recordings-header">
        <div>
          <h2>Recordings</h2>

          <p>
            Recorded camera segments,
            storage management and AI
            playback.
          </p>
        </div>

        <button
          className="recordings-refresh"
          onClick={() =>
            void load()
          }
          disabled={loading}
        >
          Refresh
        </button>
      </div>

      <div className="recording-summary">
        <div>
          <span>Total</span>
          <strong>
            {recordings.length}
          </strong>
        </div>

        <div>
          <span>Completed</span>
          <strong>
            {completed}
          </strong>
        </div>

        <div>
          <span>Protected</span>
          <strong>
            {protectedCount}
          </strong>
        </div>

        <div>
          <span>Files</span>
          <strong>
            {formatBytes(totalBytes)}
          </strong>
        </div>
      </div>

      {storage.map((item) => (
        <div
          className="storage-card"
          key={item.id}
        >
          <div className="storage-title-row">
            <strong>
              {item.name}
            </strong>

            <span>
              {formatBytes(
                Number(
                  item.current_size_bytes,
                ),
              )}{' '}
              / {item.max_size_gb} GB
            </span>
          </div>

          <div className="storage-progress">
            <span
              style={{
                width: `${Math.min(
                  100,
                  Number(
                    item.usage_percent,
                  ),
                )}%`,
              }}
            />
          </div>

          <small>
            {Number(
              item.usage_percent,
            ).toFixed(2)}%
            {' '}used • Rolling storage{' '}
            {item.rolling_enabled
              ? 'ON'
              : 'OFF'}
          </small>
        </div>
      ))}

      {message && (
        <div className="recording-alert success">
          {message}
        </div>
      )}

      {error && (
        <div className="recording-alert error">
          {error}
        </div>
      )}

      {playerRecording && (
        <section className="recording-player-card">
          <div className="recording-player-header">
            <div>
              <h3>
                {playerRecording.file_name}
              </h3>

              <p>
                {playerRecording.camera_name}
              </p>
            </div>

            <div className="recording-player-actions">
              <span className="ai-count-pill">
                PERSONS:{' '}
                {currentPersons}
              </span>

              <span className="ai-count-pill">
                VEHICLES:{' '}
                {currentVehicles}
              </span>

              <button
                type="button"
                onClick={() =>
                  setAiOverlay(
                    (value) =>
                      !value,
                  )
                }
              >
                AI OVERLAY{' '}
                {aiOverlay
                  ? 'ON'
                  : 'OFF'}
              </button>

              <button
                type="button"
                onClick={
                  closePlayer
                }
              >
                Close
              </button>
            </div>
          </div>

          <div className="recording-video-stage">
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              playsInline
              onPlay={handlePlay}
              onPause={handlePause}
              onEnded={handlePause}
              onLoadedMetadata={() =>
                drawOverlay()
              }
              onTimeUpdate={() =>
                drawOverlay()
              }
              onSeeked={() =>
                drawOverlay()
              }
            />

            <canvas
              ref={canvasRef}
              className="recording-ai-canvas"
            />

            <div className="recording-ai-hud">
              PERSONS:{' '}
              {currentPersons}
              {'  '}
              VEHICLES:{' '}
              {currentVehicles}
            </div>
          </div>
        </section>
      )}

      {loading ? (
        <div className="recording-empty">
          Loading recordings...
        </div>
      ) : recordings.length ===
        0 ? (
        <div className="recording-empty">
          No recordings available.
        </div>
      ) : (
        <div className="recordings-table-wrap">
          <table className="recordings-table">
            <thead>
              <tr>
                <th>Camera</th>
                <th>File</th>
                <th>Started</th>
                <th>Duration</th>
                <th>Size</th>
                <th>Status</th>
                <th>Protected</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {recordings.map(
                (recording) => {
                  const busy =
                    busyId ===
                    recording.id

                  return (
                    <tr
                      key={
                        recording.id
                      }
                    >
                      <td>
                        <strong>
                          {
                            recording.camera_name
                          }
                        </strong>

                        <small>
                          ID{' '}
                          {
                            recording.camera
                          }
                        </small>
                      </td>

                      <td>
                        <strong>
                          {
                            recording.file_name
                          }
                        </strong>

                        {!recording.file_exists && (
                          <small className="missing-file">
                            File missing
                          </small>
                        )}
                      </td>

                      <td>
                        {new Date(
                          recording.started_at,
                        ).toLocaleString()}
                      </td>

                      <td>
                        {formatDuration(
                          recording.duration_seconds,
                        )}
                      </td>

                      <td>
                        {formatBytes(
                          Number(
                            recording.file_size_bytes,
                          ),
                        )}
                      </td>

                      <td>
                        <span className="recording-status">
                          {
                            recording.status
                          }
                        </span>
                      </td>

                      <td>
                        {recording.protected
                          ? 'YES'
                          : 'NO'}
                      </td>

                      <td>
                        <div className="recording-actions">
                          {recording.file_exists && (
                            <>
                              <button
                                type="button"
                                onClick={() =>
                                  void openPlayer(
                                    recording,
                                  )
                                }
                              >
                                AI Play
                              </button>

                              <a
                                href={getRecordingDownloadUrl(
                                  recording.id,
                                )}
                                className="recording-action-link"
                              >
                                Download
                              </a>
                            </>
                          )}

                          {recording.protected ? (
                            <button
                              disabled={busy}
                              onClick={() =>
                                void handleUnprotect(
                                  recording,
                                )
                              }
                            >
                              Unprotect
                            </button>
                          ) : (
                            <button
                              disabled={busy}
                              onClick={() =>
                                void handleProtect(
                                  recording,
                                )
                              }
                            >
                              Protect
                            </button>
                          )}

                          <button
                            className="danger"
                            disabled={
                              busy ||
                              recording.protected
                            }
                            onClick={() =>
                              void handleDelete(
                                recording,
                              )
                            }
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                },
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Recordings
