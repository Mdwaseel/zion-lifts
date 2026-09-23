import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal from '@/components/Reveal'
import { Accordion } from '@/components/sections'
import { Arrow, ArrowDown, GaugeMark, UpDownMark, UsersMark } from '@/components/icons'
import { LIFT_ICONS } from '@/components/lift-marks'
import { PLACES } from '@/components/place-marks'
import { faqCategory } from '@/data/faqs'
import { gsap } from '@/lib/gsap'
import { useApi, useReducedMotion } from '@/lib/hooks'

import { ProjectsReel } from './home/Proof'
import CabinStudio from './lift/CabinStudio'
import { Rise, RiseIn, clamp01, useScrollVar, whenIntroDone } from './lift/shared'
import './lifts.css'

/* ==========================================================================
   /lifts — the collection
   The nine systems stand on a curved arc that the scroll turns: the lift that
   faces you plays its film and its account stands beside it. Below it, the
   figures are nine shafts on one scale.
   ========================================================================== */

const pad = (n) => String(n).padStart(2, '0')

/* --- the opening ---------------------------------------------------------- */

function Opening({ count }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(false)

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  // leaving, the room draws back into a frame, as it does on a lift's own page
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
    <header ref={ref} className={`lc-hero ${shown ? 'is-in' : ''}`}>
      <div className="lc-hero__scene">
        <Img src="/media/interiors/interior-05.jpg" alt="" priority sizes="100vw" />
      </div>
      <div className="lc-hero__grade" aria-hidden="true" />

      <div className="lc-hero__copy">
        <p className="ld-label lc-hero__label">The range</p>
        <h1 className="lc-hero__title">
          <Rise text="Nine ways to move vertically." />
        </h1>
        <p className="lc-hero__lead">
          One engineering approach underneath — a gearless machine, a rail-guided cabin and a controller that shapes
          every start and stop. Nine shells around it, for nine kinds of building.
        </p>
      </div>

      <div className="lc-hero__foot">
        <p>
          <strong>{pad(count || 9)}</strong> systems
        </p>
        <a href="#index">The index</a>
        <a href="#compare">Side by side</a>
        <a href="#index" className="lc-hero__cue" aria-label="Scroll to the index">
          <ArrowDown size={16} />
        </a>
      </div>
    </header>
  )
}

/* --- the collection: a carousel you scroll through ------------------------ */

const STEP = 38 // degrees of arc between one lift and the next

/** The lifts stand on a curved arc, like cars round a shaft. The section holds
    the screen and the scroll turns the arc: whichever lift faces you plays its
    film, and its account stands beside it. One number — how far round the arc
    has turned — places every plate, picks the account and moves the counter. */
