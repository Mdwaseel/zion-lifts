import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoLoop } from '@/components/Media'
import Reveal, { SplitLines } from '@/components/Reveal'
import { CeilingMark, DoorMark, FloorMark, PanelMark, WallMark } from '@/components/cabin-marks'
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
} from '@/components/icons'
import { LIFT_ICONS } from '@/components/lift-marks'
import { useMediaQuery, useReducedMotion } from '@/lib/hooks'
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

/* Each system has a four-second loop of its cabin, served from public/media/lifts
   and keyed by the API slug. A system without a loop falls back to its still.
   Only the active shot mounts a <video> — nine decoding at once would not be
   worth it for eight you cannot see — the others hold on the loop's first frame. */
const LOOPS = {
  'home-elevator': '/media/lifts/home-elevator',
  'capsule-elevator': '/media/lifts/capsule-elevator',
  'mrl-traction': '/media/lifts/mrl-traction',
  'hydraulic-elevator': '/media/lifts/hydraulic-elevator',
  'passenger-elevator': '/media/lifts/passenger-elevator',
  'hospital-elevator': '/media/lifts/hospital-elevator',
  'goods-elevator': '/media/lifts/goods-elevator',
  dumbwaiter: '/media/lifts/dumbwaiter',
  'car-stacker': '/media/lifts/car-stacker',
}

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
              The same engineering underneath — a gearless machine, a rail-guided cabin, a
              controller that shapes every start and stop. What changes is the shell around it, and
              what the building asks of it.
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
                {items.map((lift, i) => {
                  const loop = LOOPS[lift.slug]
                  const on = i === active
                  return (
                    <div
                      key={lift.slug}
                      className={`mx__shot ${on ? 'is-on' : ''}`}
                      aria-hidden={!on}
                    >
                      {loop && on ? (
                        <VideoLoop src={`${loop}.mp4`} poster={`${loop}.jpg`} />
                      ) : (
                        <Img
                          src={loop ? `${loop}.jpg` : lift.hero_image_url}
                          alt={on ? `${lift.name} by Zion Lifts` : ''}
                          sizes="(min-width: 1200px) 38vw, 100vw"
                          priority={i === 0}
                        />
                      )}
                    </div>
                  )
                })}
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
    body: 'A closed-loop drive reads the lift position continuously and corrects it before you notice there was anything to correct.',
    src: '/media/engineering/eng-precision.jpg',
    alt: 'A lift car sill levelled flush with the landing threshold',
  },
  {
    word: 'Silence',
    icon: WaveMark,
    line: 'No gearbox, so no gearbox noise.',
    body: 'A permanent-magnet machine drives the sheave directly. Under 52 dB(A) in the lift — quiet enough to sit beside a bedroom.',
    src: '/media/engineering/eng-silence.jpg',
    alt: 'The gearless permanent-magnet machine and traction sheave at the head of the shaft',
  },
  {
    word: 'Safety',
    icon: Shield,
    line: 'Steel wedges that need no electricity to work.',
    body: 'The governor and safety gear are mechanical. They function during a power cut because they never needed power in the first place.',
    src: '/media/engineering/eng-safety.jpg',
    alt: 'Safety gear wedge blocks clamped to the guide rails on the lift frame',
  },
  {
    word: 'Performance',
    icon: GaugeMark,
    line: 'Every start and stop is a curve, not a step.',
    body: 'Acceleration is shaped by the drive rather than the contactor, which is the whole difference between a ride and a jolt.',
    src: '/media/engineering/eng-performance.jpg',
    alt: 'The drive sheave and governor assembly that shapes the acceleration curve',
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
   07 · BUILD YOUR ZION — the configurator, and the lead-gen engine

   One immersive frame rather than a panel of controls: the cabin stands in the
   middle at full height, the copy sits to its left, the specification label
   floats over its right edge and the controls run along the bottom. Every
   value on screen is read from the finishes API through a single `choice`
   object, so the label, the render and the enquiry link cannot disagree.
   ========================================================================== */

/* Order and wording follow the specification label, not the API. `label` is the
   short key used down the right-hand list; `nav` is the two-line control label. */
const GROUPS = [
  {
    key: 'light',
    label: 'Lighting',
    nav: ['Ceiling &', 'lighting'],
    icon: CeilingMark,
    pos: '50% 18%',
  },
  { key: 'material', label: 'Wall', nav: ['Walls &', 'finish'], icon: WallMark, pos: '50% 45%' },
  { key: 'floor', label: 'Floor', nav: ['Flooring'], icon: FloorMark, pos: '50% 82%' },
  { key: 'control', label: 'Control', nav: ['Control', 'panel'], icon: PanelMark, pos: '50% 45%' },
  { key: 'door', label: 'Door', nav: ['Doors &', 'entrance'], icon: DoorMark, pos: '50% 50%' },
]

/* One cabin render per selectable finish, so picking anything — a ceiling, a
   floor, a panel — shows that finish rather than only the wall changing the
   view. The path is derived from the choice; see the `finishes` step in
   assets-src/build_images.py for how the files are named. */
const plateFor = (category, slug) =>
  NO_RENDER[`${category}-${slug}`] ?? `/media/finishes/${category}-${slug}.jpg`

/** Finishes with no render of their own yet; the nearest plate stands in. */
const NO_RENDER = {
  'material-obsidian': '/media/interiors/interior-05.jpg',
}

/** Opening configuration. Everything else falls back to its first option. */
const DEFAULTS = { material: 'antique-brass' }

export function Configurator({ finishes = [], compact = false, liftSlug = '' }) {
  const byCategory = GROUPS.map((g) => ({
    ...g,
    options: finishes.filter((f) => f.category === g.key),
  })).filter((g) => g.options.length)

  // Finishes arrive after the first render, so the selection cannot be seeded
  // in useState — each group falls back to DEFAULTS, then to its first option.
  const [choice, setChoice] = useState({})
  const [tab, setTab] = useState(GROUPS[0].key)
  const [ink, setInk] = useState(null)

  const navRef = useRef(null)
  const tabRefs = useRef([])
  const stageRef = useRef(null)
  const heroRef = useRef(null)
  const panelRef = useRef(null)
  const platesRef = useRef([])

  const wide = useMediaQuery('(min-width: 1180px)')
  const reduced = useReducedMotion()

  const activeIndex = Math.max(
    0,
    byCategory.findIndex((g) => g.key === tab),
  )

  /* The active-control underline slides rather than jumps, so it is one element
     positioned from a measurement instead of a border on each button. */
  useLayoutEffect(() => {
    const nav = navRef.current
    const el = tabRefs.current[activeIndex]
    if (!nav || !el) return
    const move = () => {
      const a = el.getBoundingClientRect()
      const b = nav.getBoundingClientRect()
      // centred and short of the control's full column: a rule the width of the
      // grid track reads as an arbitrary segment rather than a pointer
      const w = Math.max(56, a.width * 0.42)
      // measured into the rail's own scrolled coordinates: `left: 0` resolves to
      // the padding box's outer edge, so the gutter must NOT be subtracted
      setInk({ x: a.left - b.left + nav.scrollLeft + (a.width - w) / 2, w })
    }
    move()
    const ro = new ResizeObserver(move)
    ro.observe(nav)
    return () => ro.disconnect()
  }, [activeIndex, byCategory.length])

  /* Pointer parallax. The render and the label drift against each other by a
     few pixels so the label reads as floating in front of the cabin rather than
     sitting on the same plane. Transitioned, not lerped — the trailing ease is
     what keeps it from feeling like a mouse-follow toy. */
  useEffect(() => {
    const stage = stageRef.current
    if (!stage || !wide || reduced) return
    let raf = 0
    let x = 0
    let y = 0
    const apply = () => {
      raf = 0
      const hero = heroRef.current
      const panel = panelRef.current
      if (hero) {
        hero.style.setProperty('--px', `${(x * -10).toFixed(2)}px`)
        hero.style.setProperty('--py', `${(y * -7).toFixed(2)}px`)
      }
      if (panel) {
        panel.style.setProperty('--px', `${(x * 16).toFixed(2)}px`)
        panel.style.setProperty('--py', `${(y * 10).toFixed(2)}px`)
      }
    }
    const onMove = (e) => {
      const r = stage.getBoundingClientRect()
      x = (e.clientX - r.left) / r.width - 0.5
      y = (e.clientY - r.top) / r.height - 0.5
      if (!raf) raf = requestAnimationFrame(apply)
    }
    const onLeave = () => {
      x = 0
      y = 0
      if (!raf) raf = requestAnimationFrame(apply)
    }
    stage.addEventListener('pointermove', onMove)
    stage.addEventListener('pointerleave', onLeave)
    return () => {
      stage.removeEventListener('pointermove', onMove)
      stage.removeEventListener('pointerleave', onLeave)
      if (raf) cancelAnimationFrame(raf)
      onLeave()
    }
  }, [wide, reduced])

  if (!byCategory.length) return null

  const chosen = (key) => {
    const group = byCategory.find((g) => g.key === key)
    if (!group) return undefined
    return (
      group.options.find((o) => o.slug === choice[key]) ??
      group.options.find((o) => o.slug === DEFAULTS[key]) ??
      group.options[0]
    )
  }

  const wall = chosen('material')
  const activeGroup = byCategory[activeIndex] ?? byCategory[0]

  /* The frame follows the group being configured, not the wall: clicking an
     option shows that option, and moving between groups shows what is
     currently chosen there. One derived value, so the two can never disagree. */
  const shown = chosen(activeGroup.key)
  const preview = shown ? plateFor(activeGroup.key, shown.slug) : undefined

  // Plates are stacked and crossfaded, so a material change never flashes. Only
  // the ones actually visited are mounted — the rest stay unrequested.
  if (preview && !platesRef.current.some((p) => p.src === preview)) {
    platesRef.current = [
      ...platesRef.current,
      { src: preview, name: shown?.name ?? 'the selected finish' },
    ]
  }

  const enquiryHref = `/contact?${new URLSearchParams({
    config: byCategory.map((g) => `${g.key}=${chosen(g.key)?.slug ?? ''}`).join(','),
    ...(liftSlug ? { lift: liftSlug } : {}),
  })}`

  const onTabKey = (e) => {
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    e.preventDefault()
    const n = (activeIndex + step + byCategory.length) % byCategory.length
    setTab(byCategory[n].key)
    tabRefs.current[n]?.focus()
  }

  return (
    <section
      className={`section configurator ${compact ? 'configurator--compact' : ''}`}
      id="configure"
    >
      <div className="cfg__ground" aria-hidden="true" />

      <div className="cfg" ref={stageRef}>
        {!compact && (
          <Reveal className="cfg__lede" variant="fade">
            <p className="cfg__label">Build your Zion</p>
            <h2 className="cfg__title">
              <span className="cfg__line">Specify the lift,</span>
              <span className="cfg__line">
                then send it to us<span className="cfg__stop">.</span>
              </span>
            </h2>
            <p className="cfg__intro">
              Change a finish and the lift changes with it. Whatever you land on travels through to
              the enquiry form, so nobody has to describe it twice.
            </p>
          </Reveal>
        )}

        <Reveal className="cfg__hero" variant="scale" delay={compact ? 0 : 90}>
          <div className="cfg__shadow" aria-hidden="true" />
          <div className="cfg__hero-in" ref={heroRef}>
            <div className="cfg__plates">
              {platesRef.current.map((p) => (
                <div key={p.src} className={`cfg__plate ${p.src === preview ? 'is-on' : ''}`}>
                  <Img
                    src={p.src}
                    alt={p.src === preview ? `Cabin in ${p.name}` : ''}
                    sizes="(min-width: 1180px) 34vw, 92vw"
                  />
                </div>
              ))}
            </div>
            <div
              className="cfg__wash"
              style={{
                background: `linear-gradient(155deg, ${wall?.swatch_hex ?? '#B9BEC2'}2e, transparent 58%)`,
              }}
              aria-hidden="true"
            />
            <div className="cfg__fade" aria-hidden="true" />
          </div>
        </Reveal>

        <Reveal className="cfg__aside" variant="fade" delay={compact ? 90 : 220}>
          <aside className="cfg__spec" ref={panelRef}>
            <p className="cfg__spec-head">Your specification</p>
            <ul className="cfg__spec-list" aria-live="polite">
              {byCategory.map((g) => {
                const Mark = g.icon
                return (
                  <li key={g.key} className={`cfg__spec-row ${tab === g.key ? 'is-on' : ''}`}>
                    <Mark size={17} className="cfg__spec-mark" aria-hidden="true" />
                    <span className="cfg__spec-key">{g.label}</span>
                    {/* keyed on the slug so React remounts it and the value
                        change replays its fade instead of swapping silently */}
                    <span className="cfg__spec-val" key={chosen(g.key)?.slug}>
                      {chosen(g.key)?.name ?? '—'}
                    </span>
                  </li>
                )
              })}
            </ul>
            <Link to={enquiryHref} className="cfg__cta">
              <span>Request this design</span>
              <Arrow size={13} />
            </Link>
          </aside>
        </Reveal>

        <Reveal className="cfg__controls" variant="up" delay={compact ? 150 : 300}>
          <div className="cfg__nav" role="tablist" aria-label="Finish groups" ref={navRef}>
            {byCategory.map((g, i) => {
              const Mark = g.icon
              const on = g.key === activeGroup.key
              return (
                <button
                  key={g.key}
                  type="button"
                  role="tab"
                  id={`cfg-tab-${g.key}`}
                  aria-selected={on}
                  aria-controls={`cfg-panel-${g.key}`}
                  tabIndex={on ? 0 : -1}
                  ref={(el) => {
                    tabRefs.current[i] = el
                  }}
                  className={`cfg__nav-item ${on ? 'is-on' : ''}`}
                  onClick={() => setTab(g.key)}
                  onKeyDown={onTabKey}
                >
                  <Mark size={26} className="cfg__nav-mark" aria-hidden="true" />
                  <span className="cfg__nav-label">
                    {g.nav.map((l) => (
                      <span key={l}>{l}</span>
                    ))}
                  </span>
                </button>
              )
            })}
            <span
              className="cfg__ink"
              style={ink ? { transform: `translateX(${ink.x}px)`, width: `${ink.w}px` } : undefined}
              aria-hidden="true"
            />
          </div>

          <div
            className="cfg__opts"
            role="tabpanel"
            id={`cfg-panel-${activeGroup.key}`}
            aria-labelledby={`cfg-tab-${activeGroup.key}`}
            key={activeGroup.key}
          >
            {activeGroup.options.map((o, i) => {
              const on = chosen(activeGroup.key)?.slug === o.slug
              return (
                <button
                  key={o.slug}
                  type="button"
                  className={`cfg__opt ${on ? 'is-on' : ''}`}
                  style={{ '--i': i }}
                  onClick={() => setChoice((c) => ({ ...c, [activeGroup.key]: o.slug }))}
                  aria-pressed={on}
                >
                  {/* the swatch stays underneath as the colour the render
                      resolves to, so the card never flashes empty */}
                  <span
                    className="cfg__chip"
                    style={{
                      background: `linear-gradient(142deg, ${o.swatch_hex}, ${o.swatch_hex_2 || o.swatch_hex})`,
                    }}
                    aria-hidden="true"
                  >
                    <Img
                      src={plateFor(activeGroup.key, o.slug)}
                      alt=""
                      sizes="240px"
                      objectPosition={activeGroup.pos}
                    />
                    <span className="cfg__chip-sheen" />
                  </span>
                  <span className="cfg__opt-name">{o.name}</span>
                  {o.description && <span className="cfg__opt-desc">{o.description}</span>}
                  {o.tier !== 'standard' && <em className="cfg__tier">{o.tier}</em>}
                  <span className="cfg__tick" aria-hidden="true">
                    <svg viewBox="0 0 12 12" width="12" height="12">
                      <path d="M2.4 6.3 4.8 8.7 9.6 3.6" />
                    </svg>
                  </span>
                </button>
              )
            })}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
