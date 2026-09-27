import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow } from '@/components/icons'
import { gsap } from '@/lib/gsap'
import { useApi, useLightHero, useMediaQuery, useReducedMotion } from '@/lib/hooks'

import { Rise, RiseIn, useScrollVar, whenIntroDone } from './lift/shared'
import { Lightbox } from './gallery/pieces'

import './gallery.css'
import './projects-index.css'
import './gallery-index.css'

/* the order the page walks the archive in, and a line on each */
const ROWS = [
  ['residential', 'Residential', 'Villas and family houses, from the gate to the top landing.'],
  ['interiors', 'Interiors', 'Cabins, lobbies and the finishes people actually touch.'],
  [
    'commercial',
    'Commercial',
    'Restaurants and retail, where the lift is part of the front of house.',
  ],
  [
    'institutional',
    'Institutional',
    'Hospitals and public buildings, specified for beds and for queues.',
  ],
  [
    'installation',
    'Installation',
    'The work before the finishes go on: structure, rails, machine.',
  ],
]

/* --- the archive: every photograph, at its own shape ---------------------
   One masonry wall of the whole archive — nothing cropped to a tile, so a
   tall cabin and a wide façade sit side by side as they were shot. The sorts
   stay in reach at the top as the wall scrolls past; any photograph opens
   large, and the lightbox walks whatever the wall is showing. */

function useColumns() {
  const four = useMediaQuery('(min-width: 1200px)')
  const three = useMediaQuery('(min-width: 800px)')
  return four ? 4 : three ? 3 : 2
}

