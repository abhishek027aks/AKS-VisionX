import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getApiList,
} from '../services/apiService'

function Alerts() {
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
          'alerts/',
        ),
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to load alerts.',
      )
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  const active = items.filter(
    (item) =>
      item.status === 'NEW' ||
      item.status === 'ACKNOWLEDGED',
  )

  return (
    <div className="cameras-page">
      <div className="camera-page-header">
        <div>
          <h2>Alerts</h2>
          <p>
            Security alerts and system
            notifications.
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
          <span>Total Alerts</span>
          <strong>{items.length}</strong>
        </div>

        <div>
          <span>Active</span>
          <strong className="summary-online">
            {active.length}
          </strong>
        </div>
      </div>

      {loading ? (
        <div className="camera-empty">
          Loading alerts...
        </div>
      ) : error ? (
        <div className="camera-alert error">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="camera-empty">
          <div className="camera-empty-icon">
            !
          </div>

          <h3>
            No alerts
          </h3>

          <p>
            No security alerts are currently
            stored in the system.
          </p>
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
                        `Alert #${item.id}`}
                    </h3>

                    <small>
                      {item.source ||
                        'SYSTEM'}
                    </small>
                  </div>

                  <span className="running-state running">
                    {item.severity ||
                      'INFO'}
                  </span>
                </div>

                <div className="camera-meta">
                  <div>
                    <span>Status</span>
                    <strong>
                      {item.status || 'NEW'}
                    </strong>
                  </div>

                  <div>
                    <span>Camera</span>
                    <strong>
                      {item.camera ?? '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Created</span>
                    <strong>
                      {item.created_at
                        ? new Date(
                            item.created_at,
                          ).toLocaleString()
                        : '—'}
                    </strong>
                  </div>
                </div>

                {item.message && (
                  <div className="camera-test-result">
                    {item.message}
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

export default Alerts
