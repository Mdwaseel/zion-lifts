import { Suspense, lazy, useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { useReducedMotion } from '@/lib/hooks'

import Footer from './Footer'
import Nav from './Nav'

// The assistant is a utility layered over the site, not part of it: its chunk
// (and the connection to the RAG service) waits until the browser is idle, so
// it costs the first paint nothing.
const Assistant = lazy(() => import('./Assistant'))

/** Restores scroll on navigation, and honours in-page #hash targets. */
function ScrollManager() {
  const { pathname, hash } = useLocation()
  const reduced = useReducedMotion()

  useEffect(() => {
    if (hash) {
      // let the target section mount before measuring it
      const id = hash.slice(1)
      const attempt = (tries = 0) => {
        const el = document.getElementById(id)
        if (el) {
          el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
        } else if (tries < 12) {
          setTimeout(() => attempt(tries + 1), 60)
        }
      }
      attempt()
      return
    }
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [pathname, hash, reduced])

  return null
}

/** True once the browser has nothing better to do. */
function useIdle() {
  const [idle, setIdle] = useState(false)

  useEffect(() => {
    if (typeof requestIdleCallback !== 'function') {
      const t = setTimeout(() => setIdle(true), 2500)
      return () => clearTimeout(t)
    }
    const handle = requestIdleCallback(() => setIdle(true), { timeout: 4000 })
    return () => cancelIdleCallback(handle)
  }, [])

  return idle
}

export default function Layout() {
  const idle = useIdle()

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <ScrollManager />
      <Nav />
      <main id="main">
        <Outlet />
      </main>
      <Footer />
      {/* Its own boundary: a slow chunk here must not replace the page with the
          route loading bar. */}
      {idle && (
        <Suspense fallback={null}>
          <Assistant />
        </Suspense>
      )}
    </>
  )
}
