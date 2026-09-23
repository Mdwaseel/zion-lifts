import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow, ArrowDown, Close } from '@/components/icons'
import { gsap } from '@/lib/gsap'
import { useEscape, useReducedMotion, useScrollLock } from '@/lib/hooks'
import { srcSet } from '@/lib/media'

import { Rise, RiseIn, clamp01, whenIntroDone } from '../lift/shared'

const pad = (n) => String(n).padStart(2, '0')

/* The pieces the gallery is built from, shared with the projects pages: the
   opening wall of photographs, a strip the visitor moves by hand, and the
   lightbox a photograph opens in. The styles live in gallery-index.css
   (`ga-`) and gallery.css (`lightbox`). */

/* --- the opening: a tilted wall of every photograph ------------------------
   Five columns, each drifting the opposite way to its neighbour and looping
   without a seam; the whole wall leans away as the page starts to move. */

const WALL_COLS = 5

export function WallHero({ items, index = [], label, title, lead, cueHref, cueLabel = 'Scroll down' }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(false)

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  useEffect(() => {
    if (reduced) return undefined
    const el = ref.current
    let last = -1
    const tick = () => {
      const p = clamp01(window.scrollY / window.innerHeight)
      if (Math.abs(p - last) < 0.001) return
      last = p
      el.style.setProperty('--x', p.toFixed(4))
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced])

  const columns = useMemo(() => {
    const cols = Array.from({ length: WALL_COLS }, () => [])
    items.forEach((it, i) => cols[i % WALL_COLS].push(it))
    return cols
  }, [items])

  return (
    <header ref={ref} className={`ga-hero ${shown ? 'is-in' : ''}`}>
      <div className="ga-wall" aria-hidden="true">
        <div className="ga-wall__plane">
          {columns.map((col, c) => (
            <div className="ga-wall__col" key={c} style={{ '--c': c, '--dur': `${46 + c * 9}s` }}>
              {/* the list twice over, so the loop has no seam */}
              {[...col, ...col].map((it, k) => (
                <div className="ga-wall__cell" key={`${it.id}-${k}`} style={{ aspectRatio: `${it.width} / ${it.height}` }}>
                  <Img src={it.src} alt="" priority={k < 2} sizes="(min-width: 900px) 22vw, 40vw" />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="ga-hero__grade" aria-hidden="true" />

      <div className="ga-hero__copy">
        <p className="ld-label ga-hero__label">{label}</p>
        <h1 className="ga-hero__title">
          <Rise text={title} />
        </h1>
        <p className="ga-hero__lead">{lead}</p>
      </div>

      <div className="ga-hero__foot">
        {index.length > 0 && (
          <nav className="ga-hero__index" aria-label="Sections">
            {index.map((g, i) => (
              <a key={g.key} href={`#${g.key}`} style={{ '--i': i }}>
                <strong>{pad(g.count)}</strong>
                <span>{g.name}</span>
              </a>
            ))}
          </nav>
        )}
        <a href={cueHref ?? '#'} className="ga-hero__cue" aria-label={cueLabel}>
          <ArrowDown size={16} />
        </a>
      </div>
    </header>
  )
}

/* --- a strip -----------------------------------------------------------------
   One group to a strip, as long as it needs to be — and it stays where it is
   put. The visitor moves it: drag it with the mouse, swipe it, use a sideways
   wheel or the arrows. A line under the strip shows how far along it is, and a
   click that was really a drag does not open anything. `renderItem` draws each
   cell; `count` is the line under the heading. */

export function Strip({ id, index, total, name, line, count, items, renderItem, prevLabel, nextLabel }) {
  const ref = useRef(null)
  const win = useRef(null)
  const drag = useRef(null)
  const dragged = useRef(false)
  const [seen, setSeen] = useState(false)
  const [pos, setPos] = useState({ p: 0, start: true, end: false, fits: false })

  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true)
          io.disconnect()
        }
      },
      { threshold: 0.2 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    const w = win.current
    if (!w) return undefined
    let raf = 0
    const measure = () => {
      raf = 0
      const max = w.scrollWidth - w.clientWidth
      setPos({
        p: max > 0 ? w.scrollLeft / max : 0,
        start: w.scrollLeft <= 2,
        end: w.scrollLeft >= max - 2,
        fits: max <= 4,
      })
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(measure)
    }
    // the page's smooth scroller takes every wheel event for itself, so a
    // sideways wheel over the strip has to be spent here
    const onWheel = (e) => {
      const sideways = Math.abs(e.deltaX) > Math.abs(e.deltaY)
      if (!sideways && !e.shiftKey) return
      const delta = sideways ? e.deltaX : e.deltaY
      const max = w.scrollWidth - w.clientWidth
      if ((delta < 0 && w.scrollLeft <= 0) || (delta > 0 && w.scrollLeft >= max - 1)) return
      e.preventDefault()
      e.stopPropagation()
      w.scrollLeft += delta
    }
    measure()
    w.addEventListener('scroll', onScroll, { passive: true })
    w.addEventListener('wheel', onWheel, { passive: false })
    const ro = new ResizeObserver(measure)
    ro.observe(w)
    return () => {
      w.removeEventListener('scroll', onScroll)
      w.removeEventListener('wheel', onWheel)
      ro.disconnect()
      if (raf) cancelAnimationFrame(raf)
    }
  }, [items.length])

  const step = (dir) => {
    const w = win.current
    if (w) w.scrollBy({ left: dir * w.clientWidth * 0.75, behavior: 'smooth' })
  }

  // mouse drag; touch already scrolls the strip natively
  const onDown = (e) => {
    if (e.pointerType !== 'mouse' || e.button !== 0) return
    drag.current = { x: e.clientX, left: win.current.scrollLeft, moved: false }
  }
  const onMove = (e) => {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.x
    if (Math.abs(dx) > 5 && !d.moved) {
      d.moved = true
      win.current.classList.add('is-dragging')
    }
    if (d.moved) win.current.scrollLeft = d.left - dx
  }
  const onUp = () => {
    const d = drag.current
    drag.current = null
    if (!d) return
    win.current.classList.remove('is-dragging')
    if (d.moved) {
      dragged.current = true
      setTimeout(() => {
        dragged.current = false
      }, 0)
    }
  }

  return (
    <section ref={ref} id={id} className={`ga-row ${seen ? 'is-in' : ''}`} aria-labelledby={`ga-${id}`}>
      <div className="ga-row__head">
        {total > 1 && (
          <p className="ga-row__n">
            {pad(index + 1)} <span>/ {pad(total)}</span>
          </p>
        )}
        <RiseIn as="h2" id={`ga-${id}`} className="ga-row__name" text={`${name}.`} />
        <p className="ga-row__line">{line}</p>
        <p className="ga-row__count">{count}</p>
      </div>

      <div
        ref={win}
        className="ga-row__window"
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerLeave={onUp}
        onPointerCancel={onUp}
        onDragStart={(e) => e.preventDefault()}
        onClickCapture={(e) => {
          if (dragged.current) {
            e.preventDefault()
            e.stopPropagation()
          }
        }}
      >
        <ul className="ga-strip">
          {items.map((item, i) => (
            <li key={item.id ?? item.slug ?? i} style={{ '--i': i }}>
              {renderItem(item, i)}
            </li>
          ))}
        </ul>
      </div>

      {!pos.fits && (
        <div className="ga-row__ctrl">
          <span className="ga-row__bar" aria-hidden="true">
            <span style={{ transform: `translateX(${(pos.p * 300).toFixed(1)}%)` }} />
          </span>
          <p className="ga-row__hint" aria-hidden="true">
            Drag or swipe
          </p>
          <button
            type="button"
            className="ga-row__step ga-row__step--prev"
            onClick={() => step(-1)}
            disabled={pos.start}
            aria-label={prevLabel ?? `Earlier ${name}`}
          >
            <Arrow size={15} />
          </button>
          <button
            type="button"
            className="ga-row__step"
            onClick={() => step(1)}
            disabled={pos.end}
            aria-label={nextLabel ?? `More ${name}`}
          >
            <Arrow size={15} />
          </button>
        </div>
      )}
    </section>
  )
}

/* --- the lightbox ----------------------------------------------------------- */

export function Lightbox({ items, index, onClose, onMove }) {
  useScrollLock(true)
  useEscape(onClose)

  const onKey = useCallback(
    (e) => {
      if (e.key === 'ArrowRight') onMove(1)
      if (e.key === 'ArrowLeft') onMove(-1)
    },
    [onMove],
  )

  useEffect(() => {
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onKey])

  const item = items[index]
  if (!item) return null

  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label={item.title || 'Image'}>
      <button type="button" className="lightbox__scrim" onClick={onClose} aria-label="Close" />
      <button type="button" className="lightbox__close" onClick={onClose}>
        <Close size={20} />
        <span className="sr-only">Close</span>
      </button>

      <button type="button" className="lightbox__nav lightbox__nav--prev" onClick={() => onMove(-1)} aria-label="Previous image">
        <Arrow size={20} style={{ transform: 'rotate(180deg)' }} />
      </button>

      <figure className="lightbox__fig" key={item.id}>
        <img src={item.src} srcSet={srcSet(item.src)} sizes="90vw" alt={item.title || ''} />
        <figcaption className="lightbox__cap">
          <span className="lightbox__title">{item.title}</span>
          {item.meta && <span className="lightbox__meta">{item.meta}</span>}
          <span className="lightbox__count mono">
            {index + 1} / {items.length}
          </span>
          {item.project_slug && (
            <Link to={`/projects/${item.project_slug}`} className="link">
              View the project <Arrow size={13} />
            </Link>
          )}
        </figcaption>
      </figure>

      <button type="button" className="lightbox__nav lightbox__nav--next" onClick={() => onMove(1)} aria-label="Next image">
        <Arrow size={20} />
      </button>
    </div>
  )
}

/* --- the opening: the wall -------------------------------------------------
   The whole archive hung as one tilted wall behind the headline, its columns
   drifting past each other, leaning away as the page moves on. */
