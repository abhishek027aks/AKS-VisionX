import axios from 'axios'

const API = '/api'

const auth = (token: string) => ({
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

export async function getApiList(
  token: string,
  endpoint: string,
) {
  const response = await axios.get(
    `${API}/${endpoint}`,
    auth(token),
  )

  const data = response.data

  if (Array.isArray(data)) {
    return data
  }

  return Array.isArray(data?.results)
    ? data.results
    : []
}

export async function getApiItem(
  token: string,
  endpoint: string,
) {
  const response = await axios.get(
    `${API}/${endpoint}`,
    auth(token),
  )

  return response.data
}
