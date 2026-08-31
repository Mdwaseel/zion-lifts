import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// The RAG service sits behind an X-API-Key. This config runs in Node, never in
// the browser, so the key is attached here on the way through and the bundle
// stays free of it — which is the whole reason the assistant talks to /ai
// rather than to the service directly.
const AI_TARGET = process.env.AI_SERVICE_URL ?? 'http://127.0.0.1:8080'
const AI_KEY = process.env.AI_SERVICE_API_KEY ?? ''

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
      // The assistant's RAG service, on its own prefix.
      '/ai': {
        target: AI_TARGET,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/ai/, ''),
        // Answers arrive as server-sent events: without this the proxy buffers
        // the whole response and the answer lands in one lump at the end.
        selfHandleResponse: false,
        configure(proxy) {
          proxy.on('proxyReq', (proxyReq) => {
            if (AI_KEY) proxyReq.setHeader('X-API-Key', AI_KEY)
          })
        },
      },
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
