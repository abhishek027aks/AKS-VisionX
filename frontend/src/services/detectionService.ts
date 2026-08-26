import axios from 'axios'

const API = '/api'

const authConfig = (token: string) => ({
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

export type Detection = {
  id: number
  organization?: number
  camera?: number
  event?: number | null
  object_type?: string
  label?: string
  confidence?: number | string | null
  tracking_id?: string | null
  status?: string
  first_seen_at?: string | null
  last_seen_at?: string | null
  bbox_x?: number | null
  bbox_y?: number | null
  bbox_width?: number | null
  bbox_height?: number | null
  metadata?: Record<string, any> | null
  created_at?: string
  updated_at?: string
}

export async function getDetections(
  token: string,
) {
  const response = await axios.get(
    `${API}/detections/`,
    authConfig(token),
  )

  const data = Array.isArray(response.data)
    ? response.data
    : response.data.results || []

  return data as Detection[]
}
