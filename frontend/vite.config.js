import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { cwd } from 'node:process'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, cwd(), '')
  if (mode === 'production' && !env.VITE_API_BASE_URL?.trim()) {
    throw new Error('VITE_API_BASE_URL is required for production builds.')
  }
  return {
    plugins: [react()],
    server: { port: 5173 },
  }
})
