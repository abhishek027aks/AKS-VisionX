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
  connection_error?: string | null
  running?: boolean
  recording?: boolean
  recording_id?: number | null
  recording_started_at?: string | null
  recording_enabled?: boolean
  ai_supported?: boolean
  ai_animal_count?: number
  ai_animal_species_counts?: Record<string, number>
  ai_error?: string | null
  enabled?: boolean
  last_seen?: string | null
  main_stream?: {
    id: number
    url: string
    fps?: number | string | null
    width?: number | null
    height?: number | null

  onvif_supported?: boolean
  ptz_supported?: boolean

  ptz_capabilities?: {
    onvif: boolean
    ptz: boolean
    pan: boolean
    tilt: boolean
    zoom: boolean
    home: boolean
    presets: boolean
  }
  } | null
  fps?: number | string | null
  width?: number | null
  height?: number | null
}

export type CameraStatus = {
  status?: string
  connection_error?: string | null
  running?: boolean
  recording?: boolean
  recording_id?: number | null
  recording_started_at?: string | null
  recording_enabled?: boolean
  ai_supported?: boolean
  ai_animal_count?: number
  ai_animal_species_counts?: Record<string, number>
  ai_error?: string | null
  enabled?: boolean
  last_seen?: string | null
  fps?: number | string | null
  width?: number | null
  height?: number | null
}
