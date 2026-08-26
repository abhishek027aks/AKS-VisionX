import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getApiList,
} from '../services/apiService'

function Vehicles() {
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
          'vehicles/',
        ),
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to load vehicles.',
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
          <h2>Vehicles</h2>
          <p>
            Known and detected vehicle
            profiles.
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
          <span>Vehicle Profiles</span>
          <strong>{items.length}</strong>
        </div>

        <div>
          <span>Known</span>
          <strong>
            {
              items.filter(
                (item) =>
                  item.is_known === true,
              ).length
            }
          </strong>
        </div>

        <div>
          <span>Active</span>
          <strong>
            {
              items.filter(
                (item) =>
                  item.is_active !== false,
              ).length
            }
          </strong>
        </div>
      </div>

      {loading ? (
        <div className="camera-empty">
          Loading vehicles...
        </div>
      ) : error ? (
        <div className="camera-alert error">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="camera-empty">
          No vehicle profiles available.
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
                      {item.name ||
                        `Vehicle #${item.id}`}
                    </h3>

                    <small>
                      Vehicle ID: {item.id}
                    </small>
                  </div>

                  <span className="running-state running">
                    {item.is_known
                      ? 'KNOWN'
                      : 'UNKNOWN'}
                  </span>
                </div>

                <div className="camera-meta">
                  <div>
                    <span>Type</span>
                    <strong>
                      {item.vehicle_type || '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Registration</span>
                    <strong>
                      {item.registration_number ||
                        '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Category</span>
                    <strong>
                      {item.category || '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Status</span>
                    <strong>
                      {item.is_active
                        ? 'Active'
                        : 'Inactive'}
                    </strong>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

export default Vehicles
