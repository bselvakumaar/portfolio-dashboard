import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/dashboard': 'http://127.0.0.1:8080',
      '/market': 'http://127.0.0.1:8080',
      '/portfolio': 'http://127.0.0.1:8080',
      '/run': 'http://127.0.0.1:8080',
      '/top-picks': 'http://127.0.0.1:8080',
      '/health': 'http://127.0.0.1:8080',
    },
  },
})
