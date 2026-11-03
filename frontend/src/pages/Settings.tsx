import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from 'react'

import {
  createStorageLocation,
  getStorageLocations,
  refreshStorageLocation,
  updateStorageLocation,
  type StorageLocation,
  type StorageLocationPayload,
} from '../services/recordingService'

import './Settings.css'

const emptyForm: StorageLocationPayload = {
  name: 'Primary Recording Storage',
  path: 'E:\\AKS_VisionX_Recordings',
  storage_type: 'LOCAL_FOLDER',
  enabled: true,
  rolling_enabled: true,
  max_size_gb: 6,
  delete_oldest_unprotected: true,
}

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unit = 0

  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }

  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`
}

function Settings() {
  const token = localStorage.getItem('aks_token') || ''
  const [storage, setStorage] = useState<StorageLocation[]>([])
  const [selectedId, setSelectedId] = useState<number | 'new'>('new')
  const [form, setForm] = useState<StorageLocationPayload>(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const selectedStorage = useMemo(
    () => storage.find((item) => item.id === selectedId),
    [selectedId, storage],
  )

  const load = useCallback(async () => {
    if (!token) return

    setLoading(true)
    setError('')

    try {
      const data = await getStorageLocations(token)
      setStorage(data)

      if (data.length > 0 && selectedId === 'new') {
        const first = data[0]
        setSelectedId(first.id)
        setForm({
          name: first.name,
          path: first.path,
          storage_type: first.storage_type,
          enabled: first.enabled,
          rolling_enabled: first.rolling_enabled,
          max_size_gb: Number(first.max_size_gb),
          delete_oldest_unprotected: first.delete_oldest_unprotected,
        })
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to load settings.')
    } finally {
      setLoading(false)
    }
  }, [selectedId, token])

  useEffect(() => {
    void load()
  }, [load])

  const selectStorage = (item: StorageLocation | 'new') => {
    setMessage('')
    setError('')

    if (item === 'new') {
      setSelectedId('new')
      setForm(emptyForm)
      return
    }

    setSelectedId(item.id)
    setForm({
      name: item.name,
      path: item.path,
      storage_type: item.storage_type,
      enabled: item.enabled,
      rolling_enabled: item.rolling_enabled,
      max_size_gb: Number(item.max_size_gb),
      delete_oldest_unprotected: item.delete_oldest_unprotected,
    })
  }

  const save = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')

    try {
      const saved =
        selectedId === 'new'
          ? await createStorageLocation(token, form)
          : await updateStorageLocation(token, selectedId, form)

      setSelectedId(saved.id)
      setMessage('Storage settings saved and folder verified.')
      await load()
    } catch (err: any) {
      const data = err?.response?.data
      setError(
        data?.detail ||
          data?.path?.[0] ||
          data?.max_size_gb?.[0] ||
          'Unable to save storage settings.',
      )
    } finally {
      setSaving(false)
    }
  }

  const refreshSelected = async () => {
    if (selectedId === 'new') return

    setSaving(true)
    setMessage('')
    setError('')

    try {
      await refreshStorageLocation(token, selectedId)
      setMessage('Storage usage refreshed.')
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to refresh storage.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-page">
      <div className="settings-header">
        <div>
          <h2>Settings</h2>
          <p>Recording folder, quota, and rolling storage controls.</p>
        </div>

        <button onClick={() => selectStorage('new')}>
          New Storage
        </button>
      </div>

      {message && <div className="settings-alert success">{message}</div>}
      {error && <div className="settings-alert error">{error}</div>}

      <div className="settings-grid">
        <aside className="settings-list">
          <strong>Storage Locations</strong>

          {loading ? (
            <span className="settings-muted">Loading...</span>
          ) : storage.length === 0 ? (
            <span className="settings-muted">No storage configured.</span>
          ) : (
            storage.map((item) => (
              <button
                className={item.id === selectedId ? 'active' : ''}
                key={item.id}
                onClick={() => selectStorage(item)}
              >
                <span>{item.name}</span>
                <small>
                  {formatBytes(Number(item.current_size_bytes))} / {item.max_size_gb} GB
                </small>
              </button>
            ))
          )}
        </aside>

        <form className="settings-panel" onSubmit={save}>
          <label>
            Name
            <input
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              required
            />
          </label>

          <label>
            Recording Folder
            <input
              value={form.path}
              onChange={(event) =>
                setForm({ ...form, path: event.target.value })
              }
              placeholder="E:\\AKS_VisionX_Recordings"
              required
            />
          </label>

          <div className="settings-row">
            <label>
              Type
              <select
                value={form.storage_type}
                onChange={(event) =>
                  setForm({ ...form, storage_type: event.target.value })
                }
              >
                <option value="LOCAL_FOLDER">Local Folder</option>
                <option value="NETWORK_FOLDER">Network Folder</option>
                <option value="OTHER">Other</option>
              </select>
            </label>

            <label>
              Max Size GB
              <input
                min="0.1"
                step="0.1"
                type="number"
                value={form.max_size_gb}
                onChange={(event) =>
                  setForm({
                    ...form,
                    max_size_gb: Number(event.target.value),
                  })
                }
                required
              />
            </label>
          </div>

          <div className="settings-toggles">
            <label>
              <input
                checked={form.enabled}
                type="checkbox"
                onChange={(event) =>
                  setForm({ ...form, enabled: event.target.checked })
                }
              />
              Enabled
            </label>

            <label>
              <input
                checked={form.rolling_enabled}
                type="checkbox"
                onChange={(event) =>
                  setForm({ ...form, rolling_enabled: event.target.checked })
                }
              />
              Rolling storage
            </label>

            <label>
              <input
                checked={form.delete_oldest_unprotected}
                type="checkbox"
                onChange={(event) =>
                  setForm({
                    ...form,
                    delete_oldest_unprotected: event.target.checked,
                  })
                }
              />
              Delete oldest unprotected files
            </label>
          </div>

          {selectedStorage && (
            <div className="settings-usage">
              <span
                style={{
                  width: `${Math.min(100, Number(selectedStorage.usage_percent))}%`,
                }}
              />
              <small>
                {Number(selectedStorage.usage_percent).toFixed(2)}% used,
                {` ${formatBytes(Number(selectedStorage.current_size_bytes))}`}
              </small>
            </div>
          )}

          <div className="settings-actions">
            <button disabled={saving} type="submit">
              {saving ? 'Saving...' : 'Save Storage'}
            </button>

            <button
              disabled={saving || selectedId === 'new'}
              onClick={() => void refreshSelected()}
              type="button"
            >
              Refresh Usage
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Settings
