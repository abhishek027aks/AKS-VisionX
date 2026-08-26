import axios from 'axios'

const API = '/api'

const authConfig = (token: string) => ({
  headers: {
    Authorization: `Bearer ${token}`,
  },
})

export async function getDashboardSummary(
  token: string,
) {
  const response = await axios.get(
    `${API}/dashboard/summary/`,
    authConfig(token),
  )

  return response.data
}
