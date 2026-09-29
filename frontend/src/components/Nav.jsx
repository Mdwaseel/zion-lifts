import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'

import { useApi } from '@/lib/hooks'
import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import './Nav.css'

/* `menu` marks an item that opens a panel; Resources is only a menu, the
   others are pages as well */
const PRIMARY = [
  { to: '/lifts', label: 'Lifts', menu: 'lifts', chevLabel: 'Types of lift' },
  { to: '/projects', label: 'Projects' },
  { to: '/about', label: 'About' },
  { label: 'Resources', menu: 'resources', under: ['/gallery', '/journal'] },
  { to: '/contact', label: 'Contact' },
]

/* --- the lifts menu -----------------------------------------------------------
   Under "Lifts", the eleven systems: each as the arched shaft it is on /lifts,
   its name and the line that says what it is for. Pointing at "Lifts" opens
   it; the chevron beside it opens it from a keyboard or a finger. It is a
   panel of its own under the bar, because the bar clips what it holds. */

function useMenus() {
  const [open, setOpen] = useState(null) // which menu is open, if any
  const timer = useRef(0)
  const show = useCallback((key) => {
    clearTimeout(timer.current)
    setOpen(key)
  }, [])
  const hide = useCallback((now = false) => {
    clearTimeout(timer.current)
    if (now) setOpen(null)
    else timer.current = setTimeout(() => setOpen(null), 160)
  }, [])
  useEffect(() => () => clearTimeout(timer.current), [])
  return { open, show, hide, toggle: (key) => (open === key ? hide(true) : show(key)) }
}

/* Escape closes an open panel, and so does a press anywhere outside it */
function useDismiss(open, ref, onClose) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose(true)
    const onDown = (e) => {
      if (!ref.current?.contains(e.target) && !e.target.closest?.('.hd__drop')) onClose(true)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onDown)
    }
  }, [open, ref, onClose])
}

