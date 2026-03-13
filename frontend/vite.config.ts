import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 9322,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9321',
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {},
    },
  },
})
