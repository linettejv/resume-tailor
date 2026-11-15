import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // Forward /api calls to the Flask backend so the browser sees one origin.
  server: { proxy: { '/api': 'http://127.0.0.1:5001' } },
})
