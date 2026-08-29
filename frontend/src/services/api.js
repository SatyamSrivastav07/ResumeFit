import axios from 'axios'
import { signOut } from 'firebase/auth'

import { auth } from './firebase.js'

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
if (!configuredBaseUrl) {
  throw new Error('VITE_API_BASE_URL is required.')
}

const api = axios.create({
  baseURL: configuredBaseUrl,
  timeout: 60000,
})

const STATUS_MESSAGES = {
  400: 'The request could not be completed.',
  401: 'Your session has expired. Please log in again.',
  403: 'You do not have permission to access this resource.',
  404: 'The requested item was not found.',
  413: 'The selected file or request is too large.',
  422: 'Please review the submitted information.',
  429: 'Too many requests. Please wait briefly and try again.',
  500: 'Something went wrong on the server.',
  502: 'An external service is temporarily unavailable.',
  503: 'The service is temporarily unavailable.',
  504: 'The request took too long. Please try again.',
}

export function getApiErrorMessage(error, fallback = 'Unable to complete this request.') {
  return error?.userMessage || error?.response?.data?.error?.message || STATUS_MESSAGES[error?.response?.status] || fallback
}

api.interceptors.request.use(async (config) => {
  const currentUser = auth.currentUser
  if (currentUser) {
    config.headers.Authorization = `Bearer ${await currentUser.getIdToken()}`
  } else {
    delete config.headers.Authorization
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && auth.currentUser && original && !original._authRetried) {
      original._authRetried = true
      try {
        original.headers.Authorization = `Bearer ${await auth.currentUser.getIdToken(true)}`
        return await api(original)
      } catch {
        await signOut(auth).catch(() => {})
        if (window.location.pathname !== '/login') window.location.assign('/login')
      }
    }
    error.userMessage = error.response?.data?.error?.message || STATUS_MESSAGES[error.response?.status] || (error.code === 'ECONNABORTED' ? 'The request took too long. Please try again.' : 'Unable to reach the service. Please check your connection.')
    return Promise.reject(error)
  },
)

export default api
