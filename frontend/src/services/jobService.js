import api from './api.js'

export async function analyzeJob(payload) {
  const response = await api.post('/api/jobs/analyze', payload, {
    timeout: 120000,
  })
  return response.data
}

export async function analyzeMatch(jobId) {
  const response = await api.post(`/api/jobs/${encodeURIComponent(jobId)}/match`, null, {
    timeout: 60000,
  })
  return response.data
}

export async function getJob(jobId) {
  const response = await api.get(`/api/jobs/${encodeURIComponent(jobId)}`)
  return response.data
}

export async function listJobs(resumeId) {
  const response = await api.get('/api/jobs', { params: resumeId ? { resume_id: resumeId } : {} })
  return response.data
}
