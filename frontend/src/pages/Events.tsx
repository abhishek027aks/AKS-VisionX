import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getApiList,
} from '../services/apiService'

function Events() {
  const token =
    localStorage.getItem('aks_token') || ''

  const [items, setItems] =
    useState<any[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      setItems(
        await getApiList(
          token,
          'events/',
        ),
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to load events.',
      )
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="cameras-page">
      <div className="camera-page-header">
        <div>
          <h2>Security Events</h2>
          <p>
            Real security events generated
            by the platform.
          </p>
        </div>

        <button
          className="camera-refresh-button"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>

      <div className="camera-summary">
        <div>
          <span>Total Events</span>
          <strong>{items.length}</strong>
        </div>
      </div>

      {loading ? (
        <div className="camera-empty">
          Loading events...
        </div>
      ) : error ? (
        <div className="camera-alert error">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="camera-empty">
          No security events recorded.
        </div>
      ) : (
        <div className="camera-grid-new">
          {items.map((item) => (
            <article
              key={item.id}
              className="camera-card-new"
            >
              <div className="camera-card-body">
                <div className="camera-name-row">
                  <div>
                    <h3>
                      {item.title ||
                        item.event_type ||
                        `Event #${item.id}`}
                    </h3>

                    <small>
                      Event #{item.id}
                    </small>
                  </div>

                  <span className="running-state running">
                    {item.status || 'NEW'}
                  </span>
                </div>

                <div className="camera-meta">
                  <div>
                    <span>Type</span>
                    <strong>
                      {item.event_type || '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Camera</span>
                    <strong>
                      {item.camera ?? '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Confidence</span>
                    <strong>
                      {item.confidence == null
                        ? '—'
                        : `${(
                            Number(
                              item.confidence,
                            ) * 100
                          ).toFixed(1)}%`}
                    </strong>
                  </div>

                  <div>
                    <span>Occurred</span>
                    <strong>
                      {item.occurred_at
                        ? new Date(
                            item.occurred_at,
                          ).toLocaleString()
                        : '—'}
                    </strong>
                  </div>
                </div>

                {item.description && (
                  <div className="camera-test-result">
                    {item.description}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

export default Events
