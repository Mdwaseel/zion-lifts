import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(process.cwd(), 'src') },
  },
  server: {
    port: 5173,
    proxy: {
      // the Django API and its uploaded media, so the app is same-origin in dev
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  // `vite preview` would otherwise inherit the dev proxy and send /api to
  // Django — the built site must answer those from public/api itself, as it
  // does on Vercel.
  preview: { proxy: {} },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 2048,
    rollupOptions: {
      output: {
        // rolldown (Vite 8) takes a resolver rather than a map
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('gsap') || id.includes('lenis')) return 'motion'
          if (id.includes('react-router')) return 'router'
          return undefined
        },
      },
    },
  },
})
