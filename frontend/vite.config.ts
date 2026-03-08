import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/recommend': 'http://localhost:8000',
      '/usage': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
