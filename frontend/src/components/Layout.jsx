import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { useReducedMotion } from '@/lib/hooks'

import Footer from './Footer'
import Nav from './Nav'

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

export default function Layout() {
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
    </>
  )
}
