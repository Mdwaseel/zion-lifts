import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Img, VideoLoop } from '@/components/Media'
import Reveal from '@/components/Reveal'
import SafetyDrawing from '@/components/SafetyDrawing'
import { DoorMark } from '@/components/cabin-marks'
import {
  Arrow,
  ArrowDown,
  Bolt,
  CogMark,
  CrosshairMark,
  GaugeMark,
  LayersMark,
  Phone,
  Shield,
  UsersMark,
  WaveMark,
} from '@/components/icons'
import { FlameMark, PLACES, WeightMark } from '@/components/place-marks'
import { gsap } from '@/lib/gsap'
import { useApi, useMediaQuery, useReducedMotion } from '@/lib/hooks'
import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import { FEATURES, ROOMS } from './home/LiftsExperience'
import CabinStudio from './lift/CabinStudio'
import { Rise, RiseIn, Scrub, clamp01, useScrollVar, whenIntroDone } from './lift/shared'
import { ProjectsReel } from './home/Proof'
import './lift-detail.css'

/* ==========================================================================
   /lifts/[slug] — one lift, told the way the home page tells all nine
   The room fills the first screen. Below it the page goes quiet: a statement,
   the figures beside the lift's own film, the cabin, the rooms it stands in,
   what keeps it safe, and the way on to the next lift. One idea per section,
   and nothing the home page has already said.
   ========================================================================== */

/* --- the room ------------------------------------------------------------- */

/** a landscape room on a wide screen; the lift's own portrait frame on a phone */
function useScene(lift) {
  const phone = useMediaQuery('(max-width: 767px)')
  const room = ROOMS[lift.slug]
  if (phone && room) return { src: `/media/lifts/${lift.slug}.jpg`, pos: '50% 50%' }
  return { src: room?.src ?? lift.hero_image_url, pos: room?.pos }
}

function Hero({ lift }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(false)
  const scene = useScene(lift)

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  // leaving, the room draws back into a frame — the first of the page's frames
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

  return (
    <header ref={ref} className={`ld-hero ${shown ? 'is-in' : ''}`}>
      <div className="ld-hero__scene">
        <Img key={scene.src} src={scene.src} alt="" priority sizes="100vw" objectPosition={scene.pos} />
      </div>
      <div className="ld-hero__grade" aria-hidden="true" />

      <div className="ld-hero__copy">
        <nav className="ld-crumb" aria-label="Breadcrumb">
          <Link to="/lifts">Lifts</Link>
          <span aria-hidden="true">/</span>
          <span>{lift.eyebrow}</span>
        </nav>
        <h1 className="ld-hero__title">
          <Rise text={lift.name} />
        </h1>
        <p className="ld-hero__lead">{lift.tagline}</p>
      </div>

      <div className="ld-hero__foot">
        <dl className="ld-feats">
          {FEATURES.filter(([, key]) => lift[key]).map(([label, key, Icon], i) => (
            <div key={key} style={{ '--i': i }}>
              <Icon size={20} aria-hidden="true" />
              <dt>{label}</dt>
              <dd>{lift[key]}</dd>
            </div>
          ))}
        </dl>
        <a href="#overview" className="ld-hero__cue" aria-label="Scroll to the overview">
          <ArrowDown size={16} />
        </a>
      </div>
    </header>
  )
}

/* --- the statement -------------------------------------------------------- */

