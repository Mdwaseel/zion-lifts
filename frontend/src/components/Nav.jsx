import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'

import { useEscape, useScrollLock } from '@/lib/hooks'
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

const MENU_GROUPS = [
  {
    title: 'The range',
    links: [
      { to: '/lifts', label: 'All lift systems' },
      { to: '/lifts/home-elevator', label: 'Home elevators' },
      { to: '/lifts/capsule-elevator', label: 'Capsule elevators' },
      { to: '/lifts/mrl-traction', label: 'MRL traction' },
      { to: '/lifts/hospital-elevator', label: 'Hospital elevators' },
      { to: '/lifts/goods-elevator', label: 'Goods & freight' },
    ],
  },
  {
    title: 'Proof',
    links: [
      { to: '/projects', label: 'All projects' },
      { to: '/gallery', label: 'Gallery' },
      { to: '/about', label: 'About Zion' },
    ],
  },
  {
    title: 'Knowledge',
    links: [
      { to: '/journal', label: 'Journal' },
      { to: '/faq', label: 'Questions, answered' },
    ],
  },
  {
    title: 'Talk to us',
    links: [
      { to: '/contact', label: 'Start a project enquiry' },
      { to: '/contact#service', label: 'Service & breakdown' },
      { to: '/contact#visit', label: 'Arrange a visit' },
    ],
  },
]

export default function Nav() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [hidden, setHidden] = useState(false)
  const location = useLocation()
  const site = useSite()

  useScrollLock(open)
  useEscape(() => setOpen(false), open)

  useEffect(() => setOpen(false), [location.pathname, location.hash])

  useEffect(() => {
    let last = window.scrollY
    const onScroll = () => {
      const y = window.scrollY
      setScrolled(y > 40)
      // hide going down past the fold, reveal on any upward movement
      setHidden(y > 320 && y > last + 4)
      last = y
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <header className={`nav ${scrolled ? 'is-scrolled' : ''} ${hidden && !open ? 'is-hidden' : ''}`}>
        <div className="nav__inner">
          <Link to="/" className="nav__brand" aria-label="Zion Lifts — home">
            <img src="/media/brand/mark.png" alt="" className="nav__mark" width="30" height="32" />
            <span className="nav__wordmark">
              Zion<span>Lifts</span>
            </span>
          </Link>

          <nav className="nav__links" aria-label="Primary">
            {PRIMARY.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) => `nav__link ${isActive ? 'is-active' : ''}`}
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <div className="nav__actions">
            {site?.phone && (
              <a className="nav__phone" href={telHref(site.phone)}>
                {site.phone}
              </a>
            )}
            <Link to="/contact" className="btn btn--accent btn--sm nav__cta">
              Get a quote
            </Link>
            <button
              type="button"
              className={`nav__toggle ${open ? 'is-open' : ''}`}
              onClick={() => setOpen((o) => !o)}
              aria-expanded={open}
              aria-controls="site-menu"
            >
              <span className="sr-only">{open ? 'Close menu' : 'Open menu'}</span>
              <span className="nav__bar" />
              <span className="nav__bar" />
            </button>
          </div>
        </div>
      </header>

      {/* The menu parts like a pair of lift doors rather than dropping down. */}
      <div id="site-menu" className={`menu ${open ? 'is-open' : ''}`} aria-hidden={!open}>
        <div className="menu__door menu__door--l" />
        <div className="menu__door menu__door--r" />
        <div className="menu__body">
          <div className="menu__grid">
            {MENU_GROUPS.map((group, gi) => (
              <div className="menu__group" key={group.title} style={{ '--gi': gi }}>
                <p className="menu__title">{group.title}</p>
                <ul className="menu__list">
                  {group.links.map((l) => (
                    <li key={l.to + l.label}>
                      <Link to={l.to} className="menu__link">
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="menu__foot">
            <div>
              <p className="mono">Speak to an engineer</p>
              {site?.phone && (
                <a className="menu__phone" href={telHref(site.phone)}>
                  {site.phone}
                </a>
              )}
            </div>
            <p className="small">
              {site?.city ?? 'Hyderabad'}, {site?.country ?? 'India'} — since{' '}
              {site?.founded_year ?? 2012}
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
