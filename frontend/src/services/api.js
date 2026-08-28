import axios from 'axios'

import { auth } from './firebase.js'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 15000,
})

api.interceptors.request.use(async (config) => {
  const currentUser = auth.currentUser

  if (currentUser) {
    const idToken = await currentUser.getIdToken()
    config.headers.Authorization = `Bearer ${idToken}`
  } else {
    delete config.headers.Authorization
  }

  return config
})

export default api
