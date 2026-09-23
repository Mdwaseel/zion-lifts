import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import CERTIFICATIONS from '@/data/certifications'
import MILESTONES from '@/data/milestones'
import SERVICE_PILLARS from '@/data/servicePillars'
import { statsFor } from '@/data/stats'
import YearsTower from '@/components/YearsTower'
import Reveal from '@/components/Reveal'
import { Arrow, ArrowDown, PILLAR_ICONS, Shield } from '@/components/icons'
import { gsap } from '@/lib/gsap'
import { useApi, useMediaQuery, useReducedMotion } from '@/lib/hooks'
import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import { Rise, RiseIn, Scrub, clamp01, useScrollVar, whenIntroDone } from './lift/shared'
import './about.css'

/* ==========================================================================
   /about — who builds the lifts
   The same frame language as the lift pages, told as a ride: the room draws
   back, the origin is read into focus, the years are a building that goes up a
   storey at a time, the method is a stack of four cards, the factory is a zoom you fall
   into, the installations count themselves as you scroll, and the last frame
   opens onto an invitation to come and see it.
   ========================================================================== */

const pad = (n) => String(n).padStart(2, '0')

/* Two candidate designs of the "years" section sit one after the other so they
   can be shown side by side. Set this to false, and delete whichever of
   <Journey /> or <JourneyLanding /> loses, once one is chosen. */
const COMPARING = true

function Option({ letter, name }) {
  if (!COMPARING) return null
  return (
    <p className="ab-option">
      <strong>Design {letter}</strong>
      <span>{name}</span>
    </p>
  )
}
const fmt = (n) => new Intl.NumberFormat('en-IN').format(n)

/* --- the opening ---------------------------------------------------------- */

function Opening({ stats }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const site = useSite()
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

  return (
    <header ref={ref} className={`ab-hero ${shown ? 'is-in' : ''}`}>
      <div className="ab-hero__scene">
        <Img src="/media/frames/chilkuru-atrium.jpg" alt="" priority sizes="100vw" />
      </div>
      <div className="ab-hero__grade" aria-hidden="true" />

      <div className="ab-hero__copy">
        <p className="ld-label ab-hero__label">About Zion</p>
        <h1 className="ab-hero__title">
          <Rise text="Helping people move the right way." />
        </h1>
        <p className="ab-hero__lead">
          Founded in {site.founded_year} with one workshop and a straightforward purpose: to help people move better,
          safer and more comfortably. Today, {site.team_size} people, a manufacturing unit of our own, and more than{' '}
          {fmt(site.installations)} installations.
        </p>
      </div>

      <div className="ab-hero__foot">
        <dl className="ab-hero__stats">
          {(stats ?? []).map((s, i) => (
            <div key={s.label} style={{ '--i': i }}>
              <dd>{s.value}</dd>
              <dt>{s.label}</dt>
            </div>
          ))}
        </dl>
        <a href="#beginning" className="ab-hero__cue" aria-label="Scroll to the story">
          <ArrowDown size={16} />
        </a>
      </div>
    </header>
  )
}

/* --- where it began ------------------------------------------------------- */

