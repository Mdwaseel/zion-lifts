import { useEffect } from 'react'
import { Link } from 'react-router-dom'

import { Arrow } from '@/components/icons'

export default function NotFound() {
  useEffect(() => {
    document.title = 'Page not found — Zion Lifts'
  }, [])

  return (
    <section className="section" style={{ paddingTop: 'calc(var(--nav-h) + 6rem)', minHeight: '70svh' }}>
      <div className="shell state">
        <p className="eyebrow">Error 404</p>
        <h1 className="display" style={{ maxWidth: '14ch' }}>
          This floor doesn&rsquo;t exist.
        </h1>
        <p className="body">
          The page you asked for is not here. The lift is still working — try one of these instead.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '1rem' }}>
          <Link to="/" className="btn btn--accent btn--sm">
            Back to the ground floor <Arrow size={14} />
          </Link>
          <Link to="/lifts" className="btn btn--ghost btn--sm">
            The range <Arrow size={14} />
          </Link>
          <Link to="/contact" className="btn btn--ghost btn--sm">
            Contact <Arrow size={14} />
          </Link>
        </div>
      </div>
    </section>
  )
}
