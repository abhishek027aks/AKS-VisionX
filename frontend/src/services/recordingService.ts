import axios from 'axios'

const API = '/api'

const authConfig = (token: string) => ({
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

export type Recording = {
  id: number
  organization: number
  camera: number
  camera_name: string
  stream: number | null
  storage_location: number | null
  storage_name: string | null
  file_name: string
  format: string
  status: string
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  file_size_bytes: number
  protected: boolean
  protection_reason: string
  file_exists: boolean
}

export type StorageLocation = {
  id: number
  organization: number
  name: string
  path: string
  storage_type: string
  enabled: boolean
  rolling_enabled: boolean
  max_size_gb: number | string
  current_size_bytes: number
  max_size_bytes: number
  usage_percent: number
  delete_oldest_unprotected: boolean
}

export async function getRecordings(token: string) {
  const response = await axios.get(
    `${API}/recordings/`,
    authConfig(token),
  )

  return (
    Array.isArray(response.data)
      ? response.data
      : response.data.results || []
  ) as Recording[]
}

export async function getStorageLocations(
  token: string,
) {
  const response = await axios.get(
    `${API}/storage-locations/`,
    authConfig(token),
  )

  return (
    Array.isArray(response.data)
      ? response.data
      : response.data.results || []
  ) as StorageLocation[]
}

export type StorageLocationPayload = {
  name: string
  path: string
  storage_type: string
  enabled: boolean
  rolling_enabled: boolean
  max_size_gb: number
  delete_oldest_unprotected: boolean
}

export async function createStorageLocation(
  token: string,
  payload: StorageLocationPayload,
) {
  const response = await axios.post(
    `${API}/storage-locations/`,
    payload,
    authConfig(token),
  )

  return response.data as StorageLocation
}

export async function updateStorageLocation(
  token: string,
  id: number,
  payload: StorageLocationPayload,
) {
  const response = await axios.put(
    `${API}/storage-locations/${id}/`,
    payload,
    authConfig(token),
  )

  return response.data as StorageLocation
}

export async function refreshStorageLocation(
  token: string,
  id: number,
) {
  const response = await axios.post(
    `${API}/storage-locations/${id}/refresh/`,
    {},
    authConfig(token),
  )

  return response.data as StorageLocation
}

export async function protectRecording(
  token: string,
  recordingId: number,
  reason = '',
) {
  const response = await axios.post(
    `${API}/recordings/${recordingId}/protect/`,
    { reason },
    authConfig(token),
  )

  return response.data as Recording
}

export async function unprotectRecording(
  token: string,
  recordingId: number,
) {
  const response = await axios.post(
    `${API}/recordings/${recordingId}/unprotect/`,
    {},
    authConfig(token),
  )

  return response.data as Recording
}

export async function deleteRecording(
  token: string,
  recordingId: number,
) {
  return axios.delete(
    `${API}/recordings/${recordingId}/`,
    authConfig(token),
  )
}

export function getRecordingDownloadUrl(
  recordingId: number,
) {
  return `${API}/recordings/${recordingId}/download/`
}


export type RecordingDetection = {
  id: number
  timestamp: string
  object_type: string
  label: string
  confidence: number | null
  tracking_id: string
  bbox_x: number
  bbox_y: number
  bbox_width: number
  bbox_height: number
}

export async function getRecordingVideoBlob(
  token: string,
  recordingId: number,
) {
  const response = await axios.get(
    getRecordingDownloadUrl(recordingId),
    {
      ...authConfig(token),
      responseType: 'blob',
    },
  )

  return response.data as Blob
}

export async function getRecordingAIDetections(
  token: string,
  recordingId: number,
) {
  const response = await axios.get(
    `${API}/recordings/${recordingId}/ai-detections/`,
    authConfig(token),
  )

  return response.data as {
    recording_id: number
    started_at: string
    ended_at: string | null
    detections: RecordingDetection[]
  }
}
