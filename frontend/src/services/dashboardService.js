import api from './api.js'

export async function getDashboardHistory() {
  const response = await api.get('/api/dashboard/history')
  return response.data
}
