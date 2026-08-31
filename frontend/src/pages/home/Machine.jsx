import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { SplitLines } from '@/components/Reveal'
import {
  Arrow,
  CogMark,
  CrosshairMark,
  GaugeMark,
  LayersMark,
  Shield,
  UpDownMark,
  UsersMark,
  WaveMark,
  Wrench,
  LIFT_ICONS,
} from '@/components/icons'
import { useMediaQuery, useReducedMotion, useScrollProgress } from '@/lib/hooks'
import { gsap, initGsap } from '@/lib/gsap'

import EngSchematic from './EngSchematic'

/* ==========================================================================
   04 · THE ZION COLLECTION

   A product explorer: pick a system on the left, the photograph and the
   specification sheet follow. One piece of state — the active index — feeds
   the row, the image, the dot, the icon, the copy, the specs and the link,
   so nothing can drift out of step.

   The frame is sized to hold a single screen and pins while the visitor
   scrolls the nine systems. Everything shown comes from the catalogue API,
   so the specifications here are the same ones the product pages publish.
   ========================================================================== */

const SPEC_ICONS = [UsersMark, GaugeMark, UpDownMark, CogMark]

const PRINCIPLES = [
  [CogMark, 'One engineering platform', 'Built on a single, reliable core technology.'],
  [LayersMark, 'Many system configurations', 'Configured for the way your building works.'],
  [Shield, 'Built for safety, reliability and performance', 'Never compromise on what matters.'],
]

const PROOF = [
  [CogMark, 'One platform', 'Common engineering.', 'Endless applications.'],
  [UsersMark, 'Proven performance', 'Tested in 1,750+ installations', 'across use cases.'],
  [Shield, 'Engineered for safety', 'Multiple safety layers.', 'Always.'],
  [Wrench, 'Service that stays', '24/7 support and', 'long-term reliability.'],
]

/** Held after a manual choice, then autoplay resumes. */
const RESUME_MS = 7000
const ADVANCE_MS = 5200

/** Viewport heights of runway given to each system while pinned. */
const SLOT_SVH = 38

/* Half a slot of extra runway so the last system is held for a moment before
   the frame releases, instead of unpinning the instant it appears. */
const TAIL_SLOTS = 0.5

