import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { useAuth } from '@/lib/auth'

import Sidebar from './Sidebar'

/**
 * The frame every screen sits in: sidebar, top bar, content.
 *
 * On a phone the sidebar becomes a drawer. It closes on navigation, because a
 * menu that stays open over the page you just asked for is a menu you have to
 * dismiss twice.
 */

export default function Shell({ navigation, children }) {
  const { user, signOut } = useAuth()
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)

  useEffect(() => setMenuOpen(false), [pathname])

  useEffect(() => {
    if (!menuOpen) return undefined
    const close = (event) => event.key === 'Escape' && setMenuOpen(false)
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [menuOpen])

  async function onSignOut() {
    setSigningOut(true)
    await signOut()
    // A document navigation, not a route change: signing out should also drop
    // the Django admin session and leave nothing of the panel mounted.
    window.location.assign('/login')
  }

  return (
    <div className={`cf${menuOpen ? ' cf--menu-open' : ''}`}>
      <a className="cf-skip" href="#cf-main">
        Skip to content
      </a>

      <header className="cf-topbar">
        <button
          type="button"
          className="cf-topbar__menu"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          aria-controls="cf-sidebar"
        >
          <span aria-hidden="true">{menuOpen ? '×' : '☰'}</span>
          <span className="cf-sr">{menuOpen ? 'Close menu' : 'Open menu'}</span>
        </button>

        <p className="cf-topbar__brand">
          Zion Lifts <span>Control Room</span>
        </p>

        <div className="cf-topbar__user">
          <span className="cf-topbar__name">{user?.name}</span>
          <button
            type="button"
            className="cf-btn cf-btn--ghost cf-btn--sm"
            onClick={onSignOut}
            disabled={signingOut}
          >
            {signingOut ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      </header>

      <div className="cf-body">
        <Sidebar
          groups={navigation.groups}
          open={menuOpen}
          onNavigate={() => setMenuOpen(false)}
        />

        {/* Closes the drawer when the page behind it is tapped. Inert on
            desktop, where the sidebar is always visible. */}
        <button
          type="button"
          className="cf-scrim"
          onClick={() => setMenuOpen(false)}
          tabIndex={-1}
          aria-hidden="true"
        />

        <main className="cf-main" id="cf-main">
          {children}
        </main>
      </div>
    </div>
  )
}
