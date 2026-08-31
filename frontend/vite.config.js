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
      // /login redirects a signed-in staff user here; proxying keeps the whole
      // flow on one origin in dev, which is what makes SameSite=Lax cookies work.
      '/admin': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
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
