import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  getApiList,
} from '../services/apiService'

function Tracking() {
  const token =
    localStorage.getItem('aks_token') || ''

  const [points, setPoints] =
    useState<any[]>([])

  const [locations, setLocations] =
    useState<any[]>([])

  const [visits, setVisits] =
    useState<any[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const [
        pointData,
        locationData,
        visitData,
      ] = await Promise.all([
        getApiList(
          token,
          'tracking-points/',
        ),
        getApiList(
          token,
          'tracking-locations/',
        ),
        getApiList(
          token,
          'tracking-camera-visits/',
        ),
      ])

      setPoints(pointData)
      setLocations(locationData)
      setVisits(visitData)
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to load tracking data.',
      )
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  const activeVisits = useMemo(
    () =>
      visits.filter(
        (item) => !item.exited_at,
      ),
    [visits],
  )

  const uniqueSessions = useMemo(
    () =>
      new Set(
        [
          ...points,
          ...locations,
          ...visits,
        ].map(
          (item) =>
            item.tracking_session,
        ),
      ).size,
    [points, locations, visits],
  )

  return (
    <div className="cameras-page">
      <div className="camera-page-header">
        <div>
          <h2>Object Tracking</h2>
          <p>
            Tracking sessions, movement
            points, locations and camera
            visits.
          </p>
        </div>

        <div className="camera-header-actions">
          <button
            className="camera-refresh-button"
            onClick={() => void load()}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="camera-summary">
        <div>
          <span>Sessions</span>
          <strong>
            {uniqueSessions}
          </strong>
        </div>

        <div>
          <span>Points</span>
          <strong>
            {points.length}
          </strong>
        </div>

        <div>
          <span>Locations</span>
          <strong>
            {locations.length}
          </strong>
        </div>

        <div>
          <span>Active Visits</span>
          <strong className="summary-online">
            {activeVisits.length}
          </strong>
        </div>
      </div>

      {loading ? (
        <div className="camera-empty">
          Loading tracking data...
        </div>
      ) : error ? (
        <div className="camera-alert error">
          {error}
        </div>
      ) : (
        <>
          <section className="camera-card-new">
            <div className="camera-card-body">
              <div className="camera-name-row">
                <h3>
                  Recent Camera Visits
                </h3>

                <span>
                  {visits.length}
                </span>
              </div>

              {visits.length === 0 ? (
                <p>
                  No camera visits recorded.
                </p>
              ) : (
                visits
                  .slice(0, 100)
                  .map((item) => (
                    <div
                      key={item.id}
                      className="camera-test-result"
                    >
                      <strong>
                        Camera{' '}
                        {item.camera ?? '—'}
                      </strong>

                      <div>
                        Tracking session:{' '}
                        {item.tracking_session ??
                          '—'}
                      </div>

                      <small>
                        {item.entered_at
                          ? new Date(
                              item.entered_at,
                            ).toLocaleString()
                          : '—'}
                        {' • '}
                        Detections:{' '}
                        {item.detection_count ??
                          0}
                      </small>
                    </div>
                  ))
              )}
            </div>
          </section>

          <section className="camera-card-new">
            <div className="camera-card-body">
              <div className="camera-name-row">
                <h3>
                  Recent Locations
                </h3>

                <span>
                  {locations.length}
                </span>
              </div>

              {locations.length === 0 ? (
                <p>
                  No tracking locations recorded.
                </p>
              ) : (
                locations
                  .slice(0, 100)
                  .map((item) => (
                    <div
                      key={item.id}
                      className="camera-test-result"
                    >
                      <strong>
                        {item.zone ||
                          'Unzoned'}
                      </strong>

                      <div>
                        Session:{' '}
                        {item.tracking_session ??
                          '—'}
                      </div>

                      <small>
                        Duration:{' '}
                        {item.duration_seconds ??
                          0}{' '}
                        sec
                      </small>
                    </div>
                  ))
              )}
            </div>
          </section>
        </>
      )}
    </div>
  )
}

export default Tracking