export function Machine({ lifts = [] }) {
  const [active, setActive] = useState(0)
  const [held, setHeld] = useState(false)
  const [onScreen, setOnScreen] = useState(false)
  const stageRef = useRef(null)
  const iconRef = useRef(null)
  const infoRef = useRef(null)
  const scrollerRef = useRef(null)
  const reduced = useReducedMotion()
  const wide = useMediaQuery('(min-width: 1200px)')

  const items = useMemo(() => lifts.slice(0, 9), [lifts])
  const n = items.length
  const pinned = wide && !reduced

  /* Tracks visibility both ways. `useInView` is not usable here: it latches
     true on first sight, so it could never pause the rotation once the section
     scrolls away, and it attaches its observer in an effect that cannot re-run
     when this component goes from rendering nothing (before the API answers)
     to rendering the section. Keying on `n` is what makes it attach. */
  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting), {
      threshold: 0.25,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [n])

  // Scroll picks the system while the frame is pinned.
  useEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller || !pinned || !n) return
    const { ScrollTrigger } = initGsap()
    const slots = n + TAIL_SLOTS
    const apply = (progress) => {
      const i = Math.min(n - 1, Math.max(0, Math.floor(progress * slots)))
      setActive((prev) => (prev === i ? prev : i))
    }
    const st = ScrollTrigger.create({
      trigger: scroller,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => apply(self.progress),
      onRefresh: (self) => apply(self.progress),
    })
    return () => st.kill()
  }, [pinned, n])

  /* Rotates on its own only where scroll is not already driving it — pinned,
     the two would fight over every frame. */
  useEffect(() => {
    if (reduced || pinned || held || !onScreen || n < 2) return
    const t = setInterval(() => setActive((a) => (a + 1) % n), ADVANCE_MS)
    return () => clearInterval(t)
  }, [reduced, pinned, held, onScreen, n])

  // Release the hold a while after the last manual choice.
  useEffect(() => {
    if (!held) return
    const t = setTimeout(() => setHeld(false), RESUME_MS)
    return () => clearTimeout(t)
  }, [held, active])

  useEffect(() => {
    if (reduced) return
    const tweens = []
    if (infoRef.current) {
      tweens.push(
        gsap.fromTo(
          infoRef.current,
          { autoAlpha: 0, y: 10 },
          { autoAlpha: 1, y: 0, duration: 0.42, ease: 'power2.out', overwrite: true },
        ),
      )
    }
    if (iconRef.current) {
      tweens.push(
        gsap.fromTo(
          iconRef.current,
          { autoAlpha: 0, scale: 0.9 },
          { autoAlpha: 1, scale: 1, duration: 0.3, ease: 'power2.out', overwrite: true },
        ),
      )
    }
    return () => tweens.forEach((t) => t.kill())
  }, [active, reduced])

  if (!n) return null
  const current = items[active]
  const Icon = LIFT_ICONS[current.slug]

  const pick = (i) => {
    const idx = ((i % n) + n) % n
    setActive(idx)
    setHeld(true)
    const scroller = scrollerRef.current
    if (!pinned || !scroller) return
    // keep the pinned scroll position and the shown system in agreement
    const runway = scroller.offsetHeight - window.innerHeight
    if (runway <= 0) return
    const top = scroller.getBoundingClientRect().top + window.scrollY
    const target = top + runway * ((idx + 0.5) / (n + TAIL_SLOTS))
    if (window.__lenis) window.__lenis.scrollTo(target, { duration: 0.8 })
    else window.scrollTo({ top: target, behavior: 'smooth' })
  }

  const onKeyDown = (e) => {
    let next = null
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') next = active + 1
    else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') next = active - 1
    else if (e.key === 'Home') next = 0
    else if (e.key === 'End') next = n - 1
    if (next === null) return
    e.preventDefault()
    const i = ((next % n) + n) % n
    pick(i)
    document.getElementById(`mx-tab-${items[i].slug}`)?.focus()
  }

  const specs = [
    ['Capacity', current.capacity],
    ['Speed', current.speed],
    ['Stops', current.stops],
    ['Drive', current.drive],
  ]

  return (
    <section className="section mx" aria-labelledby="mx-title">
      {/* --- statement ------------------------------------------------- */}
      <div className="shell zc__intro">
        <div className="zc__intro-copy">
          <Reveal variant="fade">
            <p className="zc__eyebrow">The Zion collection</p>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="zc__title" id="mx-title">
              One system.
              <br />
              <em>Many possibilities.</em>
            </h2>
          </Reveal>
          <Reveal delay={110}>
            <span className="zc__rule" aria-hidden="true" />
          </Reveal>
          <Reveal delay={150}>
            <p className="zc__lead">
              The same engineering underneath — a gearless machine, a rail-guided car, a controller
              that shapes every start and stop. What changes is the shell around it, and what the
              building asks of it.
            </p>
          </Reveal>
          <Reveal delay={200}>
            <Link to="/lifts" className="zc__link">
              Compare every system <Arrow size={14} />
            </Link>
          </Reveal>
        </div>

        <div className="zc__intro-media">
          <div className="zc__intro-shot">
            <Img
              src="/media/frames/chilkuru-atrium.jpg"
              alt="A glazed capsule lift rising through the atrium of a private residence in Hyderabad"
              sizes="(min-width: 1100px) 42vw, 100vw"
            />
            <div className="zc__intro-fade" aria-hidden="true" />
          </div>

          <ul className="zc__principles">
            {PRINCIPLES.map(([Icon, title, body]) => (
              <li key={title}>
                <Icon size={24} className="zc__principle-icon" />
                <p className="zc__principle-title">{title}</p>
                <p className="zc__principle-body">{body}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* --- the nine systems ------------------------------------------ */}
      <div
        className={`mx__scroller ${pinned ? 'is-pinned' : ''}`}
        ref={scrollerRef}
        style={pinned ? { '--mx-runway': `${(n + TAIL_SLOTS) * SLOT_SVH}svh` } : undefined}
      >
        <div className="mx__pin">
          <div className="shell">
            <div className="mx__frame">
              {/* --- selector ------------------------------------------- */}
              <ul
                className="mx__nav"
                role="tablist"
                aria-orientation="vertical"
                aria-label="Lift systems"
                onKeyDown={onKeyDown}
              >
                {items.map((lift, i) => {
                  const RowIcon = LIFT_ICONS[lift.slug]
                  const on = i === active
                  return (
                    <li key={lift.slug}>
                      <button
                        type="button"
                        id={`mx-tab-${lift.slug}`}
                        role="tab"
                        aria-selected={on}
                        aria-controls="mx-panel"
                        aria-label={`Select ${lift.name}`}
                        tabIndex={on ? 0 : -1}
                        className={`mx__tab ${on ? 'is-on' : ''}`}
                        onClick={() => pick(i)}
                      >
                        {RowIcon && <RowIcon size={26} className="mx__tab-icon" />}
                        <span className="mx__tab-name">{lift.name}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>

              {/* --- photograph ----------------------------------------- */}
              <div className="mx__stage" ref={stageRef}>
                {items.map((lift, i) => (
                  <div
                    key={lift.slug}
                    className={`mx__shot ${i === active ? 'is-on' : ''}`}
                    aria-hidden={i !== active}
                  >
                    <Img
                      src={lift.hero_image_url}
                      alt={i === active ? `${lift.name} by Zion Lifts` : ''}
                      sizes="(min-width: 1200px) 38vw, 100vw"
                      priority={i === 0}
                    />
                  </div>
                ))}
                <div className="mx__stage-foot" aria-hidden="true" />

                <div className="mx__dots" role="tablist" aria-label="Lift systems">
                  {items.map((lift, i) => (
                    <button
                      key={lift.slug}
                      type="button"
                      role="tab"
                      aria-selected={i === active}
                      aria-label={`Go to ${lift.name}`}
                      className={`mx__dot ${i === active ? 'is-on' : ''}`}
                      onClick={() => pick(i)}
                    />
                  ))}
                </div>
              </div>

              {/* --- specification -------------------------------------- */}
              <div className="mx__panel" id="mx-panel" role="tabpanel" aria-live="polite">
                <span className="mx__panel-icon" ref={iconRef}>
                  {Icon && <Icon size={38} />}
                </span>

                <div className="mx__info" ref={infoRef}>
                  <h3 className="mx__name">{current.name}</h3>
                  <p className="mx__summary">{current.summary}</p>

                  <dl className="mx__specs">
                    {specs
                      .filter(([, v]) => v)
                      .map(([label, value], i) => {
                        const SpecIcon = SPEC_ICONS[i]
                        return (
                          <div className="mx__spec" key={label}>
                            <dt>
                              <SpecIcon size={22} className="mx__spec-icon" />
                              {label}
                            </dt>
                            <dd>{value}</dd>
                          </div>
                        )
                      })}
                  </dl>
                </div>

                <Link to={`/lifts/${current.slug}`} className="mx__cta">
                  <span>Explore {current.short_name || current.name}</span>
                  <Arrow size={16} />
                </Link>
              </div>
            </div>
          </div>
        </div>
        <div className="mx__runway" aria-hidden="true" />
      </div>

      {/* --- proof rail ------------------------------------------------- */}
      <div className="shell zc__proof-wrap">
        <ul className="zc__proof">
          {PROOF.map(([Icon, title, l1, l2]) => (
            <li key={title}>
              <Icon size={22} className="zc__proof-icon" />
              <div>
                <p className="zc__proof-title">{title}</p>
                <p className="zc__proof-body">
                  {l1}
                  <br />
                  {l2}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

/* ==========================================================================
   05 · THE ENGINEERING

   Four measurable qualities rather than four marketing cards: a two-column
   editorial header with a faint shaft schematic in the negative space beside
   it, then one continuous panel of four plates divided by hairlines.
   ========================================================================== */

const ENGINEERING = [
  {
    word: 'Precision',
    icon: CrosshairMark,
    line: 'Floor levelling within three millimetres, loaded or empty.',
    body: 'A closed-loop drive reads the car position continuously and corrects it before you notice there was anything to correct.',
    src: '/media/sourced/macro-bearing.jpg',
    alt: 'A machined bearing surface held against a measuring gauge',
  },
  {
    word: 'Silence',
    icon: WaveMark,
    line: 'No gearbox, so no gearbox noise.',
    body: 'A permanent-magnet machine drives the sheave directly. Under 52 dB(A) in the car — quiet enough to sit beside a bedroom.',
    src: '/media/frames/kashi-drive.jpg',
    alt: 'The gearless permanent-magnet drive at the head of a Zion shaft',
  },
  {
    word: 'Safety',
    icon: Shield,
    line: 'Steel wedges that need no electricity to work.',
    body: 'The governor and safety gear are mechanical. They function during a power cut because they never needed power in the first place.',
    src: '/media/frames/kashi-machine.jpg',
    alt: 'The governor and safety gear mounted on the car frame',
  },
  {
    word: 'Performance',
    icon: GaugeMark,
    line: 'Every start and stop is a curve, not a step.',
    body: 'Acceleration is shaped by the drive rather than the contactor, which is the whole difference between a ride and a jolt.',
    src: '/media/sourced/macro-circuit.jpg',
    alt: 'The drive controller board that shapes the acceleration curve',
  },
]

export function Engineering() {
  return (
    <section className="section eng" aria-labelledby="eng-title">
      <div className="shell eng__head">
        <EngSchematic />

        <div className="eng__intro">
          <Reveal variant="fade">
            <p className="eng__eyebrow">The engineering</p>
          </Reveal>
          <SplitLines
            as="h2"
            className="eng__title"
            lines={[
              'Four things',
              <>
                a lift is judged on<span className="eng__dot">.</span>
              </>,
            ]}
          />
          <span className="sr-only" id="eng-title">
            Four things a lift is judged on
          </span>
        </div>

        <Reveal variant="fade" delay={220} className="eng__lead-wrap">
          <p className="eng__lead">
            A lift is a system of little details working in perfect agreement. These four decide how
            it feels, every single day.
          </p>
        </Reveal>
      </div>

      <div className="shell">
        {/* horizontally scrollable below 768px, so it has to be focusable */}
        <ol className="eng__grid" tabIndex={0} aria-label="The four engineering qualities">
          {ENGINEERING.map((e, i) => {
            const Icon = e.icon
            return (
              <Reveal as="li" key={e.word} className="eng__card" variant="up" delay={i * 100}>
                <div className="eng__media">
                  <Img
                    src={e.src}
                    alt={e.alt}
                    sizes="(min-width: 1200px) 23vw, (min-width: 768px) 46vw, 84vw"
                    parallax={12}
                  />
                  <span className="eng__media-veil" aria-hidden="true" />
                  <span className="eng__num" aria-hidden="true">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                </div>

                <div className="eng__copy">
                  <Icon size={30} className="eng__icon" />
                  <p className="eng__label">{e.word}</p>
                  <h3 className="eng__line">{e.line}</h3>
                  <p className="eng__body">{e.body}</p>
                  <span className="eng__tick" aria-hidden="true" />
                </div>
              </Reveal>
            )
          })}
        </ol>
      </div>
    </section>
  )
}

/* ==========================================================================
   06 · THE CABIN
   The slow chapter. One frame, held, while the camera drifts.
   ========================================================================== */

const CABIN_LAYERS = [
  { src: '/media/frames/lacheta-ceiling.jpg', label: 'Ceiling & lighting' },
  { src: '/media/interiors/interior-01.jpg', label: 'Walls & finish' },
  { src: '/media/frames/kashi-floor.jpg', label: 'Flooring' },
  { src: '/media/frames/lacheta-cop.jpg', label: 'Control panel' },
  { src: '/media/frames/lekha-ceiling.jpg', label: 'Doors & entrance' },
]

export function Cabin() {
  const [ref, progress] = useScrollProgress()
  const active = Math.min(
    CABIN_LAYERS.length - 1,
    Math.floor(progress * CABIN_LAYERS.length * 1.05),
  )

  return (
    <section ref={ref} className="section section--flush cabin" aria-labelledby="cabin-title">
      <div className="cabin__pin">
        <div className="cabin__stage">
          {CABIN_LAYERS.map((l, i) => (
            <div key={l.src} className={`cabin__layer ${i === active ? 'is-on' : ''}`}>
              <Img src={l.src} alt="" sizes="100vw" />
            </div>
          ))}
          <div className="cabin__veil" aria-hidden="true" />

          <div className="shell cabin__content">
            <p className="eyebrow">The cabin</p>
            <h2 className="h2 cabin__title" id="cabin-title">
              Designed around
              <br />
              your architecture.
            </h2>
            <p className="lead cabin__lead">
              Wall material, flooring, ceiling, lighting, handrail and control panel are specified
              separately — with the interior, not from a fixed catalogue.
            </p>
            <ol className="cabin__rail">
              {CABIN_LAYERS.map((l, i) => (
                <li key={l.label} className={i === active ? 'is-on' : ''}>
                  <span className="cabin__rail-n">{String(i + 1).padStart(2, '0')}</span>
                  <span>{l.label}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
      <div className="cabin__runway" aria-hidden="true" />
    </section>
  )
}

/* ==========================================================================
   07 · BUILD YOUR ZION — the configurator, and the lead-gen engine
   ========================================================================== */

const GROUPS = [
  { key: 'material', label: 'Wall material' },
  { key: 'floor', label: 'Flooring' },
  { key: 'light', label: 'Lighting' },
  { key: 'door', label: 'Door' },
  { key: 'control', label: 'Control panel' },
]

/** Preview plate chosen by wall material — the finish that changes the car most. */
const PREVIEW = {
  'brushed-steel': '/media/frames/owaisi-cabin.jpg',
  'antique-brass': '/media/frames/lacheta-lobby.jpg',
  'rose-gold': '/media/interiors/interior-03.jpg',
  walnut: '/media/frames/chath-cabin.jpg',
  'stone-grey': '/media/interiors/interior-10.jpg',
  obsidian: '/media/interiors/interior-04.jpg',
}

export function Configurator({ finishes = [], compact = false, liftSlug = '' }) {
  const byCategory = GROUPS.map((g) => ({
    ...g,
    options: finishes.filter((f) => f.category === g.key),
  })).filter((g) => g.options.length)

  // Finishes arrive after the first render, so the selection cannot be seeded
  // in useState — each group falls back to its first option until picked.
  const [choice, setChoice] = useState({})
  const [tab, setTab] = useState('material')

  if (!byCategory.length) return null

  const chosen = (key) => {
    const group = byCategory.find((g) => g.key === key)
    if (!group) return undefined
    return group.options.find((o) => o.slug === choice[key]) ?? group.options[0]
  }

  const wall = chosen('material')
  const preview = PREVIEW[wall?.slug] ?? PREVIEW['brushed-steel']
  const activeGroup = byCategory.find((g) => g.key === tab) ?? byCategory[0]

  const summary = byCategory.map((g) => `${g.label}: ${chosen(g.key)?.name ?? '—'}`).join(' · ')

  const enquiryHref = `/contact?${new URLSearchParams({
    config: byCategory.map((g) => `${g.key}=${chosen(g.key)?.slug ?? ''}`).join(','),
    ...(liftSlug ? { lift: liftSlug } : {}),
  })}`

  return (
    <section
      className={`section configurator ${compact ? 'configurator--compact' : ''}`}
      id="configure"
    >
      <div className="shell">
        {!compact && (
          <div className="section-head section-head--split">
            <div>
              <Reveal variant="fade">
                <p className="eyebrow">Build your Zion</p>
              </Reveal>
              <Reveal delay={60}>
                <h2 className="h2" style={{ marginTop: '1.1rem' }}>
                  Specify the car,
                  <br />
                  then send it to us.
                </h2>
              </Reveal>
            </div>
            <Reveal delay={130}>
              <p className="body">
                Change a finish and the car changes with it. Whatever you land on travels through to
                the enquiry form, so nobody has to describe it twice.
              </p>
            </Reveal>
          </div>
        )}

        <div className="cfg">
          <div className="cfg__preview">
            <Img
              src={preview}
              alt={`Cabin in ${wall?.name ?? 'the selected finish'}`}
              sizes="(min-width: 900px) 52vw, 100vw"
            />
            <div
              className="cfg__wash"
              style={{
                background: `linear-gradient(150deg, ${wall?.swatch_hex ?? '#B9BEC2'}22, transparent 62%)`,
              }}
              aria-hidden="true"
            />
            <div className="cfg__badge">
              <span className="mono">Your configuration</span>
              <span className="cfg__badge-name">{wall?.name}</span>
            </div>
          </div>

          <div className="cfg__panel">
            <div className="cfg__tabs" role="tablist" aria-label="Finish groups">
              {byCategory.map((g) => (
                <button
                  key={g.key}
                  type="button"
                  role="tab"
                  aria-selected={tab === g.key}
                  className={`cfg__tab ${tab === g.key ? 'is-on' : ''}`}
                  onClick={() => setTab(g.key)}
                >
                  {g.label}
                  <span className="cfg__tab-val">{chosen(g.key)?.name}</span>
                </button>
              ))}
            </div>

            <div className="cfg__options" role="tabpanel">
              {activeGroup.options.map((o) => {
                const on = chosen(activeGroup.key)?.slug === o.slug
                return (
                  <button
                    key={o.slug}
                    type="button"
                    className={`cfg__swatch ${on ? 'is-on' : ''}`}
                    onClick={() => setChoice((c) => ({ ...c, [activeGroup.key]: o.slug }))}
                    aria-pressed={on}
                  >
                    <span
                      className="cfg__chip"
                      style={{
                        background: `linear-gradient(135deg, ${o.swatch_hex}, ${o.swatch_hex_2 || o.swatch_hex})`,
                      }}
                      aria-hidden="true"
                    />
                    <span className="cfg__swatch-body">
                      <span className="cfg__swatch-name">
                        {o.name}
                        {o.tier !== 'standard' && <em className="cfg__tier">{o.tier}</em>}
                      </span>
                      {o.description && <span className="cfg__swatch-desc">{o.description}</span>}
                    </span>
                  </button>
                )
              })}
            </div>

            <div className="cfg__foot">
              <p className="cfg__summary">{summary}</p>
              <div className="cfg__actions">
                <Link to={enquiryHref} className="btn btn--accent btn--sm">
                  Request this design <Arrow size={14} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