function LiftsMenu({ id, open, onEnter, onLeave, onClose }) {
  const { data: lifts } = useApi('lifts/')
  const ref = useRef(null)

  useDismiss(open, ref, onClose)

  return (
    <div
      ref={ref}
      id={id}
      className={`hd-menu ${open ? 'is-open' : ''}`}
      onPointerEnter={onEnter}
      onPointerLeave={() => onLeave()}
      hidden={!open}
    >
      <ul className="hd-menu__grid">
        {(lifts ?? []).map((l) => (
          <li key={l.slug}>
            <Link to={`/lifts/${l.slug}`} className="hd-menu__item" onClick={() => onClose(true)}>
              <img className="hd-menu__arch" src={`/media/lifts/${l.slug}.jpg`} alt="" loading="lazy" decoding="async" />
              <span className="hd-menu__text">
                <strong>{l.name}</strong>
                <span>{l.tagline}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <div className="hd-menu__foot">
        <Link to="/lifts" onClick={() => onClose(true)}>
          See the whole range
        </Link>
        <Link to="/lifts#compare" onClick={() => onClose(true)}>
          Compare them side by side
        </Link>
      </div>
    </div>
  )
}

/* --- the resources menu -------------------------------------------------------
   Two places to read about lifts rather than buy one: the gallery of every
   photograph, and the journal, with its newest article a click away. */
const RESOURCES = [
  {
    to: '/gallery',
    name: 'Gallery',
    line: 'Every photograph of a Zion lift — cabins, doors, shafts and the buildings around them.',
    src: '/media/interiors/interior-01.jpg',
  },
  {
    to: '/journal',
    name: 'Journal',
    line: 'Notes from the survey, the factory floor and the service van, for anyone specifying a lift.',
    src: '/media/frames/lekha-hall.jpg',
  },
]

function ResourcesMenu({ id, open, onEnter, onLeave, onClose }) {
  const { data: posts } = useApi('journal/')
  const ref = useRef(null)
  useDismiss(open, ref, onClose)
  const latest = (posts ?? [])[0]

  return (
    <div
      ref={ref}
      id={id}
      className={`hd-menu hd-menu--res ${open ? 'is-open' : ''}`}
      onPointerEnter={onEnter}
      onPointerLeave={() => onLeave()}
      hidden={!open}
    >
      <ul className="hd-res">
        {RESOURCES.map((c) => (
          <li key={c.to}>
            <Link to={c.to} className="hd-res__card" onClick={() => onClose(true)}>
              <img className="hd-res__img" src={c.src} alt="" loading="lazy" decoding="async" />
              <span className="hd-res__name">{c.name}</span>
              <span className="hd-res__line">{c.line}</span>
            </Link>
          </li>
        ))}
      </ul>
      {latest && (
        <div className="hd-menu__foot">
          <Link to={`/journal/${latest.slug}`} className="hd-res__latest" onClick={() => onClose(true)}>
            <span>Latest in the journal</span>
            {latest.title}
          </Link>
        </div>
      )}
    </div>
  )
}

/* The header has two shapes. Over the top of a page it is a plain bar with no
   ground: brand, links, the ask. Once the page moves it draws in to a black tab
   hanging from the top edge of the screen — square where it meets the edge,
   rounded underneath — carrying the mark and the links spread evenly across
   it. There is one menu at every width; what opens is the list of lifts under
   "Lifts" and the gallery and journal under "Resources".

   While it is a bar, the right end carries the one lift-shaped thing in it: a
   position indicator, an arrow for the direction of travel and the page's
   height in floors. */
export default function Nav() {
  const [atTop, setAtTop] = useState(true)
  const barRef = useRef(null)
  const site = useSite()
  const menu = useMenus()
  const { pathname } = useLocation()

  // a new page closes the menu
  useEffect(() => {
    menu.hide(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

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
          {PRIMARY.map((l, i) => {
            /* the label twice: the second copy rolls up into place on hover */
            const roll = (
              <span className="hd__roll">
                <span>{l.label}</span>
                <span aria-hidden="true">{l.label}</span>
              </span>
            )
            if (!l.menu) {
              return (
                <NavLink
                  key={l.label}
                  to={l.to}
                  style={{ '--i': i }}
                  className={({ isActive }) => `hd__link ${isActive ? 'is-active' : ''}`}
                >
                  {roll}
                </NavLink>
              )
            }
            const panel = `hd-${l.menu}-menu`
            const isOpen = menu.open === l.menu
            const here = l.under?.some((u) => pathname === u || pathname.startsWith(`${u}/`))
            const chevron = (
              <svg viewBox="0 0 12 12" aria-hidden="true">
                <path d="M2.5 4.5 6 8l3.5-3.5" />
              </svg>
            )
            return (
              <span
                key={l.label}
                className="hd__drop"
                onPointerEnter={(e) => e.pointerType === 'mouse' && menu.show(l.menu)}
                onPointerLeave={(e) => e.pointerType === 'mouse' && menu.hide()}
              >
                {l.to ? (
                  <>
                    <NavLink
                      to={l.to}
                      style={{ '--i': i }}
                      className={({ isActive }) => `hd__link ${isActive ? 'is-active' : ''}`}
                    >
                      {roll}
                    </NavLink>
                    <button
                      type="button"
                      className={`hd__chev ${isOpen ? 'is-open' : ''}`}
                      aria-expanded={isOpen}
                      aria-controls={panel}
                      aria-label={l.chevLabel}
                      onClick={() => menu.toggle(l.menu)}
                    >
                      {chevron}
                    </button>
                  </>
                ) : (
                  // only a menu: the whole label opens it
                  <button
                    type="button"
                    style={{ '--i': i }}
                    className={`hd__link hd__link--menu ${here ? 'is-active' : ''}`}
                    aria-expanded={isOpen}
                    aria-controls={panel}
                    onClick={() => menu.toggle(l.menu)}
                  >
                    {roll}
                    <span className={`hd__chev hd__chev--in ${isOpen ? 'is-open' : ''}`}>{chevron}</span>
                  </button>
                )}
              </span>
            )
          })}
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
      <LiftsMenu
        id="hd-lifts-menu"
        open={menu.open === 'lifts'}
        onEnter={() => menu.show('lifts')}
        onLeave={menu.hide}
        onClose={menu.hide}
      />
      <ResourcesMenu
        id="hd-resources-menu"
        open={menu.open === 'resources'}
        onEnter={() => menu.show('resources')}
        onLeave={menu.hide}
        onClose={menu.hide}
      />
    </header>
  )
}
