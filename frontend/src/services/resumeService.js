import api from './api.js'

export async function uploadResume(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/resumes/upload', formData, {
    timeout: 60000,
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress(Math.min(100, Math.round((event.loaded * 100) / event.total)))
      }
    },
  })

  return response.data
}

export async function parseResume(resumeId) {
  const response = await api.post(`/api/resumes/${encodeURIComponent(resumeId)}/parse`, null, {
    timeout: 120000,
  })
  return response.data
}

export async function listResumes() {
  const response = await api.get('/api/resumes')
  return response.data
}

export async function getResume(resumeId) {
  const response = await api.get(`/api/resumes/${encodeURIComponent(resumeId)}`)
  return response.data
}

export async function refreshResumePDFAccess(resumeId) {
  const response = await api.get(`/api/resumes/${encodeURIComponent(resumeId)}/pdf-access`)
  return response.data
}

export async function deleteResume(resumeId) {
  await api.delete(`/api/resumes/${encodeURIComponent(resumeId)}`)
}
