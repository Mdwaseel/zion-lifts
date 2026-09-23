import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import { Rise, useScrollVar } from './lift/shared'
import { Lightbox, Strip, WallHero } from './gallery/pieces'

import './gallery.css'
import './projects-index.css'
import './gallery-index.css'

const pad = (n) => String(n).padStart(2, '0')

/* the order the page walks the archive in, and a line on each */
const ROWS = [
  ['residential', 'Residential', 'Villas and family houses, from the gate to the top landing.'],
  ['interiors', 'Interiors', 'Cabins, lobbies and the finishes people actually touch.'],
  ['commercial', 'Commercial', 'Restaurants and retail, where the lift is part of the front of house.'],
  ['institutional', 'Institutional', 'Hospitals and public buildings, specified for beds and for queues.'],
  ['installation', 'Installation', 'The work before the finishes go on: structure, rails, machine.'],
]

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
            Any of these can be specified for your building. Tell us which one and what it has to fit into.
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

/* --- page ----------------------------------------------------------------- */

export default function Gallery() {
  const { data: items } = useApi('gallery/')
  const [open, setOpen] = useState(null)

  useEffect(() => {
    document.title = 'Gallery — Zion Lifts'
  }, [])

  const all = useMemo(() => items ?? [], [items])

  const groups = useMemo(() => {
    const known = ROWS.map(([key, name, line]) => ({ key, name, line, items: all.filter((i) => i.category === key) }))
    const rest = all.filter((i) => !ROWS.some(([key]) => key === i.category))
    if (rest.length) known.push({ key: 'more', name: 'More', line: 'Everything else in the archive.', items: rest })
    return known.filter((g) => g.items.length)
  }, [all])

  // the lightbox walks the whole archive, in the order the page shows it
  const ordered = useMemo(() => groups.flatMap((g) => g.items), [groups])
  const move = useCallback(
    (delta) => setOpen((i) => (i === null ? null : (i + delta + ordered.length) % ordered.length)),
    [ordered.length],
  )

  return (
    <div className="ga">
      <WallHero
        items={all}
        index={groups.map((g) => ({ key: g.key, name: g.name, count: g.items.length }))}
        label="Zion in motion"
        title="Built. Installed. Experienced."
        lead="Every image here is of a lift Zion made. Cabins, doors, shafts, control panels, buildings — and the installations behind them."
        cueHref={groups[0] ? `#${groups[0].key}` : '#'}
        cueLabel="Scroll to the photographs"
      />
      <div className="ga-rows on-paper">
        {groups.map((g, i) => (
          <Strip
            key={g.key}
            id={g.key}
            index={i}
            total={groups.length}
            name={g.name}
            line={g.line}
            count={`${pad(g.items.length)} photographs · select one to open it`}
            items={g.items}
            prevLabel={`Earlier ${g.name} photographs`}
            nextLabel={`More ${g.name} photographs`}
            renderItem={(item) => (
              <button
                type="button"
                className="ga-cell"
                style={{ aspectRatio: `${item.width} / ${item.height}` }}
                onClick={() => setOpen(ordered.findIndex((x) => x.id === item.id))}
                aria-label={`${item.title} — open`}
              >
                <Img src={item.src} alt={item.title} sizes="(min-width: 900px) 36vw, 78vw" draggable={false} />
                <span className="ga-cell__cap">
                  <span className="ga-cell__title">{item.title}</span>
                  {item.meta && <span className="ga-cell__meta">{item.meta}</span>}
                </span>
              </button>
            )}
          />
        ))}
      </div>
      <Invitation />

      {open !== null && <Lightbox items={ordered} index={open} onClose={() => setOpen(null)} onMove={move} />}
    </div>
  )
}
