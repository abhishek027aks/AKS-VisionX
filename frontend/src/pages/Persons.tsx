import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getApiList,
} from '../services/apiService'

function Persons() {
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
          'persons/',
        ),
      )
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Unable to load persons.',
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
          <h2>Persons</h2>
          <p>
            Known and detected person
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
          <span>Person Profiles</span>
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
          Loading persons...
        </div>
      ) : error ? (
        <div className="camera-alert error">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="camera-empty">
          No person profiles available.
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
                        `Person #${item.id}`}
                    </h3>

                    <small>
                      Person ID: {item.id}
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

                {item.notes && (
                  <div className="camera-test-result">
                    {item.notes}
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

export default Persons
