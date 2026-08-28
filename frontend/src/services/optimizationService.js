import api from './api.js'

export async function generateOptimizations(payload) {
  const response = await api.post('/api/optimizations/generate', payload, {
    timeout: 120000,
  })
  return response.data
}

export async function applyOptimizations(optimizationId, suggestions) {
  const decisions = suggestions.map((item) => ({
    id: item.id,
    status: item.status,
    edited_text: item.status === 'edited' ? item.suggested : null,
  }))
  const response = await api.patch(`/api/optimizations/${optimizationId}/apply`, { suggestions: decisions }, {
    timeout: 60000,
  })
  return response.data
}

export async function generateFinalResume(optimizationId) {
  const response = await api.post(`/api/optimizations/${optimizationId}/generate-pdf`, null, {
    timeout: 120000,
  })
  return response.data
}

export async function refreshPDFAccess(optimizationId) {
  const response = await api.get(`/api/optimizations/${optimizationId}/pdf-access`)
  return response.data
}

export async function getOptimization(optimizationId) {
  const response = await api.get(`/api/optimizations/${optimizationId}`)
  return response.data
}

export async function deleteOptimization(optimizationId) {
  await api.delete(`/api/optimizations/${optimizationId}`)
}