function Archive({ groups, all, filter, setFilter, onOpen }) {
  const cols = useColumns()
  const sentinel = useRef(null)
  const [stuck, setStuck] = useState(false)

  // stuck once the line above the band has gone up under it
  useEffect(() => {
    const mark = sentinel.current
    if (!mark) return undefined
    const band = mark.nextElementSibling
    let last = null
    const tick = () => {
      const top = parseFloat(getComputedStyle(band).top) || 0
      const now = mark.getBoundingClientRect().top < top - 1
      if (now !== last) {
        last = now
        setStuck(now)
      }
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [all.length])
  const group = groups.find((g) => g.key === filter)
  const shown = group ? group.items : all

  // each photograph goes to the shortest column so far, so the wall ends level
  const columns = useMemo(() => {
    const out = Array.from({ length: cols }, () => ({ h: 0, items: [] }))
    shown.forEach((it, i) => {
      const c = out.reduce((best, col, k) => (col.h < out[best].h ? k : best), 0)
      out[c].items.push({ ...it, n: i })
      out[c].h += (it.height || 3) / (it.width || 4)
    })
    return out
  }, [shown, cols])

  if (!all.length) return null
  const chips = [
    { key: 'all', name: 'All', count: all.length },
    ...groups.map((g) => ({ ...g, count: g.items.length })),
  ]

  return (
    <section
      className="section on-paper ga-archive"
      id="archive"
      aria-labelledby="ga-archive-title"
    >
      <div className="shell">
        <header className="ga-archive__head">
          <RiseIn
            as="h2"
            id="ga-archive-title"
            className="pr-h2"
            text="Every photograph, sorted."
            accent={false}
          />
          <p className="pr-lead">
            From the building outside to the rails inside the shaft. Select any photograph to see it
            large.
          </p>
        </header>
      </div>

      {/* a line the band watches: once it has gone under the header, the band is stuck */}
      <span ref={sentinel} className="ga-sort__mark" aria-hidden="true" />
      <div className={`ga-sort ${stuck ? 'is-stuck' : ''}`}>
        <div className="shell ga-sort__in">
          <div className="ga-sort__track" role="group" aria-label="Show photographs from">
            {chips.map((c) => (
              <button
                type="button"
                key={c.key}
                className={filter === c.key ? 'is-on' : ''}
                aria-pressed={filter === c.key}
                onClick={() => setFilter(c.key)}
              >
                {c.name} <span>{c.count}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="shell">
        {group?.line && (
          <p className="ga-archive__line" key={group.key}>
            {group.line}
          </p>
        )}

        <div className="ga-masonry" key={`${filter}-${cols}`} style={{ '--cols': cols }}>
          {columns.map((col, c) => (
            <div className="ga-masonry__col" key={c}>
              {col.items.map((item) => (
                <figure className="ga-shot" key={item.id} style={{ '--i': Math.min(item.n, 12) }}>
                  <button
                    type="button"
                    className="ga-shot__btn"
                    style={{ aspectRatio: `${item.width} / ${item.height}` }}
                    onClick={() => onOpen(shown, item.n)}
                    aria-label={`${item.title} — open`}
                  >
                    <Img
                      src={item.src}
                      alt={item.title}
                      sizes={`(min-width: 800px) ${Math.round(100 / cols)}vw, 50vw`}
                    />
                  </button>
                  <figcaption>
                    <strong>{item.title}</strong>
                    {item.meta && <span>{item.meta}</span>}
                  </figcaption>
                </figure>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* --- the ask: a frame that opens ------------------------------------------ */

function Invitation() {
  const wrap = useRef(null)
  useScrollVar(wrap, { from: 1, to: 0.15 })

  return (
    <div ref={wrap} className="pr-invite-wrap">
      <section className="pr-invite">
        <div className="pr-invite__scene">
          <Img src="/media/frames/lekha-hall.jpg" alt="" sizes="100vw" />
        </div>
        <div className="pr-invite__copy">
          <p className="ld-label">Next step</p>
          <h2 className="pr-invite__title ld-rise">
            <Rise text="Seen something you like?" />
          </h2>
          <p className="pr-invite__lead">
            Any of these can be specified for your building. Tell us which one and what it has to
            fit into.
          </p>
          <div className="pr-invite__actions">
            <Link to="/contact" className="pr-go">
              <span>Get a quote</span>
              <span className="pr-go__ring">
                <Arrow size={16} />
              </span>
            </Link>
            <Link to="/projects" className="pr-invite__alt">
              See the projects
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

/* --- the opening: the archive, never still -------------------------------
   The headline takes one cell of a grid of photographs; every couple of
   seconds one of the others turns over to another picture from the archive,
   so the whole collection passes through the frame without anyone scrolling.
   Any tile opens its photograph. */

/* where the tiles sit in the six-column grid: [column, row, width, height] */
const TILES = [
  [4, 1, 2, 2],
  [6, 1, 1, 1],
  [6, 2, 1, 1],
  [1, 3, 1, 1],
  [2, 3, 2, 1],
  [4, 3, 1, 1],
  [5, 3, 2, 1],
]
const TURN = 2300

function Opening({ items, groups, onOpen, onPick }) {
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(false)
  const [turns, setTurns] = useState(() => TILES.map(() => 0))
  const [paused, setPaused] = useState(false)
  useLightHero()

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  // the archive dealt round the tiles, so no tile repeats another's pictures
  const pools = useMemo(() => {
    const out = TILES.map(() => [])
    items.forEach((it, i) => out[i % TILES.length].push(it))
    return out
  }, [items])

  useEffect(() => {
    if (reduced || paused || !items.length) return undefined
    let k = 0
    const order = [0, 4, 2, 6, 1, 5, 3] // never the same corner twice in a row
    const id = setInterval(() => {
      const t = order[k++ % order.length]
      setTurns((prev) => prev.map((v, i) => (i === t ? v + 1 : v)))
    }, TURN)
    return () => clearInterval(id)
  }, [reduced, paused, items.length])

  return (
    <header className={`ga-hero ${shown ? 'is-in' : ''}`}>
      <div
        className="ga-mosaic"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        <div className="ga-hero__copy">
          <h1 className="ga-hero__title">
            <Rise text="Built. Installed. Experienced." accent={false} />
          </h1>
          <p className="ga-hero__lead">
            Every image here is of a lift Zion made. Cabins, doors, shafts, control panels,
            buildings — and the installations behind them.
          </p>
          {groups.length > 0 && (
            <nav className="ga-hero__index" aria-label="Sections">
              {groups.map((g) => (
                <a
                  key={g.key}
                  href="#archive"
                  onClick={(e) => {
                    e.preventDefault()
                    onPick(g.key)
                  }}
                >
                  {g.name} <span>{g.items.length}</span>
                </a>
              ))}
            </nav>
          )}
        </div>

        {TILES.map(([c, r, w, h], t) => {
          const pool = pools[t]
          if (!pool?.length) return null
          const cur = pool[turns[t] % pool.length]
          const prev = pool[(turns[t] - 1 + pool.length) % pool.length]
          return (
            <button
              type="button"
              key={t}
              className="ga-tile"
              style={{ gridColumn: `${c} / span ${w}`, gridRow: `${r} / span ${h}`, '--i': t }}
              onClick={() => onOpen(cur)}
              aria-label={`${cur.title} — open`}
            >
              {turns[t] > 0 && (
                <span className="ga-tile__layer" key={`p-${prev.id}`}>
                  <Img src={prev.src} alt="" sizes="(min-width: 900px) 34vw, 46vw" />
                </span>
              )}
              <span className="ga-tile__layer is-new" key={`c-${cur.id}`}>
                <Img
                  src={cur.src}
                  alt=""
                  priority={turns[t] === 0}
                  sizes="(min-width: 900px) 34vw, 46vw"
                />
              </span>
              <span className="ga-tile__cap">{cur.title}</span>
            </button>
          )
        })}
      </div>
    </header>
  )
}

/* --- page ----------------------------------------------------------------- */

export default function Gallery() {
  const { data: items } = useApi('gallery/')
  const [open, setOpen] = useState(null)

  useEffect(() => {
    document.title = 'Gallery — Zion Lifts'
  }, [])

  const all = useMemo(() => items ?? [], [items])

  const groups = useMemo(() => {
    const known = ROWS.map(([key, name, line]) => ({
      key,
      name,
      line,
      items: all.filter((i) => i.category === key),
    }))
    const rest = all.filter((i) => !ROWS.some(([key]) => key === i.category))
    if (rest.length)
      known.push({
        key: 'more',
        name: 'More',
        line: 'Everything else in the archive.',
        items: rest,
      })
    return known.filter((g) => g.items.length)
  }, [all])

  const [filter, setFilter] = useState('all')
  const [list, setList] = useState([]) // what the open lightbox walks
  const move = useCallback(
    (delta) => setOpen((i) => (i === null ? null : (i + delta + list.length) % list.length)),
    [list.length],
  )
  const openIn = (items, i) => {
    setList(items)
    setOpen(i)
  }

  // a sort in the opening sorts the archive and takes you down to it
  const pick = (key) => {
    setFilter(key)
    const el = document.getElementById('archive')
    if (!el) return
    if (window.__lenis) window.__lenis.scrollTo(el, { offset: -40, duration: 1.1 })
    else el.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="ga">
      <Opening
        items={all}
        groups={groups}
        onPick={pick}
        onOpen={(item) =>
          openIn(
            all,
            all.findIndex((x) => x.id === item.id),
          )
        }
      />
      <Archive groups={groups} all={all} filter={filter} setFilter={setFilter} onOpen={openIn} />
      <Invitation />

      {open !== null && (
        <Lightbox items={list} index={open} onClose={() => setOpen(null)} onMove={move} />
      )}
    </div>
  )
}
