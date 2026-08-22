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
  description: string
  location: string
  enabled: boolean
  recording_enabled: boolean
  ai_supported: boolean
  rtsp_supported: boolean
}

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
  return axios.delete(
    `${API}/cameras/${cameraId}/`,
    authConfig(token),
  )
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
