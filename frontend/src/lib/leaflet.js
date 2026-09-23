/**
 * Leaflet is fetched from a CDN the first time a map is about to be shown,
 * rather than bundled: only the installations map needs it, and only once the
 * visitor has scrolled that far. Resolves to the global `L`.
 */
const VERSION = '1.9.4'
const BASE = `https://unpkg.com/leaflet@${VERSION}/dist/`

let pending = null

export function loadLeaflet() {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'))
  if (window.L?.map) return Promise.resolve(window.L)
  if (pending) return pending
  pending = new Promise((resolve, reject) => {
    if (!document.querySelector('link[data-leaflet]')) {
      const css = document.createElement('link')
      css.rel = 'stylesheet'
      css.href = `${BASE}leaflet.css`
      css.crossOrigin = ''
      css.dataset.leaflet = ''
      document.head.appendChild(css)
    }
    const script = document.createElement('script')
    script.src = `${BASE}leaflet.js`
    script.async = true
    script.crossOrigin = ''
    script.onload = () => (window.L?.map ? resolve(window.L) : reject(new Error('leaflet did not load')))
    script.onerror = () => {
      pending = null
      reject(new Error('leaflet did not load'))
    }
    document.head.appendChild(script)
  })
  return pending
}
