import axios from 'axios'
import type { Camera, CameraStatus } from '../types/camera'

const API = '/api'

const authConfig = (token: string) => ({
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

export async function getCameras(token: string) {
  const response = await axios.get(
    `${API}/cameras/`,
    authConfig(token),
  )

  const data = Array.isArray(response.data)
    ? response.data
    : response.data.results || []

  return data as Camera[]
}

export async function getCameraStatus(
  token: string,
  cameraId: number,
) {
  const response = await axios.get(
    `${API}/cameras/${cameraId}/status/`,
    authConfig(token),
  )

  return response.data as CameraStatus
}

export async function getCameraLiveToken(
  token: string,
  cameraId: number,
) {
  const response = await axios.get(
    `${API}/cameras/${cameraId}/live-token/`,
    authConfig(token),
  )

  return response.data as {
    token: string
    expires_in: number
  }
}

export type CameraPayload = {
  name: string
  main_stream_url: string
  username: string
  credential_encrypted?: string
  connection_type: string
<<<<<<< HEAD
  host?: string
  port?: number | null
=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
  description: string
  location: string
  enabled: boolean
  recording_enabled: boolean
  ai_supported: boolean
  rtsp_supported: boolean
}

<<<<<<< HEAD
export type NewCameraConnectionPayload = {
  camera_type: string
  host?: string
  username?: string
  password?: string
  stream_url?: string
  port?: number
  device_index?: number
}

export type LocalCameraDevice = {
  device_index: number
  name: string
  stream_url: string
  width: number
  height: number
  fps: number
}

export type OnvifCameraDevice = {
  host: string
  port: number
  device_service_url: string
  name: string
}

export type CameraDiscoveryResult<T> = {
  devices: T[]
  message: string
  warning?: string
}

export type NewCameraConnectionResult = {
  success: boolean
  reachable: boolean
  protocol?: string
  stream_url?: string
  message: string
  error_code?: string
  fps?: number
  width?: number
  height?: number
}

export async function testNewCameraConnection(
  token: string,
  payload: NewCameraConnectionPayload,
) {
  const response = await axios.post(
    `${API}/cameras/test-connection/`,
    payload,
    authConfig(token),
  )

  return response.data as NewCameraConnectionResult
}

export async function discoverLocalCameras(token: string) {
  const response = await axios.post(
    `${API}/cameras/discover-local/`,
    {},
    authConfig(token),
  )

  return response.data as CameraDiscoveryResult<LocalCameraDevice>
}

export async function discoverOnvifCameras(token: string) {
  const response = await axios.post(
    `${API}/cameras/discover-onvif/`,
    {},
    authConfig(token),
  )

  return response.data as CameraDiscoveryResult<OnvifCameraDevice>
}

=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
export async function createCamera(
  token: string,
  payload: CameraPayload,
) {
  const response = await axios.post(
    `${API}/cameras/`,
    payload,
    authConfig(token),
  )

  return response.data as Camera
}

export async function updateCamera(
  token: string,
  cameraId: number,
  payload: CameraPayload,
) {
  const response = await axios.put(
    `${API}/cameras/${cameraId}/`,
    payload,
    authConfig(token),
  )

  return response.data as Camera
}

export async function deleteCamera(
  token: string,
  cameraId: number,
) {
<<<<<<< HEAD
  const response = await axios.delete(
    `${API}/cameras/${cameraId}/`,
    authConfig(token),
  )

  return response.data as {
    status?: string
    detail?: string
  } | undefined
=======
  return axios.delete(
    `${API}/cameras/${cameraId}/`,
    authConfig(token),
  )
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
}

export async function testCameraConnection(
  token: string,
  cameraId: number,
  streamUrl?: string,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/test-connection/`,
    streamUrl ? { stream_url: streamUrl } : {},
    authConfig(token),
  )

  return response.data as {
    status: string
    detail: string
    fps?: number
    width?: number
    height?: number
  }
}

export async function startCamera(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/start/`,
    {},
    authConfig(token),
  )

  return response.data
}

export async function stopCamera(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/stop/`,
    {},
    authConfig(token),
  )

  return response.data
}


export type PTZStatus = {
  camera_id: number
  supported: boolean
  onvif_supported: boolean
  ptz_supported: boolean
  pan?: number | null
  tilt?: number | null
  zoom?: number | null
}

export type PTZPreset = {
  token: string
  name: string
}

export async function detectCameraPTZ(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/ptz/detect/`,
    {},
    authConfig(token),
  )

  return response.data as {
    onvif_supported: boolean
    ptz_supported: boolean
  }
}

export async function getCameraPTZStatus(
  token: string,
  cameraId: number,
) {
  const response = await axios.get(
    `${API}/cameras/${cameraId}/ptz/status/`,
    authConfig(token),
  )

  return response.data as PTZStatus
}

export async function moveCameraPTZ(
  token: string,
  cameraId: number,
  pan = 0,
  tilt = 0,
  zoom = 0,
  timeout = 0.8,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/ptz/move/`,
    {
      pan,
      tilt,
      zoom,
      timeout,
    },
    authConfig(token),
  )

  return response.data
}

export async function stopCameraPTZ(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/ptz/stop/`,
    {},
    authConfig(token),
  )

  return response.data
}

export async function homeCameraPTZ(
  token: string,
  cameraId: number,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/ptz/home/`,
    {},
    authConfig(token),
  )

  return response.data
}

export async function getCameraPTZPresets(
  token: string,
  cameraId: number,
) {
  const response = await axios.get(
    `${API}/cameras/${cameraId}/ptz/presets/`,
    authConfig(token),
  )

  return response.data as {
    supported: boolean
    presets: PTZPreset[]
  }
}

export async function gotoCameraPTZPreset(
  token: string,
  cameraId: number,
  presetToken: string,
) {
  const response = await axios.post(
    `${API}/cameras/${cameraId}/ptz/preset/`,
    {
      token: presetToken,
    },
    authConfig(token),
  )

  return response.data
}
