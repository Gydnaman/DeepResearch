import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backend = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const proxy = {
  '/api': { target: backend, changeOrigin: true },
  '/docs': { target: backend, changeOrigin: true },
  '/openapi.json': { target: backend, changeOrigin: true },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: { host: '127.0.0.1', proxy },
  preview: { host: '0.0.0.0', port: 4173, proxy },
})
