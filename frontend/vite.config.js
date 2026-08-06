import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // No rewrite on any entry — the backend router prefixes are preserved as-is.
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/.well-known': { target: 'http://localhost:8000', changeOrigin: true },
      '/rpc': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
