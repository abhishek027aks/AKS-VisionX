export type Camera = {
  id: number
  name: string
  description?: string
  location?: string
  connection_type?: string
  host?: string
  port?: number | null
  username?: string
  status?: string
  running?: boolean
  recording?: boolean
  recording_id?: number | null
  recording_started_at?: string | null
  recording_enabled?: boolean
  ai_supported?: boolean
  enabled?: boolean
  last_seen?: string | null
  main_stream?: {
    id: number
    url: string
    fps?: number | string | null
    width?: number | null
    height?: number | null
  } | null
  fps?: number | string | null
  width?: number | null
  height?: number | null
}

export type CameraStatus = {
  status?: string
  running?: boolean
  recording?: boolean
  recording_id?: number | null
  recording_started_at?: string | null
  recording_enabled?: boolean
  ai_supported?: boolean
  enabled?: boolean
  last_seen?: string | null
  fps?: number | string | null
  width?: number | null
  height?: number | null
}
