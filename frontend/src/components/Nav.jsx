import { useEffect, useRef, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'

import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import './Nav.css'

const PRIMARY = [
  { to: '/lifts', label: 'Lifts' },
  { to: '/projects', label: 'Projects' },
  { to: '/about', label: 'About' },
  { to: '/gallery', label: 'Gallery' },
  { to: '/contact', label: 'Contact' },
]

/* The header has two shapes. Over the top of a page it is a plain bar with no
   ground: brand, links, the ask. Once the page moves it draws in to a black tab
   hanging from the top edge of the screen — square where it meets the edge,
   rounded underneath — carrying the mark and the links spread evenly across
   it. There is one menu at every width; nothing opens.

   While it is a bar, the right end carries the one lift-shaped thing in it: a
   position indicator, an arrow for the direction of travel and the page's
   height in floors. */
export default function Nav() {
  const [atTop, setAtTop] = useState(true)
  const barRef = useRef(null)
  const site = useSite()

  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      const y = window.scrollY
      setAtTop(y < 24)
      const doc = document.documentElement
      const max = doc.scrollHeight - doc.clientHeight
      const p = max > 0 ? Math.min(1, Math.max(0, y / max)) : 0
      if (barRef.current) barRef.current.style.transform = `scaleX(${p})`
    }
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [])

  return (
    <header className={`hd ${atTop ? 'is-top' : 'is-tab'}`}>
      <div className="hd__inner">
        <Link to="/" className="hd__brand" aria-label="Zion Lifts — home">
          <img src="/media/brand/mark.png" alt="" className="hd__mark" width="30" height="32" />
          <span className="hd__wordmark">
            Zion<span>Lifts</span>
          </span>
        </Link>

        <nav className="hd__links" aria-label="Primary">
          {PRIMARY.map((l, i) => (
            <NavLink
              key={l.to}
              to={l.to}
              style={{ '--i': i }}
              className={({ isActive }) => `hd__link ${isActive ? 'is-active' : ''}`}
            >
              {/* the label twice: the second copy rolls up into place on hover */}
              <span className="hd__roll">
                <span>{l.label}</span>
                <span aria-hidden="true">{l.label}</span>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="hd__actions">
          {site?.phone && (
            <a className="hd__phone" href={telHref(site.phone)}>
              {site.phone}
            </a>
          )}
          <Link to="/contact" className="hd__cta">
            <span className="hd__roll">
              <span>Get a quote</span>
              <span aria-hidden="true">Get a quote</span>
            </span>
          </Link>
        </div>
        <span className="hd__progress" ref={barRef} aria-hidden="true" />
      </div>
    </header>
  )
}