function Index({ lifts }) {
  const sec = useRef(null)
  const ring = useRef(null)
  const fill = useRef(null)
  const reduced = useReducedMotion()
  const [active, setActive] = useState(0)

  const list = lifts
  const n = list.length
  const held = !reduced && n > 1

  useEffect(() => {
    if (!held) return undefined
    const el = sec.current
    const rg = ring.current
    const plates = [...rg.querySelectorAll('.lc-car')]
    let radius = 0
    let beside = false
    const measure = () => {
      // beside the account, the cars that have gone by leave quickly so they never cross the type
      beside = window.matchMedia('(min-width: 900px)').matches
      radius = (plates[0]?.offsetWidth ?? 300) * 1.72
      rg.style.transform = `translateZ(${-radius}px)`
    }
    measure()
    window.addEventListener('resize', measure)

    let cur = 0
    let last = -1
    let shown = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < 0 || r.top > vh) return
      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      cur += (p * (n - 1) - cur) * 0.1
      if (Math.abs(cur - last) > 0.0008) {
        last = cur
        plates.forEach((pl, i) => {
          const d = i - cur
          const away = Math.abs(d)
          if (away > 3.1) {
            pl.style.visibility = 'hidden'
            return
          }
          pl.style.visibility = 'visible'
          pl.style.transform = `rotateY(${(d * STEP).toFixed(2)}deg) translateZ(${radius.toFixed(0)}px)`
          const fade = beside && d < 0 ? Math.max(0, away - 0.3) / 0.85 : Math.max(0, away - 1.4) / 1.7
          pl.style.opacity = Math.max(0, 1 - fade).toFixed(3)
          pl.style.setProperty('--away', Math.min(1, away).toFixed(3))
        })
        if (fill.current) fill.current.style.transform = `scaleX(${(n > 1 ? cur / (n - 1) : 1).toFixed(4)})`
      }
      const i = Math.max(0, Math.min(n - 1, Math.round(cur)))
      if (i !== shown) {
        shown = i
        setActive(i)
      }
    }
    gsap.ticker.add(tick)
    return () => {
      gsap.ticker.remove(tick)
      window.removeEventListener('resize', measure)
    }
  }, [held, n, list])

  const go = (i) => {
    const to = Math.max(0, Math.min(n - 1, i))
    if (!held) {
      setActive(to)
      return
    }
    const el = sec.current
    const top = el.getBoundingClientRect().top + window.scrollY
    const y = top + (n > 1 ? to / (n - 1) : 0) * (el.offsetHeight - window.innerHeight)
    if (window.__lenis) window.__lenis.scrollTo(y, { duration: 1 })
    else window.scrollTo({ top: y, behavior: 'smooth' })
  }

  const at = Math.min(active, Math.max(0, n - 1))
  const lift = list[at]
  const Mark = lift ? LIFT_ICONS[lift.slug] : null

  return (
    <section
      ref={sec}
      className={`lc-index ${held ? 'is-held' : 'is-free'}`}
      id="index"
      style={held ? { height: `calc(100svh + ${(n - 1) * 46}svh)` } : undefined}
    >
      <div className="lc-index__stage">
        <div className="lc-index__glow" aria-hidden="true" />

        <header className="lc-index__top">
          <h2 className="lc-index__title">
            Every lift Zion <em>builds.</em>
          </h2>
        </header>

        {lift && (
          <div className="lc-index__body">
            {/* the account of the lift facing you */}
            <div className="lc-about" key={lift.slug} aria-live="polite">
              <p className="lc-about__n">
                {Mark && <Mark size={26} />}
                <span>
                  {pad(lifts.indexOf(lift) + 1)} — {lift.eyebrow}
                </span>
              </p>
              <h3 className="lc-about__name">{lift.name}</h3>
              <p className="lc-about__line">{lift.tagline}</p>
              <dl className="lc-about__specs">
                {[
                  ['Capacity', lift.capacity, UsersMark],
                  ['Speed', lift.speed, GaugeMark],
                  ['Stops', lift.stops, UpDownMark],
                ].map(([k, v, Icon]) => (
                  <div key={k}>
                    <Icon size={17} />
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
              <Link to={`/lifts/${lift.slug}`} className="lc-about__go">
                <span>View the lift</span>
                <span className="lc-about__ring">
                  <Arrow size={17} />
                </span>
              </Link>
            </div>

            <div className="lc-arc">
              <ol ref={ring} className="lc-arc__ring">
                {list.map((l, i) => (
                  <li key={l.slug} className={`lc-car ${i === at ? 'is-on' : ''}`} style={{ '--d': i - at }}>
                    <button type="button" onClick={() => go(i)} tabIndex={i === at ? -1 : 0} aria-label={`Show ${l.name}`}>
                      <Img src={`/media/lifts/${l.slug}.jpg`} alt="" sizes="(min-width: 900px) 26vw, 64vw" priority />
                      {i === at && !reduced && (
                        <video src={`/media/lifts/${l.slug}.mp4`} autoPlay muted loop playsInline aria-hidden="true" tabIndex={-1} />
                      )}
                      <span className="lc-car__name">{l.short_name}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </div>

            <div className="lc-index__foot">
              <span className="lc-index__now">{pad(at + 1)}</span>
              <span className="lc-index__line" aria-hidden="true">
                <span ref={fill} />
              </span>
              <span>{pad(n)}</span>
              <button type="button" onClick={() => go(at - 1)} disabled={at === 0} aria-label="Previous lift">
                <Arrow size={16} />
              </button>
              <button type="button" onClick={() => go(at + 1)} disabled={at === n - 1} aria-label="Next lift">
                <Arrow size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

/* --- side by side: nine shafts -------------------------------------------- */

/** the two ends of a range written as "0.3 – 1.0 m/s" or "2,000 – 2,700 kg …" */
function range(text) {
  const nums = (String(text ?? '').split('(')[0].match(/[\d.,]+/g) ?? [])
    .map((t) => parseFloat(t.replace(/,/g, '')))
    .filter((v) => !Number.isNaN(v))
  if (!nums.length) return null
  return [Math.min(...nums.slice(0, 2)), Math.max(...nums.slice(0, 2))]
}

const METRICS = [
  { key: 'speed', label: 'Speed', unit: 'm/s', ticks: [0, 0.5, 1, 1.5, 2, 2.5], scale: (v) => v / 2.5 },
  {
    key: 'capacity',
    label: 'Capacity',
    unit: 'kg',
    ticks: [0, 250, 1000, 2000, 3500, 5000],
    // the range runs from a dumbwaiter to a goods lift, so the scale is a root one
    scale: (v) => Math.sqrt(v / 5000),
  },
  { key: 'stops', label: 'Stops', unit: 'stops', ticks: [0, 5, 10, 15, 20], scale: (v) => v / 20 },
]

function Compare({ lifts }) {
  const ref = useRef(null)
  const [metric, setMetric] = useState(0)
  const [over, setOver] = useState(-1)
  const [seen, setSeen] = useState(false)
  const m = METRICS[metric]

  useEffect(() => {
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true)
          io.disconnect()
        }
      },
      { threshold: 0.3 },
    )
    io.observe(ref.current)
    return () => io.disconnect()
  }, [])

  const focus = over >= 0 ? lifts[over] : null

  return (
    <section className="section on-paper lc-compare" id="compare">
      <div className="shell">
        <header className="lc-compare__head">
          <RiseIn as="h2" className="lc-h2" text="Side by side." />
          <Reveal delay={100}>
            <p className="lc-index__lead">
              Nine shafts, one scale. Choose what to measure and each car rides to where that lift sits.
            </p>
          </Reveal>
        </header>

        <Reveal className="lc-measure" role="tablist" aria-label="What to compare">
          {METRICS.map((x, i) => (
            <button
              key={x.key}
              type="button"
              role="tab"
              aria-selected={i === metric}
              className={i === metric ? 'is-on' : ''}
              onClick={() => setMetric(i)}
            >
              {x.label}
            </button>
          ))}
        </Reveal>

        <div ref={ref} className={`lc-shafts ${seen ? 'is-in' : ''}`} onPointerLeave={() => setOver(-1)}>
          <ol className="lc-shafts__scale" aria-hidden="true">
            {m.ticks.map((t) => (
              <li key={`${m.key}-${t}`} style={{ '--at': m.scale(t) }}>
                <span>{t.toLocaleString('en-IN')}</span>
              </li>
            ))}
            <li className="lc-shafts__unit">{m.unit}</li>
          </ol>

          <div className="lc-shafts__row">
            {lifts.map((l, i) => {
              const Mark = LIFT_ICONS[l.slug]
              const r = range(l[m.key]) ?? [0, 0]
              const lo = clamp01(m.scale(r[0]))
              const hi = clamp01(m.scale(r[1]))
              return (
                <Link
                  key={l.slug}
                  to={`/lifts/${l.slug}`}
                  className={`lc-shaft ${over === i ? 'is-over' : ''}`}
                  style={{ '--lo': lo, '--hi': Math.max(hi, lo + 0.035), '--i': i }}
                  onPointerEnter={() => setOver(i)}
                  onFocus={() => setOver(i)}
                  onBlur={() => setOver(-1)}
                  aria-label={`${l.name}: ${m.label.toLowerCase()} ${l[m.key]}`}
                >
                  <span className="lc-shaft__well" aria-hidden="true">
                    <span className="lc-shaft__rope" />
                    <span className="lc-shaft__car">
                      <em>{r[1].toLocaleString('en-IN')}</em>
                      <em>{r[0].toLocaleString('en-IN')}</em>
                    </span>
                  </span>
                  <span className="lc-shaft__mark">{Mark && <Mark size={24} />}</span>
                  <span className="lc-shaft__name">{l.short_name}</span>
                </Link>
              )
            })}
          </div>
        </div>

        {/* what the chart cannot draw: the drive, and whether it needs a machine room */}
        <div className={`lc-detail ${focus ? 'is-on' : ''}`} aria-live="polite">
          {focus ? (
            <>
              <strong>{focus.name}</strong>
              <span>
                <em>Drive</em>
                {focus.drive}
              </span>
              <span>
                <em>Machine room</em>
                {focus.machine_room}
              </span>
              <span>
                <em>{m.label}</em>
                {focus[m.key]}
              </span>
            </>
          ) : (
            <span className="lc-detail__hint">Point at a shaft for its drive and machine room — or press it to open that lift.</span>
          )}
        </div>

        <table className="sr-only">
          <caption>Comparison of Zion lift systems</caption>
          <thead>
            <tr>
              <th scope="col">System</th>
              <th scope="col">Drive</th>
              <th scope="col">Speed</th>
              <th scope="col">Capacity</th>
              <th scope="col">Stops</th>
              <th scope="col">Machine room</th>
            </tr>
          </thead>
          <tbody>
            {lifts.map((l) => (
              <tr key={l.slug}>
                <th scope="row">{l.name}</th>
                <td>{l.drive}</td>
                <td>{l.speed}</td>
                <td>{l.capacity}</td>
                <td>{l.stops}</td>
                <td>{l.machine_room}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

/* --- where they go -------------------------------------------------------- */

function Places({ applications, lifts }) {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.15 })
  const places = (applications ?? []).filter((a) => PLACES[a.slug])
  if (!places.length) return null

  return (
    <section className="section on-stone lc-places">
      <div className="shell">
        <header className="lc-compare__head">
          <RiseIn as="h2" className="lc-h2" text="Where these lifts go." />
          <Reveal delay={100}>
            <p className="lc-index__lead">
              The building decides most of the specification before anyone opens a catalogue.
            </p>
          </Reveal>
        </header>

        <div ref={ref} className="lc-places__grid">
          {places.map((a, i) => {
            const { Icon, src } = PLACES[a.slug]
            const suited = lifts.filter((l) => (l.applications ?? []).some((x) => x.slug === a.slug))
            return (
              <article className="lc-place" key={a.slug} style={{ '--i': i % 4 }}>
                <div className="lc-place__in">
                  <div className="lc-place__media">
                    <Img src={src} alt="" sizes="(min-width: 1000px) 24vw, (min-width: 640px) 46vw, 92vw" />
                  </div>
                  <span className="lc-place__icon">
                    <Icon size={26} />
                  </span>
                  <h3>{a.name}</h3>
                  <p>{a.description}</p>
                  <ul>
                    {suited.map((l) => (
                      <li key={l.slug}>
                        <Link to={`/lifts/${l.slug}`}>{l.short_name}</Link>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* --- page ----------------------------------------------------------------- */

export default function Lifts() {
  const { data: lifts } = useApi('lifts/')
  const { data: applications } = useApi('applications/')
  const { data: projects } = useApi('projects/')
  const { data: finishes } = useApi('finishes/')

  useEffect(() => {
    document.title = 'Lift systems — Zion Lifts'
  }, [])

  const all = lifts ?? []
  const chooseFaq = faqCategory('choosing-a-lift')

  return (
    <div className="lc">
      <Opening count={all.length} />
      {all.length > 0 && <Index lifts={all} />}
      {all.length > 0 && <Compare lifts={all} />}
      <Places applications={applications} lifts={all} />
      <CabinStudio finishes={finishes} />
      {projects?.length > 0 && (
        <ProjectsReel
          projects={projects}
          eyebrow="Installed"
          title={
            <>
              These systems,
              <br />
              in buildings.
            </>
          }
          lead="A few of the places they are running today."
        />
      )}

      {chooseFaq && (
        <section className="section on-paper lc-faq">
          <div className="shell shell--text">
            <header className="lc-compare__head lc-faq__head">
              <RiseIn as="h2" className="lc-h2" text="The questions people actually ask." />
              <Link to="/faq" className="link">
                Every question <Arrow size={14} />
              </Link>
            </header>
            <Accordion items={chooseFaq.questions} defaultOpen={0} />
          </div>
        </section>
      )}
    </div>
  )
}
