import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      '/api/session': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/api/product/recognize': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/api/product/vector-status': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      '/api': {
        target: 'http://localhost:8065',
        changeOrigin: true
      }
    }
  }
})
