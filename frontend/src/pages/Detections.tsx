import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  getDetections,
  type Detection,
} from '../services/detectionService'

function formatDate(
  value?: string | null,
) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleString()
}

function getToken() {
  return localStorage.getItem(
    'aks_token',
  ) || ''
}

function Detections() {
  const token = getToken()

  const [detections, setDetections] =
    useState<Detection[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [search, setSearch] =
    useState('')

  const [statusFilter, setStatusFilter] =
    useState('ALL')

  const [page, setPage] =
    useState(1)

  const pageSize = 25

  const loadDetections = useCallback(
    async () => {
      setLoading(true)
      setError('')

      try {
        const data =
          await getDetections(token)

        setDetections(data)
      } catch (err: any) {
        console.error(
          'DETECTIONS LOAD ERROR:',
          err,
        )

        setError(
          err?.response?.data?.detail ||
            'Unable to load detections.',
        )
      } finally {
        setLoading(false)
      }
    },
    [token],
  )

  useEffect(() => {
    void loadDetections()
  }, [loadDetections])

  const filtered = useMemo(() => {
    const query =
      search.trim().toLowerCase()

    return detections.filter(
      (item) => {
        const matchesSearch =
          !query ||
          String(
            item.label || '',
          )
            .toLowerCase()
            .includes(query) ||
          String(
            item.object_type || '',
          )
            .toLowerCase()
            .includes(query) ||
          String(
            item.tracking_id || '',
          )
            .toLowerCase()
            .includes(query) ||
          String(
            item.camera || '',
          ).includes(query)

        const matchesStatus =
          statusFilter === 'ALL' ||
          item.status === statusFilter

        return (
          matchesSearch &&
          matchesStatus
        )
      },
    )
  }, [
    detections,
    search,
    statusFilter,
  ])

  useEffect(() => {
    setPage(1)
  }, [
    search,
    statusFilter,
  ])

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        filtered.length /
          pageSize,
      ),
    )

  const safePage =
    Math.min(
      page,
      totalPages,
    )

  const visibleRows =
    filtered.slice(
      (safePage - 1) *
        pageSize,
      safePage *
        pageSize,
    )

  const objectCount =
    useMemo(() => {
      const counts =
        new Map<string, number>()

      for (const item of detections) {
        const label =
          item.label ||
          item.object_type ||
          'Unknown'

        counts.set(
          label,
          (counts.get(label) || 0) +
            1,
        )
      }

      return [...counts.entries()]
        .sort(
          (a, b) =>
            b[1] - a[1],
        )
        .slice(0, 6)
    }, [detections])

  const activeCount =
    detections.filter(
      (item) =>
        item.status ===
          'ACTIVE' ||
        item.status === 'OPEN',
    ).length

  const trackedCount =
    detections.filter(
      (item) =>
        Boolean(
          item.tracking_id,
        ),
    ).length

  const averageConfidence =
    detections.length
      ? detections.reduce(
          (sum, item) =>
            sum +
            Number(
              item.confidence || 0,
            ),
          0,
        ) /
        detections.length
      : 0

  if (!token) {
    return (
      <div className="page-placeholder">
        <div className="page-placeholder-icon">
          !
        </div>
        <h2>
          Authentication Required
        </h2>
        <p>
          Please login again.
        </p>
      </div>
    )
  }

  return (
    <div className="detections-page">
      <div className="camera-page-header">
        <div>
          <h2>
            AI Detections
          </h2>
          <p>
            Real-time object detection
            history from AKS VisionX.
          </p>
        </div>

        <div className="camera-header-actions">
          <button
            className="camera-refresh-button"
            onClick={() =>
              void loadDetections()
            }
            disabled={loading}
          >
            {loading
              ? 'Loading...'
              : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="camera-alert error">
          {error}
        </div>
      )}

      <div className="camera-summary">
        <div>
          <span>
            Total Detections
          </span>
          <strong>
            {detections.length}
          </strong>
        </div>

        <div>
          <span>
            Active
          </span>
          <strong className="summary-online">
            {activeCount}
          </strong>
        </div>

        <div>
          <span>
            Tracked
          </span>
          <strong>
            {trackedCount}
          </strong>
        </div>

        <div>
          <span>
            Avg Confidence
          </span>
          <strong className="summary-recording">
            {(
              averageConfidence *
              100
            ).toFixed(1)}
            %
          </strong>
        </div>
      </div>

      <div className="camera-grid-new">
        <section className="camera-card-new">
          <div className="camera-card-body">
            <h3>
              Detection Classes
            </h3>

            {objectCount.length ===
            0 ? (
              <p>
                No detections available.
              </p>
            ) : (
              objectCount.map(
                ([label, count]) => (
                  <div
                    key={label}
                    className="camera-test-result"
                  >
                    <strong>
                      {label}
                    </strong>

                    <span>
                      {' • '}
                      {count}
                    </span>
                  </div>
                ),
              )
            )}
          </div>
        </section>

        <section className="camera-card-new">
          <div className="camera-card-body">
            <h3>
              Filters
            </h3>

            <div className="camera-form-grid">
              <label>
                Search
                <input
                  value={search}
                  onChange={(event) =>
                    setSearch(
                      event.target.value,
                    )
                  }
                  placeholder="Person, car, tracking ID..."
                />
              </label>

              <label>
                Status
                <select
                  value={statusFilter}
                  onChange={(event) =>
                    setStatusFilter(
                      event.target.value,
                    )
                  }
                >
                  <option value="ALL">
                    All
                  </option>
                  <option value="ACTIVE">
                    Active
                  </option>
                  <option value="OPEN">
                    Open
                  </option>
                </select>
              </label>
            </div>
          </div>
        </section>
      </div>

      <section className="camera-card-new">
        <div className="camera-card-body">
          <div className="camera-name-row">
            <h3>
              Detection History
            </h3>

            <span>
              {filtered.length}
            </span>
          </div>

          {loading ? (
            <p>
              Loading detections...
            </p>
          ) : visibleRows.length ===
            0 ? (
            <p>
              No detections match
              the selected filters.
            </p>
          ) : (
            <div
              style={{
                overflowX:
                  'auto',
              }}
            >
              <table
                style={{
                  width: '100%',
                  borderCollapse:
                    'collapse',
                }}
              >
                <thead>
                  <tr>
                    <th>Object</th>
                    <th>Type</th>
                    <th>Confidence</th>
                    <th>Camera</th>
                    <th>Tracking ID</th>
                    <th>Status</th>
                    <th>Last Seen</th>
                  </tr>
                </thead>

                <tbody>
                  {visibleRows.map(
                    (item) => (
                      <tr
                        key={item.id}
                      >
                        <td>
                          <strong>
                            {item.label ||
                              item.object_type ||
                              'Unknown'}
                          </strong>
                        </td>

                        <td>
                          {item.object_type ||
                            '—'}
                        </td>

                        <td>
                          {item.confidence ==
                          null
                            ? '—'
                            : `${(
                                Number(
                                  item.confidence,
                                ) *
                                100
                              ).toFixed(
                                1,
                              )}%`}
                        </td>

                        <td>
                          {item.camera ??
                            '—'}
                        </td>

                        <td>
                          {item.tracking_id ||
                            '—'}
                        </td>

                        <td>
                          {item.status ||
                            '—'}
                        </td>

                        <td>
                          {formatDate(
                            item.last_seen_at,
                          )}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="camera-controls">
            <button
              className="camera-status-button"
              disabled={
                safePage <= 1
              }
              onClick={() =>
                setPage(
                  (value) =>
                    Math.max(
                      1,
                      value - 1,
                    ),
                )
              }
            >
              Previous
            </button>

            <span>
              Page {safePage} /{' '}
              {totalPages}
            </span>

            <button
              className="camera-status-button"
              disabled={
                safePage >=
                totalPages
              }
              onClick={() =>
                setPage(
                  (value) =>
                    Math.min(
                      totalPages,
                      value + 1,
                    ),
                )
              }
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Detections