function Beginning() {
  const sec = useRef(null)
  useScrollVar(sec, { from: 1, to: -0.9, name: '--s', ease: 0.1 })

  return (
    <section ref={sec} className="section on-stone ab-begin" id="beginning">
      <p className="ab-begin__ghost" aria-hidden="true">
        2012 · Hyderabad · 2012
      </p>
      <div className="shell">
        <Scrub
          className="ab-begin__line"
          text="Zion Lifts was founded on a simple observation: most of the lifts going into Indian buildings were being sold rather than engineered."
        />
        <div className="ab-begin__grid">
          <figure className="ab-begin__frame">
            <div className="ab-begin__tilt">
              <Img
                src="/media/sourced/factory-floor.jpg"
                alt="A manufacturing floor"
                ratio="4 / 5"
                sizes="(min-width: 900px) 34vw, 92vw"
                parallax={20}
              />
            </div>
          </figure>
          <div className="ab-begin__body">
            <Scrub
              span={0.3}
              text="The specification came from a price list, the survey happened after the order, and the maintenance contract was an afterthought."
            />
            <Scrub
              span={0.3}
              text="We started the other way round — survey first, specify second, quote third — and kept manufacturing close enough to fix what the survey found. Thirteen years later that is still the whole method."
            />
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- the years: a building that goes up -------------------------------------- */

/** Thirteen years, drawn as the thing the company works in: a building. Each
    milestone adds a storey with architecture of its own, a tower crane climbs
    with it, and a car rides the shaft to the new floor while the indicator
    beside the account counts up to the year — the way the one in the lift does. */
function Journey({ milestones }) {
  const items = (milestones ?? []).slice(0, 7)
  const n = items.length
  const sec = useRef(null)
  const site = useSite()
  const reduced = useReducedMotion()
  const narrow = useMediaQuery('(max-width: 899px)')
  const held = !reduced && n > 1
  const [active, setActive] = useState(0)
  const [dir, setDir] = useState(1)
  const prev = useRef(0)

  useEffect(() => {
    if (!held) return undefined
    const el = sec.current
    let shown = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < 0 || r.top > vh) return
      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      const i = Math.min(n - 1, Math.floor(p * n))
      if (i !== shown) {
        shown = i
        setActive(i)
      }
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [held, n])

  useEffect(() => {
    if (active !== prev.current) setDir(active > prev.current ? 1 : -1)
    prev.current = active
  }, [active])

  if (!n) return null

  const go = (i) => {
    if (!held) {
      setActive(i)
      return
    }
    const el = sec.current
    const top = el.getBoundingClientRect().top + window.scrollY
    const y = top + ((i + 0.5) / n) * (el.offsetHeight - window.innerHeight)
    if (window.__lenis) window.__lenis.scrollTo(y, { duration: 1.1 })
    else window.scrollTo({ top: y, behavior: 'smooth' })
  }

  const m = items[active]

  return (
    <section
      ref={sec}
      className={`ab-tower ${held ? 'is-held' : 'is-free'}`}
      id="journey"
      style={held ? { height: `calc(100svh + ${n * 58}svh)` } : undefined}
    >
      <div className="ab-tower__stage">
        <div className="shell ab-tower__inner">
          <header className="ab-tower__top">
            <Option letter="A" name="The building" />
            <h2>
              Thirteen years, <em>a floor at a time.</em>
            </h2>
            <p>Only real milestones. We would rather show seven honest ones than pad it out to twenty.</p>
          </header>

          <div className="ab-tower__draw">
            <YearsTower
              years={items.map((it) => it.year)}
              active={active}
              zoomed={narrow}
              sign={`${fmt(site.installations ?? 1750)}+`}
              onPick={go}
            />
          </div>

          <div className="ab-tower__side">
            {/* the indicator: the year, the way a lift shows a floor */}
            <p className={`ab-led ${dir > 0 ? 'is-up' : 'is-down'}`} key={`led-${m.year}`} aria-hidden="true">
              <span className="ab-led__arrow" />
              <span className="ab-led__num">{m.year}</span>
              <span className="ab-led__floor">L{active + 1}</span>
            </p>

            <div className="ab-tower__text" key={m.year} aria-live="polite">
              <h3>
                <span className="sr-only">{m.year}: </span>
                {m.title}
              </h3>
              <p>{m.description}</p>
            </div>

            <div className="ab-tower__plate">
              {items.map((it, i) => (
                <div key={it.year} className={`ab-tower__shot ${i <= active ? 'is-up' : ''}`}>
                  <Img src={it.image_url} alt="" sizes="(min-width: 900px) 30vw, 60vw" priority={i < 2} />
                </div>
              ))}
            </div>

            <ol className="ab-tower__years">
              {items.map((it, i) => (
                <li key={it.year}>
                  <button type="button" className={i === active ? 'is-on' : ''} aria-current={i === active} onClick={() => go(i)}>
                    {it.year}
                  </button>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- the years, design B: at the landing ----------------------------------- */

/** The same seven years, seen from where a passenger stands: a pair of steel
    doors, the indicator over them, and a car operating panel whose buttons are
    the years. Calling a year closes the doors, the indicator counts to it, and
    the doors open on that year's photograph. */
function JourneyLanding({ milestones }) {
  const items = (milestones ?? []).slice(0, 8)
  const n = items.length
  const sec = useRef(null)
  const reduced = useReducedMotion()
  const held = !reduced && n > 1
  const [active, setActive] = useState(0) // the year that has been called
  const [shown, setShown] = useState(0) // the year behind the doors
  const [open, setOpen] = useState(false)
  const [seen, setSeen] = useState(false)
  const [dir, setDir] = useState(1)

  // the doors stay shut until the landing is properly on screen (the milestones arrive after mount)
  useEffect(() => {
    const stage = sec.current?.querySelector('.ab-land__stage')
    if (!stage) return undefined
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setSeen(true), { threshold: 0.45 })
    io.observe(stage)
    return () => io.disconnect()
  }, [n])

  useEffect(() => {
    if (!held) return undefined
    const el = sec.current
    let last = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < 0 || r.top > vh) return
      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      const i = Math.min(n - 1, Math.floor(p * n))
      if (i !== last) {
        last = i
        setActive(i)
      }
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [held, n])

  // a call: doors close, the car travels, doors open on the new floor
  useEffect(() => {
    if (active === shown) {
      setOpen(true)
      return undefined
    }
    setDir(active > shown ? 1 : -1)
    setOpen(false)
    const t = setTimeout(() => setShown(active), reduced ? 0 : 640)
    return () => clearTimeout(t)
  }, [active, shown, reduced])

  if (!n) return null

  const call = (i) => {
    if (!held) {
      setActive(i)
      return
    }
    const el = sec.current
    const top = el.getBoundingClientRect().top + window.scrollY
    const y = top + ((i + 0.5) / n) * (el.offsetHeight - window.innerHeight)
    if (window.__lenis) window.__lenis.scrollTo(y, { duration: 1.1 })
    else window.scrollTo({ top: y, behavior: 'smooth' })
  }

  const m = items[shown]
  const parted = seen && open
  const travelling = active !== shown

  return (
    <section
      ref={sec}
      className={`ab-land ${held ? 'is-held' : 'is-free'}`}
      id="journey-b"
      style={held ? { height: `calc(100svh + ${n * 58}svh)` } : undefined}
    >
      <div className="ab-land__stage">
        <div className="shell ab-land__inner">
          <div className="ab-land__copy">
            <Option letter="B" name="The landing" />
            <h2>
              Thirteen years. <em>Going up.</em>
            </h2>
            <div className="ab-land__text" key={m.year} aria-live="polite">
              <p className="ab-land__year">{m.year}</p>
              <h3>{m.title}</h3>
              <p>{m.description}</p>
            </div>
          </div>

          {/* the landing: indicator, architrave, the pair of doors and what is behind them */}
          <div className={`ab-doorway ${parted ? 'is-open' : ''}`}>
            <p className={`ab-doorway__led ${travelling ? 'is-moving' : ''} ${dir > 0 ? 'is-up' : 'is-down'}`} aria-hidden="true">
              <span className="ab-doorway__arrow" />
              <span key={items[active].year}>{items[active].year}</span>
            </p>
            <div className="ab-doorway__frame">
              <div className="ab-doorway__cabin">
                {items.map((it, i) => (
                  <div key={it.year} className={`ab-doorway__shot ${i === shown ? 'is-on' : ''}`}>
                    <Img src={it.image_url} alt="" sizes="(min-width: 900px) 30vw, 70vw" priority={i < 2} />
                  </div>
                ))}
                <span className="ab-doorway__floor" aria-hidden="true">
                  L{shown + 1}
                </span>
              </div>
              <span className="ab-doorway__leaf ab-doorway__leaf--l" aria-hidden="true" />
              <span className="ab-doorway__leaf ab-doorway__leaf--r" aria-hidden="true" />
            </div>
            <span className="ab-doorway__sill" aria-hidden="true" />
          </div>

          {/* the car operating panel: the years are its floors, the newest at the top */}
          <nav className="ab-cop" aria-label="Years">
            <p className="ab-cop__plate">Zion</p>
            <ol>
              {items
                .map((it, i) => ({ it, i }))
                .reverse()
                .map(({ it, i }) => (
                  <li key={it.year}>
                    <button
                      type="button"
                      className={`${i === active ? 'is-on' : ''} ${i < active ? 'is-past' : ''}`}
                      aria-current={i === active}
                      aria-label={`${it.year}: ${it.title}`}
                      onClick={() => call(i)}
                    >
                      <span>{String(it.year).slice(2)}</span>
                    </button>
                    <em>{it.year}</em>
                  </li>
                ))}
            </ol>
            <p className="ab-cop__keys" aria-hidden="true">
              <span className="ab-cop__key ab-cop__key--open" />
              <span className="ab-cop__key ab-cop__key--close" />
            </p>
          </nav>
        </div>
      </div>
    </section>
  )
}

/* --- the method: four cards ------------------------------------------------ */

const STAGES = [
  ['Engineering', 'Understanding the building before anything is drawn — survey, traffic, structure, the constraints nobody wrote down.', '/media/frames/kashi-shaft.jpg'],
  ['Manufacturing', 'Lift frames, cabins and structural shafts built in-house at Jeedimetla, then load-tested before dispatch.', '/media/frames/kashi-structure.jpg'],
  ['Installation', 'Rails aligned, machine set, doors adjusted, lift commissioned — sequenced around a building that is often still in use.', '/media/frames/kashi-machine.jpg'],
  ['Support', 'Maintenance, safety testing and 24/7 breakdown cover, through the twenty-odd years that follow.', '/media/frames/chilkuru-panel.jpg'],
]

function Method({ team }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    if (reduced || !ref.current) return undefined
    const slots = [...ref.current.querySelectorAll('.ab-stack__slot')]
    const last = slots.map(() => -1)
    const tick = () => {
      const vh = window.innerHeight
      const box = ref.current.getBoundingClientRect()
      if (box.bottom < -vh * 0.5 || box.top > vh * 1.5) return
      slots.forEach((slot, i) => {
        const r = slot.getBoundingClientRect()
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
  }, [reduced])

  return (
    <section className="section on-paper ab-method">
      <div className="shell">
        <header className="ab-head">
          <RiseIn as="h2" className="ab-h2" text="From idea to installation." />
          <Reveal delay={100}>
            <p className="ab-lead">
              Four crews, one company. The people who survey the shaft are down the corridor from the people who build
              what goes in it.
            </p>
          </Reveal>
        </header>

        <div ref={ref} className={`ab-stack ${reduced ? 'is-still' : ''}`}>
          {STAGES.map(([title, body, src], i) => {
            const crew = (team ?? []).find((t) => t.name === title || (title === 'Support' && t.name === 'Service'))
            return (
              <div className="ab-stack__slot" key={title} style={{ '--i': i }}>
                <article className="ab-card">
                  <div className="ab-card__media">
                    <Img src={src} alt="" sizes="(min-width: 900px) 46vw, 92vw" />
                  </div>
                  <div className="ab-card__copy">
                    <p className="ab-card__n">
                      {pad(i + 1)} <span>/ {pad(STAGES.length)}</span>
                    </p>
                    <h3>{title}</h3>
                    <p className="ab-card__text">{body}</p>
                    {crew && (
                      <p className="ab-card__crew">
                        <em>{crew.role}</em>
                        {crew.bio}
                      </p>
                    )}
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

/* --- inside the factory: a zoom you fall into ----------------------------- */

const FACTORY_STEPS = [
  ['Fabrication', 'Raw material into components.'],
  ['Assembly', 'Components into systems.'],
  ['Testing', 'Systems into a tested lift.'],
  ['Dispatch', 'Factory to site.'],
]

/* the frame in the middle grows to fill the screen; the ones round it grow
   faster and leave past the edges */
const ZOOM = [
  // the centre frame ends up filling the screen, so it is the one full-size plate: looking up a shaft
  { src: '/media/process/process-structure.jpg', k: 4, box: { top: '37.5%', left: '37.5%', width: '25%', height: '25%' } },
  { src: '/media/sourced/factory-machining.jpg', k: 5, box: { top: '7%', left: '55%', width: '35%', height: '27%' } },
  { src: '/media/sourced/factory-welding.jpg', k: 6, box: { top: '17%', left: '9%', width: '21%', height: '42%' } },
  { src: '/media/frames/kashi-structure.jpg', k: 5, box: { top: '39%', left: '67%', width: '24%', height: '25%' } },
  { src: '/media/sourced/people-engineer.jpg', k: 6, box: { top: '66%', left: '33%', width: '21%', height: '26%' } },
  { src: '/media/sourced/macro-bearing.jpg', k: 8, box: { top: '68%', left: '5%', width: '25%', height: '24%' } },
  { src: '/media/sourced/factory-assembly.jpg', k: 9, box: { top: '70%', left: '66%', width: '16%', height: '18%' } },
]

function Factory() {
  const run = useRef(null)
  const reduced = useReducedMotion()
  useScrollVar(run, { from: 0, to: -2, name: '--z', ease: 0.12 })

  return (
    <section className="ab-factory" id="factory">
      <header className="shell ab-head ab-factory__head">
        <RiseIn as="h2" className="ab-h2" text="Where elevators take shape." />
        <Reveal delay={100}>
          <p className="ab-lead">
            Fabrication came in-house in 2014, so lift frames, cabins and structural shafts are built to our own
            tolerances rather than bought in.
          </p>
        </Reveal>
      </header>

      <div ref={run} className={`ab-zoom ${reduced ? 'is-still' : ''}`}>
        <div className="ab-zoom__stage">
          {ZOOM.map((z, i) => (
            <div className="ab-zoom__el" key={z.src} style={{ '--k': z.k, zIndex: i === 0 ? 1 : 2 }}>
              <div className="ab-zoom__box" style={z.box}>
                <Img src={z.src} alt="" sizes={i === 0 ? '100vw' : '(min-width: 900px) 36vw, 50vw'} />
              </div>
            </div>
          ))}
          <ol className="ab-zoom__steps">
            {FACTORY_STEPS.map(([title, line], i) => (
              <li key={title} style={{ '--i': i }}>
                <span>{pad(i + 1)}</span>
                <strong>{title}</strong>
                <em>{line}</em>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

/* --- tested, then recorded ------------------------------------------------ */

function Quality({ certifications, awards }) {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.2 })
  if (!certifications?.length) return null

  return (
    <section className="section on-stone ab-quality">
      <div className="shell">
        <header className="ab-head">
          <RiseIn as="h2" className="ab-h2" text="Tested, then recorded." />
          <Reveal delay={100}>
            <p className="ab-lead">
              Certification only means anything if the tests behind it actually happen. These are the ones that do.
            </p>
          </Reveal>
        </header>

        <div ref={ref} className="ab-certs">
          {certifications.map((c, i) => (
            <article className="ab-cert" key={c.id} style={{ '--i': i }}>
              <div className="ab-cert__in">
                <span className="ab-cert__icon">
                  <Shield size={26} />
                </span>
                <p className="ab-cert__n">{pad(i + 1)}</p>
                <h3>{c.name}</h3>
                {c.issuer && <p className="ab-cert__issuer">{c.issuer}</p>}
                <p className="ab-cert__desc">{c.description}</p>
                {c.reference && <p className="ab-cert__ref">{c.reference}</p>}
              </div>
            </article>
          ))}
        </div>

        {awards?.length > 0 && (
          <ul className="ab-awards">
            {awards.map((a) => (
              <Reveal as="li" key={a.id}>
                <span>{a.year}</span>
                <strong>{a.name}</strong>
                <em>{a.organisation}</em>
              </Reveal>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

/* --- the installations count themselves ----------------------------------- */

const MOSAIC = [
  '/media/frames/lekha-cabin.jpg',
  '/media/frames/owaisi-lobby.jpg',
  '/media/frames/chath-facade.jpg',
  '/media/interiors/interior-03.jpg',
  '/media/frames/lacheta-lobby.jpg',
  '/media/frames/kashi-cabin.jpg',
]

function Installed() {
  const site = useSite()
  const sec = useRef(null)
  const num = useRef(null)
  const reduced = useReducedMotion()
  const total = site.installations ?? 1750

  // the figure is driven by the scroll: it counts as the section climbs the screen
  useEffect(() => {
    const el = sec.current
    if (reduced) {
      num.current.textContent = fmt(total)
      el.style.setProperty('--c', '1')
      return undefined
    }
    let cur = 0
    let last = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh * 0.3 || r.top > vh * 1.3) return
      const p = clamp01((vh * 0.85 - r.top) / (vh * 0.85 + r.height * 0.25))
      cur += (p - cur) * 0.12
      if (Math.abs(cur - last) < 0.0006) return
      last = cur
      // ease out, so it slows as it lands on the figure
      const e = 1 - Math.pow(1 - clamp01(cur * 1.15), 3)
      num.current.textContent = fmt(Math.round(e * total))
      el.style.setProperty('--c', cur.toFixed(4))
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced, total])

  return (
    <section ref={sec} className="ab-count">
      <div className="ab-count__wall" aria-hidden="true">
        {MOSAIC.map((src, i) => (
          <div className="ab-count__tile" key={src} style={{ '--i': i }}>
            <Img src={src} alt="" sizes="(min-width: 900px) 22vw, 44vw" />
          </div>
        ))}
      </div>
      <div className="ab-count__veil" aria-hidden="true" />
      <div className="shell ab-count__copy">
        <p className="ld-label">Installed</p>
        <p className="ab-count__num">
          <span ref={num}>0</span>
          <em>+</em>
        </p>
        <p className="ab-count__label">
          lifts installed across residential, commercial, hospitality, healthcare, institutional and industrial
          buildings since {site.founded_year}.
        </p>
        <Link to="/projects" className="ab-go">
          <span>See the work</span>
          <span className="ab-go__ring">
            <Arrow size={16} />
          </span>
        </Link>
      </div>
    </section>
  )
}

/* --- after handover -------------------------------------------------------- */

function After({ pillars }) {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.2 })
  if (!pillars?.length) return null

  return (
    <section className="section ab-after">
      <div className="shell">
        <header className="ab-head">
          <RiseIn as="h2" className="ab-h2" text="The relationship doesn't end at installation." />
          <Reveal delay={100}>
            <p className="ab-lead">
              A lift runs for twenty to twenty-five years. Most of that time is our responsibility too.
            </p>
          </Reveal>
        </header>

        <div ref={ref} className="ab-pillars">
          {pillars.map((p, i) => {
            const Icon = PILLAR_ICONS[p.icon] ?? Shield
            return (
              <article className="ab-pillar" key={p.slug} style={{ '--i': i }}>
                <span className="ab-pillar__icon">
                  <Icon size={24} />
                </span>
                <h3>{p.name}</h3>
                <p>{p.description}</p>
                {p.detail && <p className="ab-pillar__detail">{p.detail}</p>}
              </article>
            )
          })}
        </div>

        <Reveal className="ab-after__foot">
          <Link to="/service" className="link">
            Need service? <Arrow size={14} />
          </Link>
        </Reveal>
      </div>
    </section>
  )
}

/* --- the invitation -------------------------------------------------------- */

function Invitation() {
  const wrap = useRef(null)
  const site = useSite()
  useScrollVar(wrap, { from: 1, to: 0.15 })

  return (
    <div ref={wrap} className="ab-invite-wrap">
      <section className="ab-invite">
        <div className="ab-invite__scene">
          <Img src="/media/frames/lekha-aerial.jpg" alt="" sizes="100vw" />
        </div>
        <div className="ab-invite__copy">
          <p className="ld-label">See it yourself</p>
          <h2 className="ab-invite__title ld-rise">
            <Rise text="See Zion in motion." />
          </h2>
          <p className="ab-invite__lead">
            Come to the factory and watch a lift get loaded to 125% of its rating. It tells you more than any brochure.
          </p>
          <div className="ab-invite__actions">
            <Link to="/contact#visit" className="ab-go ab-go--light">
              <span>Arrange a visit</span>
              <span className="ab-go__ring">
                <Arrow size={16} />
              </span>
            </Link>
            {site.phone && (
              <a href={telHref(site.phone)} className="ab-invite__alt">
                {site.phone}
              </a>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

/* --- page ----------------------------------------------------------------- */

export default function About() {
  const { data: team } = useApi('team/')
  const { data: awards } = useApi('awards/')

  /* Static — see src/data. The Certification, Milestone, ServicePillar and
     Stat models were dropped from the backend (adminpanel migration 0004):
     none of it changes between deploys, so it renders with the first paint
     instead of arriving a round trip later. */
  const stats = statsFor('about')
  const milestones = MILESTONES
  const certifications = CERTIFICATIONS
  const pillars = SERVICE_PILLARS

  useEffect(() => {
    document.title = 'About — Zion Lifts'
  }, [])

  return (
    <div className="ab">
      <Opening stats={stats} />
      <Beginning />
      <Journey milestones={milestones} />
      {COMPARING && <JourneyLanding milestones={milestones} />}
      <Method team={team} />
      <Factory />
      <Quality certifications={certifications} awards={awards} />
      <Installed />
      <After pillars={pillars} />
      <Invitation />
    </div>
  )
}
