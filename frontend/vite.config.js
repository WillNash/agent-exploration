import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In Docker the backend is reachable via the service name, not localhost.
// VITE_BACKEND_HOST is set to "backend" in docker-compose; falls back to
// "localhost" for running Vite directly on the host.
const backendHost = process.env.VITE_BACKEND_HOST || 'localhost'
const backendOrigin = `http://${backendHost}:8000`

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // No rewrite on any entry — the backend router prefixes are preserved as-is.
      '/api':         { target: backendOrigin, changeOrigin: true },
      '/auth':        { target: backendOrigin, changeOrigin: true },
      '/.well-known': { target: backendOrigin, changeOrigin: true },
      '/rpc':         { target: backendOrigin, changeOrigin: true },
    },
  },
})