function Statement({ lift }) {
  const sec = useRef(null)
  const paras = (lift.overview || '').split('\n\n').filter(Boolean)
  const frame = (lift.images ?? []).find((g) => g.kind === 'gallery') ?? { src: lift.hero_image_url, alt: lift.name }
  // one variable for the whole section: the name drifting behind, the frame tipping up
  useScrollVar(sec, { from: 1, to: -0.9, name: '--s', ease: 0.1 })

  return (
    <section ref={sec} className="section on-stone ld-say" id="overview">
      <p className="ld-say__ghost" aria-hidden="true">
        {lift.short_name} · {lift.short_name} · {lift.short_name}
      </p>
      <div className="shell">
        <Scrub text={lift.summary} className="ld-say__line" />

        <div className="ld-say__grid">
          <figure className="ld-say__frame">
            <div className="ld-say__tilt">
              <Img src={frame.src} alt={frame.alt} ratio="4 / 5" sizes="(min-width: 900px) 34vw, 92vw" parallax={20} />
            </div>
          </figure>
          <div className="ld-say__body">
            {paras.map((para, i) => (
              <Scrub key={i} text={para} span={0.3} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- where it belongs ----------------------------------------------------- */

/** Each kind of building is a card, and the cards pile up as you go: the next
    one slides over the last, which steps back and dims under it. */
function Belongs({ lift }) {
  const apps = useMemo(() => (lift.applications ?? []).filter((a) => PLACES[a.slug]), [lift.applications])
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const [seen, setSeen] = useState(() => new Set())

  useEffect(() => {
    if (!ref.current) return undefined
    const cards = [...ref.current.querySelectorAll('.ld-card')]
    const io = new IntersectionObserver(
      (entries) => {
        const hit = entries.filter((e) => e.isIntersecting).map((e) => +e.target.dataset.i)
        if (hit.length) setSeen((old) => new Set([...old, ...hit]))
      },
      { threshold: 0.35 },
    )
    cards.forEach((c) => io.observe(c))
    return () => io.disconnect()
  }, [apps.length])

  useEffect(() => {
    if (reduced || !ref.current) return undefined
    const slots = [...ref.current.querySelectorAll('.ld-stack__slot')]
    const last = slots.map(() => -1)
    const tick = () => {
      const vh = window.innerHeight
      const box = ref.current.getBoundingClientRect()
      if (box.bottom < -vh * 0.5 || box.top > vh * 1.5) return
      slots.forEach((slot, i) => {
        const r = slot.getBoundingClientRect()
        // how far this card has come into view, and how far the next has come over it
        const arrive = clamp01((vh - r.top) / (vh * 0.75))
        const next = slots[i + 1]?.getBoundingClientRect()
        const cover = next ? clamp01(1 - (next.top - r.top) / r.height) : 0
        const key = arrive + cover * 10
        if (Math.abs(key - last[i]) < 0.002) return
        last[i] = key
        slot.style.setProperty('--in', arrive.toFixed(4))
        slot.style.setProperty('--q', cover.toFixed(4))
      })
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced, apps.length])

  if (!apps.length) return null

  return (
    <section className="section on-stone ld-for">
      <div className="shell">
        <div className="ld-for__head">
          <Reveal>
            <h2 className="ld-h2">Where it belongs.</h2>
          </Reveal>
          <Reveal delay={80}>
            <p className="ld-note">
              {apps.length} kinds of building the {lift.short_name} is specified for, and what each one asks of it.
            </p>
          </Reveal>
        </div>

        <div ref={ref} className={`ld-stack ${reduced ? 'is-still' : ''}`}>
          {apps.map((a, i) => {
            const { Icon, src } = PLACES[a.slug]
            return (
              <div className="ld-stack__slot" key={a.slug} style={{ '--i': i }}>
                <article className={`ld-card ${seen.has(i) ? 'is-in' : ''}`} data-i={i}>
                  <div className="ld-card__copy">
                    <p className="ld-card__n">
                      {String(i + 1).padStart(2, '0')} <span>/ {String(apps.length).padStart(2, '0')}</span>
                    </p>
                    <span className="ld-card__icon">
                      <Icon size={34} />
                    </span>
                    <h3>{a.name}</h3>
                    <p className="ld-card__text">{a.description}</p>
                  </div>
                  <div className="ld-card__media">
                    <Img src={src} alt={a.name} sizes="(min-width: 900px) 46vw, 92vw" />
                  </div>
                </article>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* --- the figures, beside the film ----------------------------------------- */

function Film({ lift, sectionRef }) {
  const videoRef = useRef(null)
  const figRef = useRef(null)
  const reduced = useReducedMotion()
  const wide = useMediaQuery('(min-width: 900px) and (hover: hover)')
  const scrub = wide && !reduced
  const base = `/media/lifts/${lift.slug}`

  // the doors answer the scroll: the section's travel is the film's timeline
  useEffect(() => {
    if (!scrub) return undefined
    const v = videoRef.current
    const el = sectionRef.current
    if (!v || !el) return undefined
    let cur = 0
    let shownAt = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh * 0.5 || r.top > vh * 1.5) return
      const p = clamp01((vh * 0.75 - r.top) / Math.max(1, r.height - vh * 0.75))
      cur += (p - cur) * 0.12
      if (!v.duration || v.seeking) return
      const t = cur * (v.duration - 0.05)
      if (Math.abs(t - shownAt) < 1 / 48) return
      shownAt = t
      v.currentTime = t
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [scrub, sectionRef])

  useScrollVar(figRef, { from: 1, to: 0.32 })

  return (
    <figure ref={figRef} className="ld-film">
      <div className="ld-film__frame">
        {scrub ? (
          <video
            ref={videoRef}
            src={`${base}-scrub.mp4`}
            poster={`${base}.jpg`}
            muted
            playsInline
            preload="auto"
            aria-hidden="true"
            tabIndex={-1}
          />
        ) : (
          <VideoLoop src={`${base}.mp4`} poster={`${base}.jpg`} />
        )}
      </div>
    </figure>
  )
}

function ShaftDiagram({ lift }) {
  return (
    <svg
      className="ld-shaft"
      viewBox="0 0 320 420"
      role="img"
      aria-label={`Shaft section: headroom ${lift.headroom || 'by survey'}, pit ${lift.pit_depth || 'by survey'}`}
    >
      <defs>
        <pattern id="ld-hatch" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="7" stroke="currentColor" strokeWidth="1" opacity="0.3" />
        </pattern>
      </defs>
      <rect className="ld-shaft__fill" x="61" y="21" width="198" height="70" fill="url(#ld-hatch)" />
      <rect className="ld-shaft__fill" x="61" y="346" width="198" height="53" fill="url(#ld-hatch)" />
      <g className="ld-shaft__lines" fill="none" stroke="currentColor">
        <rect pathLength="1" x="60" y="20" width="200" height="380" strokeWidth="1.5" />
        <line pathLength="1" x1="60" y1="91" x2="260" y2="91" strokeWidth="1" opacity="0.6" />
        <line pathLength="1" x1="60" y1="345" x2="260" y2="345" strokeWidth="1" opacity="0.6" />
        <line pathLength="1" x1="34" y1="21" x2="34" y2="90" strokeWidth="1" />
        <line pathLength="1" x1="34" y1="346" x2="34" y2="399" strokeWidth="1" />
        <line pathLength="1" x1="286" y1="92" x2="286" y2="344" strokeWidth="1" />
      </g>
      <g className="ld-shaft__car" fill="none" stroke="var(--accent)">
        <rect pathLength="1" x="88" y="150" width="144" height="150" strokeWidth="1.5" />
        <line pathLength="1" x1="160" y1="150" x2="160" y2="300" strokeWidth="1" opacity="0.4" />
      </g>
      <g className="ld-shaft__text" fill="currentColor">
        <text x="18" y="56" transform="rotate(-90 18 56)" textAnchor="middle">HEADROOM</text>
        <text x="18" y="373" transform="rotate(-90 18 373)" textAnchor="middle">PIT</text>
        <text x="304" y="218" transform="rotate(-90 304 218)" textAnchor="middle">TRAVEL</text>
        {lift.headroom && <text x="160" y="60" textAnchor="middle" className="ld-shaft__v">{lift.headroom}</text>}
        {lift.pit_depth && <text x="160" y="377" textAnchor="middle" className="ld-shaft__v">{lift.pit_depth}</text>}
        {lift.shaft_footprint && <text x="160" y="326" textAnchor="middle" className="ld-shaft__v ld-shaft__v--car">{lift.shaft_footprint}</text>}
      </g>
    </svg>
  )
}

const VARIANT_ROWS = [
  ['Capacity', 'capacity', UsersMark],
  ['Passengers', 'persons', UsersMark],
  ['Speed', 'speed', GaugeMark],
  ['Shaft', 'shaft', CrosshairMark],
]

/** The sizes stand up one after another as the block comes up the screen. */
function Variants({ lift }) {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.98, to: 0.3 })

  return (
    <div ref={ref} className="ld-block ld-sizes" id="variants">
      <Reveal>
        <h2 className="ld-h2">Sized to the job.</h2>
      </Reveal>
      <div className="ld-sizes__row">
        {lift.variants.map((v, i) => (
          <Link
            key={v.code}
            to={`/contact?lift=${lift.slug}&variant=${encodeURIComponent(v.code)}`}
            className="ld-size"
            style={{ '--i': i }}
            aria-label={`Enquire about the ${v.name}, ${v.code}`}
          >
            <span className="ld-size__in">
              <span className="ld-size__code">{v.code}</span>
              <span className="ld-size__name">{v.name}</span>
              {v.description && <span className="ld-size__desc">{v.description}</span>}
              <span className="ld-size__rows">
                {VARIANT_ROWS.filter(([, key]) => v[key] && v[key] !== '—').map(([label, key, Icon]) => (
                  <span key={key}>
                    <Icon size={16} />
                    <em>{label}</em>
                    <strong>{v[key]}</strong>
                  </span>
                ))}
              </span>
              <span className="ld-size__go">
                Enquire <Arrow size={14} />
              </span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}

function Figures({ lift }) {
  const ref = useRef(null)
  const dimsRef = useRef(null)
  useScrollVar(dimsRef, { from: 0.95, to: 0.15 })
  const groups = useMemo(() => {
    const out = new Map()
    for (const s of lift.specs ?? []) {
      if (!out.has(s.group)) out.set(s.group, [])
      out.get(s.group).push(s)
    }
    return [...out.entries()]
  }, [lift.specs])

  return (
    <section ref={ref} className="section on-paper ld-fig" id="figures">
      <div className="shell ld-fig__inner">
        <Film lift={lift} sectionRef={ref} />

        <div className="ld-fig__col">
          {lift.variants?.length > 0 && <Variants lift={lift} />}

          <div ref={dimsRef} className="ld-block ld-dimsblock" id="dimensions">
            <Reveal>
              <h2 className="ld-h2">What the building has to give it.</h2>
              <p className="ld-note">
                Indicative figures for the standard configurations. The specification for your project is set by survey.
              </p>
            </Reveal>
            <div className="ld-dims">
              <ShaftDiagram lift={lift} />
              <div className="ld-dims__groups">
                {groups.map(([group, rows], gi) => (
                  <div className="ld-specgroup" key={group} style={{ '--i': gi }}>
                    <h3 className="ld-label">{group}</h3>
                    <dl className="ld-spec">
                      {rows.map((r) => (
                        <div key={r.id}>
                          <dt>{r.label}</dt>
                          <dd>
                            {r.value}
                            {r.note && <small>{r.note}</small>}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- in place ------------------------------------------------------------- */

const KIND_ORDER = { gallery: 0, cabin: 1, detail: 2 }
const lerp = (p, a, b, from, to) => from + (to - from) * clamp01((p - a) / (b - a))

/* where each column rests, and where it drifts to once the wall stands up */
const COLUMNS = [
  { from: -10, to: 2 },
  { from: 15, to: 5 },
  { from: -10, to: 2 },
]
const PER_COLUMN = 4
const SHARED_FRAMES = [
  '/media/frames/kashi-cabin.jpg',
  '/media/frames/lekha-cabin.jpg',
  '/media/frames/chath-cabin.jpg',
  '/media/frames/owaisi-cabin.jpg',
  '/media/frames/kashi-shaft.jpg',
  '/media/frames/chilkuru-capsule.jpg',
  '/media/frames/lacheta-glass.jpg',
  '/media/frames/niloufer-cabin.jpg',
]

/** The installations hang as a wall of frames. It arrives lying back, almost
    flat to the floor; the scroll stands it upright, draws it in, and then lets
    the three columns slide past each other. */
function Plates({ lift }) {
  const pool = useMemo(() => {
    const own = [...(lift.images ?? [])]
      .sort((a, b) => (KIND_ORDER[a.kind] ?? 3) - (KIND_ORDER[b.kind] ?? 3))
      .map((g) => ({ src: g.src, alt: g.alt || g.caption || lift.name }))
    const more = [ROOMS[lift.slug]?.src, lift.hero_image_url, `/media/lifts/${lift.slug}.jpg`, `/media/lifts/${lift.slug}-open.jpg`]
      .filter(Boolean)
      .map((src) => ({ src, alt: lift.name }))
    // a lift with few frames of its own borrows from the wider body of work,
    // so the wall never has to hang the same picture twice in view
    const shared = own.length + more.length < 12 ? SHARED_FRAMES.map((src) => ({ src, alt: 'A Zion installation' })) : []
    const seen = new Set()
    return [...own, ...more, ...shared].filter((g) => !seen.has(g.src) && seen.add(g.src)).slice(0, 12)
  }, [lift])

  const sec = useRef(null)
  const reduced = useReducedMotion()
  const [near, setNear] = useState(false)
  const [seen, setSeen] = useState(false)

  useEffect(() => {
    if (!sec.current) return undefined
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setNear(true), { rootMargin: '100% 0px' })
    const head = new IntersectionObserver(([e]) => e.isIntersecting && setSeen(true), { threshold: 0.5 })
    io.observe(sec.current)
    head.observe(sec.current.querySelector('.ld-gal__head'))
    return () => {
      io.disconnect()
      head.disconnect()
    }
  }, [])

  useEffect(() => {
    if (reduced || !sec.current) return undefined
    const run = sec.current.querySelector('.ld-gal__run')
    const wall = sec.current.querySelector('.ld-gal__wall')
    const cols = [...sec.current.querySelectorAll('.ld-gal__col')]
    let cur = 0
    let last = -1
    const tick = () => {
      const r = run.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh * 0.5 || r.top > vh * 1.5) return
      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      cur += (p - cur) * 0.12
      if (Math.abs(cur - last) < 0.0004) return
      last = cur
      const tilt = lerp(cur, 0, 0.5, 75, 0)
      const scale = lerp(cur, 0.5, 0.9, 1.2, 1)
      wall.style.transform = `rotateX(${tilt.toFixed(2)}deg) scale(${scale.toFixed(4)})`
      cols.forEach((col, i) => {
        const c = COLUMNS[i % COLUMNS.length]
        col.style.transform = `translate3d(0, ${lerp(cur, 0.5, 1, c.from, c.to).toFixed(2)}%, 0)`
      })
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced, pool.length])

  if (!pool.length) return null

  // twelve frames from however many the lift has, never the same one side by side
  const columns = COLUMNS.map((_, c) =>
    Array.from({ length: PER_COLUMN }, (_, r) => pool[(c * PER_COLUMN + r + (pool.length < 5 ? c : 0)) % pool.length]),
  )

  return (
    <section ref={sec} className={`ld-gal ${reduced ? 'is-still' : 'is-pinned'}`}>
      <div className={`ld-gal__head ${seen || reduced ? 'is-in' : ''}`}>
        <h2>
          <span style={{ '--i': 0 }}>In place.</span>
        </h2>
        <p style={{ '--i': 1 }}>
          {lift.name}, as built — frames from Zion&rsquo;s own installations and the rooms they stand in.
        </p>
        <Link to="/gallery" className="ld-gal__link" style={{ '--i': 2 }}>
          The full gallery <Arrow size={14} />
        </Link>
      </div>
      <div className="ld-gal__glow" aria-hidden="true" />

      <div className="ld-gal__run">
        <div className="ld-gal__stage">
          <div className="ld-gal__wall">
            {columns.map((col, c) => (
              <div className={`ld-gal__col ld-gal__col--${c}`} key={c}>
                {col.map((g, r) => (
                  <div className="ld-gal__cell" key={`${c}-${r}`}>
                    <Img src={g.src} alt={c * PER_COLUMN + r < pool.length ? g.alt : ''} priority={near} sizes="(min-width: 900px) 34vw, 45vw" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- what drives it -------------------------------------------------------- */

const PART_ICONS = { drive: CogMark, motor: CogMark, controller: WaveMark, door: DoorMark, safety: Shield }

function Engineering({ lift, partners }) {
  const head = useRef(null)
  useScrollVar(head, { from: 0.95, to: 0.12 })

  return (
    <section className="section ld-eng" id="drive">
      <div className="shell">
        <div ref={head} className="ld-eng__head">
          <div className="ld-eng__copy">
            <Reveal variant="fade">
              <p className="ld-label">The drive</p>
            </Reveal>
            <RiseIn as="h2" className="ld-eng__title" text={`${lift.drive}.`} />
            <Reveal delay={120}>
              <p className="ld-eng__body">
                {lift.machine_room === 'Not required'
                  ? 'The machine mounts on the guide rails at the head of the shaft, so the building gives up no room above it. A closed-loop VVVF drive shapes acceleration into a curve and holds levelling within a few millimetres, loaded or empty.'
                  : 'A power unit sized to the duty, sited where the building has space for it, driving the lift through a controlled ramp rather than a step. Levelling is held tight and re-levelled on load change.'}
              </p>
            </Reveal>
            {partners?.length > 0 && (
              <div className="ld-eng__parts">
                {partners.slice(0, 4).map((p, i) => {
                  const Icon = PART_ICONS[p.role] ?? CogMark
                  return (
                    <div className="ld-part" key={p.id} style={{ '--i': i }}>
                      <span className="ld-part__icon">
                        <Icon size={24} />
                      </span>
                      <h3>{p.name}</h3>
                      {p.component && <p>{p.component}</p>}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          <div className="ld-eng__media">
            <div className="ld-eng__tilt">
            <Img
              src="/media/frames/kashi-machine.jpg"
              alt="Drive and sheave assembly"
              ratio="4 / 5"
              sizes="(min-width: 900px) 38vw, 92vw"
              parallax={26}
            />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- what keeps it safe ---------------------------------------------------- */

const SAFETY_ICONS = {
  overload: WeightMark,
  'power-failure': Bolt,
  'emergency-braking': GaugeMark,
  'fire-mode': FlameMark,
  'door-protection': DoorMark,
  'emergency-comms': Phone,
  seismic: LayersMark,
}

/** The lift in section, and its safety systems found on it one by one. The
    drawing holds one side of the screen; as you scroll, the camera moves
    through the shaft to each system, that part of the drawing lights and traces
    itself, and the account of it comes up alongside. On a phone the drawing
    rides along at the top while the accounts scroll beneath it. */
function Safety({ lift }) {
  const items = lift.safety_features ?? []
  const n = items.length
  const sec = useRef(null)
  const fill = useRef(null)
  const reduced = useReducedMotion()
  const wide = useMediaQuery('(min-width: 900px)')
  const held = wide && !reduced && n > 1
  const [active, setActive] = useState(0)

  useEffect(() => {
    const el = sec.current
    if (!el || n < 2) return undefined
    let last = -1
    let shown = -1
    const pick = (i) => {
      if (i !== shown) {
        shown = i
        setActive(i)
      }
    }
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < 0 || r.top > vh) return
      if (held) {
        const p = clamp01(-r.top / Math.max(1, r.height - vh))
        if (Math.abs(p - last) > 0.0005) {
          last = p
          if (fill.current) fill.current.style.transform = `scaleX(${p.toFixed(4)})`
        }
        pick(Math.min(n - 1, Math.floor(p * n)))
        return
      }
      // not held: whichever account is nearest the reading line is the one in hand
      let nearest = 0
      let best = Infinity
      el.querySelectorAll('.ld-ss__panel').forEach((panel, i) => {
        const b = panel.getBoundingClientRect()
        const d = Math.abs(b.top + Math.min(b.height, vh * 0.3) / 2 - vh * 0.66)
        if (d < best) {
          best = d
          nearest = i
        }
      })
      pick(nearest)
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [held, n])

  if (!n) return null

  const go = (i) => {
    const el = sec.current
    if (!held) {
      el.querySelectorAll('.ld-ss__panel')[i]?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' })
      return
    }
    const top = el.getBoundingClientRect().top + window.scrollY
    const y = top + ((i + 0.5) / n) * (el.offsetHeight - window.innerHeight)
    if (window.__lenis) window.__lenis.scrollTo(y, { duration: 1.1 })
    else window.scrollTo({ top: y, behavior: 'smooth' })
  }

  const current = items[active] ?? items[0]

  return (
    <section
      ref={sec}
      className={`ld-ss ${held ? 'is-held' : 'is-free'}`}
      id="safety"
      style={held ? { height: `calc(100svh + ${n * 60}svh)` } : undefined}
    >
      <div className="ld-ss__stage">
        <div className="shell ld-ss__inner">
          <figure className="ld-ss__draw">
            <SafetyDrawing active={current.slug} />
            <figcaption className="sr-only">{current.name} highlighted on a section through the lift shaft.</figcaption>
            <span className="ld-ss__corner ld-ss__corner--tl" aria-hidden="true">
              Section A–A
            </span>
            <span className="ld-ss__corner ld-ss__corner--tr" aria-hidden="true">
              {String(active + 1).padStart(2, '0')} / {String(n).padStart(2, '0')}
            </span>
            <span className="ld-ss__corner ld-ss__corner--bl" key={current.slug} aria-hidden="true">
              {current.name}
            </span>
          </figure>

          <div className="ld-ss__side">
            <header className="ld-ss__top">
              <p className="ld-label">Fitted as standard</p>
              <h2 className="ld-ss__title">
                {n} systems, <em>always on.</em>
              </h2>
            </header>

            <div className="ld-ss__panels">
              {items.map((f, i) => (
                <article
                  className={`ld-ss__panel ${i === active ? 'is-on' : i < active ? 'is-past' : ''}`}
                  key={f.slug}
                  aria-hidden={held && i !== active}
                >
                  <p className="ld-ss__n">
                    {String(i + 1).padStart(2, '0')} <span>— {f.standard}</span>
                  </p>
                  <h3>{f.name}</h3>
                  <p className="ld-ss__head">{f.headline}</p>
                  {f.description && <p className="ld-ss__text">{f.description}</p>}
                  {f.test_procedure && (
                    <p className="ld-ss__test">
                      <span>How it is tested</span>
                      {f.test_procedure}
                    </p>
                  )}
                </article>
              ))}
            </div>

            <nav className="ld-ss__index" aria-label="Safety systems">
              <ol>
                {items.map((f, i) => {
                  const Icon = SAFETY_ICONS[f.slug] ?? Shield
                  return (
                    <li key={f.slug}>
                      <button
                        type="button"
                        className={i === active ? 'is-on' : ''}
                        aria-current={i === active}
                        aria-label={f.name}
                        title={f.name}
                        onClick={() => go(i)}
                      >
                        <Icon size={20} />
                      </button>
                    </li>
                  )
                })}
              </ol>
              <span className="ld-ss__line" aria-hidden="true">
                <span ref={fill} />
              </span>
            </nav>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- in the field --------------------------------------------------------- */

function Field({ lift, projects }) {
  if (!projects?.length) return null
  return (
    <ProjectsReel
      projects={projects}
      eyebrow="In the field"
      title={
        <>
          The {lift.short_name},
          <br />
          installed.
        </>
      }
      lead="Buildings where this system is running today."
    />
  )
}

/* --- the enquiry ---------------------------------------------------------- */

/** The page ends the way a journey does: the doors part, and there is the ask. */
function Enquire({ lift }) {
  const ref = useRef(null)
  const site = useSite()
  const reduced = useReducedMotion()
  const fine = useMediaQuery('(hover: hover) and (pointer: fine)')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (reduced) {
      setOpen(true)
      return undefined
    }
    const el = ref.current
    const left = el.querySelector('.ld-ask__door--l')
    const right = el.querySelector('.ld-ask__door--r')
    const inner = el.querySelector('.ld-ask__inner')
    let last = -1
    let wasOpen = false
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh * 0.2 || r.top > vh * 1.2) return
      const raw = clamp01((vh * 0.92 - r.top) / (vh * 0.8))
      if (Math.abs(raw - last) < 0.001) return
      last = raw
      // doors ease away from rest and ease into their pockets
      const p = raw < 0.5 ? 2 * raw * raw : 1 - Math.pow(-2 * raw + 2, 2) / 2
      left.style.transform = `translate3d(${(-p * 101).toFixed(2)}%, 0, 0)`
      right.style.transform = `translate3d(${(p * 101).toFixed(2)}%, 0, 0)`
      inner.style.transform = `scale(${(0.93 + p * 0.07).toFixed(4)})`
      const now = raw > 0.55
      if (now !== wasOpen) {
        wasOpen = now
        setOpen(now)
      }
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced])

  // the warm light follows the hand; the button leans towards it
  useEffect(() => {
    if (!fine || reduced) return undefined
    const el = ref.current
    const btn = el.querySelector('.ld-ask__go')
    const gx = gsap.quickTo(el, '--mx', { duration: 0.9, ease: 'power3.out' })
    const gy = gsap.quickTo(el, '--my', { duration: 0.9, ease: 'power3.out' })
    const bx = gsap.quickTo(btn, 'x', { duration: 0.5, ease: 'power3.out' })
    const by = gsap.quickTo(btn, 'y', { duration: 0.5, ease: 'power3.out' })
    const move = (e) => {
      const r = el.getBoundingClientRect()
      gx(((e.clientX - r.left) / r.width) * 100)
      gy(((e.clientY - r.top) / r.height) * 100)
      const b = btn.getBoundingClientRect()
      const dx = e.clientX - (b.left + b.width / 2)
      const dy = e.clientY - (b.top + b.height / 2)
      const pull = Math.hypot(dx, dy) < 170
      bx(pull ? dx * 0.28 : 0)
      by(pull ? dy * 0.28 : 0)
    }
    const leave = () => {
      bx(0)
      by(0)
    }
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerleave', leave)
    return () => {
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerleave', leave)
    }
  }, [fine, reduced])

  return (
    <section ref={ref} className={`ld-ask ${open ? 'is-open' : ''}`} id="enquire">
      <div className="ld-ask__glow" aria-hidden="true" />
      <div className="ld-ask__inner">
        <p className="ld-label">Next step</p>
        <h2 className="ld-ask__title ld-rise">
          <Rise text={`Enquire about the ${lift.short_name}.`} />
        </h2>
        <p className="ld-ask__lead">
          Send the number of levels, the building type and a plan if you have one. We will come back with a
          specification and a figure.
        </p>
        <div className="ld-ask__actions">
          <Link to={`/contact?lift=${lift.slug}`} className="ld-ask__go">
            <span>Get a quote</span>
            <span className="ld-ask__go-ring">
              <Arrow size={18} />
            </span>
          </Link>
          {site.phone && (
            <a href={telHref(site.phone)} className="ld-ask__alt">
              {site.phone}
            </a>
          )}
        </div>
      </div>
      <span className="ld-ask__door ld-ask__door--l" aria-hidden="true" />
      <span className="ld-ask__door ld-ask__door--r" aria-hidden="true" />
    </section>
  )
}

/* --- the next lift -------------------------------------------------------- */

function NextLift({ lift, lifts }) {
  const list = (lifts ?? []).filter((l) => ROOMS[l.slug])
  const at = list.findIndex((l) => l.slug === lift.slug)
  const next = list.length > 1 ? list[(at + 1) % list.length] : lift.related?.[0]
  const scene = useScene(next ?? lift)
  const wrap = useRef(null)
  useScrollVar(wrap, { from: 1, to: 0.18 })
  if (!next) return null

  return (
    <div ref={wrap} className="ld-next-wrap">
    <Link to={`/lifts/${next.slug}`} className="ld-next" aria-label={`Next lift: ${next.name}`}>
      <span className="ld-next__scene">
        <Img key={scene.src} src={scene.src} alt="" sizes="100vw" objectPosition={scene.pos} />
      </span>
      <span className="ld-next__copy">
        <span className="ld-next__label">Next lift</span>
        <span className="ld-next__name">{next.name}</span>
        <span className="ld-next__line">{next.tagline}</span>
      </span>
      <span className="ld-next__ring" aria-hidden="true">
        <Arrow size={20} />
      </span>
    </Link>
    </div>
  )
}

/* --- the standing enquiry ------------------------------------------------- */

function EnquirePill({ lift }) {
  const [on, setOn] = useState(false)

  useEffect(() => {
    let raf = 0
    const read = () => {
      raf = 0
      const past = window.scrollY > window.innerHeight * 0.9
      const end = document.querySelector('.ld-ask')
      const before = !end || end.getBoundingClientRect().top > window.innerHeight * 0.6
      // the wall of frames holds the whole screen; nothing should stand over it
      const reel = document.querySelector('.ld-gal__run')?.getBoundingClientRect()
      const inReel = reel && reel.top < window.innerHeight * 0.4 && reel.bottom > window.innerHeight * 0.6
      // the cabin studio carries its own ask
      const studio = document.querySelector('.cs')?.getBoundingClientRect()
      const inStudio = studio && studio.top < window.innerHeight * 0.75 && studio.bottom > window.innerHeight * 0.4
      setOn(past && before && !inReel && !inStudio)
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(read)
    }
    read()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <Link
      to={`/contact?lift=${lift.slug}`}
      className={`ld-pill ${on ? 'is-on' : ''}`}
      tabIndex={on ? 0 : -1}
      aria-hidden={!on}
    >
      <span>Enquire</span>
      <em>{lift.short_name}</em>
      <Arrow size={14} />
    </Link>
  )
}

/* --- page ----------------------------------------------------------------- */

function LiftPage({ slug }) {
  const { data: lift, loading, error } = useApi(`lifts/${slug}/`)
  const { data: lifts } = useApi('lifts/')
  const { data: finishes } = useApi('finishes/')
  const { data: projects } = useApi('projects/', { lift_type__slug: slug })
  const { data: partners } = useApi('partners/')

  useEffect(() => {
    if (lift) document.title = `${lift.name} — Zion Lifts`
  }, [lift])

  if (loading) {
    return (
      <div className="ld-hero ld-hero--wait" aria-busy="true">
        <div className="skeleton" />
      </div>
    )
  }

  if (error || !lift) {
    return (
      <section className="section">
        <div className="shell state">
          <p className="state__title">We could not find that lift.</p>
          <Link to="/lifts" className="btn btn--accent btn--sm">
            All lift systems <Arrow size={14} />
          </Link>
        </div>
      </section>
    )
  }

  return (
    <div className="ld">
      <Hero lift={lift} />
      <Statement lift={lift} />
      <Belongs lift={lift} />
      <Figures lift={lift} />
      <CabinStudio lift={lift} finishes={finishes} />
      <Plates lift={lift} />
      <Engineering lift={lift} partners={partners} />
      <Safety lift={lift} />
      <Field lift={lift} projects={projects} />
      <Enquire lift={lift} />
      <NextLift lift={lift} lifts={lifts} />
      <EnquirePill lift={lift} />
    </div>
  )
}

export default function LiftDetail() {
  const { slug } = useParams()
  /* keyed, so moving on to the next lift starts its page from the top state */
  return <LiftPage key={slug} slug={slug} />
}
