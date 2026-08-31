import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Arrow } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import './legal.css'

const SIBLINGS = [
  { slug: 'privacy', label: 'Privacy Policy', to: '/privacy' },
  { slug: 'terms', label: 'Terms of Use', to: '/terms' },
  { slug: 'cookies', label: 'Cookie Policy', to: '/cookies' },
]

/** Deliberately plain: sticky contents left, clauses right, no motion. */
export default function Legal({ slug }) {
  const { data: doc, loading, error } = useApi(`legal/${slug}/`)
  const [active, setActive] = useState(null)

  useEffect(() => {
    if (doc) document.title = `${doc.title} — Zion Lifts`
  }, [doc])

  useEffect(() => {
    if (!doc?.clauses?.length) return
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-15% 0px -75% 0px' },
    )
    for (const c of doc.clauses) {
      const el = document.getElementById(`clause-${c.id}`)
      if (el) io.observe(el)
    }
    return () => io.disconnect()
  }, [doc])

  if (loading) {
    return (
      <div className="section" style={{ paddingTop: 'calc(var(--nav-h) + 4rem)' }}>
        <div className="shell">
          <div className="skeleton" style={{ height: '50vh' }} />
        </div>
      </div>
    )
  }

  if (error || !doc) {
    return (
      <section className="section" style={{ paddingTop: 'calc(var(--nav-h) + 4rem)' }}>
        <div className="shell state">
          <p className="state__title">That document is not available.</p>
          <Link to="/" className="btn btn--accent btn--sm">
            Back to the site <Arrow size={14} />
          </Link>
        </div>
      </section>
    )
  }

  const effective = doc.effective_date
    ? new Date(doc.effective_date).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    : ''

  return (
    <div className="legal">
      <header className="legal__head">
        <div className="shell">
          <nav className="pagehero__crumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span aria-hidden="true">/</span>
            <span>{doc.title}</span>
          </nav>
          <h1 className="h2 legal__title">{doc.title}</h1>
          {doc.intro && <p className="lead legal__intro">{doc.intro}</p>}
          {effective && <p className="mono legal__date">Effective {effective}</p>}
        </div>
      </header>

      <div className="shell legal__layout">
        <aside className="legal__nav">
          <p className="mono legal__nav-title">Contents</p>
          <ol className="legal__toc">
            {doc.clauses.map((c, i) => (
              <li key={c.id}>
                <a
                  href={`#clause-${c.id}`}
                  className={active === `clause-${c.id}` ? 'is-on' : ''}
                >
                  <span className="legal__toc-n">{String(i + 1).padStart(2, '0')}</span>
                  {c.heading}
                </a>
              </li>
            ))}
          </ol>

          <div className="legal__siblings">
            <p className="mono legal__nav-title">Other documents</p>
            <ul>
              {SIBLINGS.filter((s) => s.slug !== slug).map((s) => (
                <li key={s.slug}>
                  <Link to={s.to} className="link">
                    {s.label} <Arrow size={13} />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <article className="legal__body">
          {doc.clauses.map((c, i) => (
            <section className="legal__clause" id={`clause-${c.id}`} key={c.id}>
              <h2 className="legal__clause-title">
                <span className="legal__clause-n">{String(i + 1).padStart(2, '0')}</span>
                {c.heading}
              </h2>
              {c.body.split('\n\n').map((p, j) => (
                <p key={j}>{p}</p>
              ))}
            </section>
          ))}

          <footer className="legal__foot">
            <p className="small">
              Questions about this document? Write to{' '}
              <a href="mailto:info@zionlifts.com">info@zionlifts.com</a>.
            </p>
          </footer>
        </article>
      </div>
    </div>
  )
}
