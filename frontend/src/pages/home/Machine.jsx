import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { SplitLines } from '@/components/Reveal'
import { CeilingMark, DoorMark, FloorMark, PanelMark, WallMark } from '@/components/cabin-marks'
import { Arrow, CrosshairMark, GaugeMark, Shield, WaveMark } from '@/components/icons'
import { useMediaQuery, useReducedMotion } from '@/lib/hooks'

import EngSchematic from './EngSchematic'

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
export const GROUPS = [
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
export const plateFor = (category, slug) =>
  NO_RENDER[`${category}-${slug}`] ?? `/media/finishes/${category}-${slug}.jpg`

/** Finishes with no render of their own yet; the nearest plate stands in. */
const NO_RENDER = {
  'material-obsidian': '/media/interiors/interior-05.jpg',
}

/** Opening configuration. Everything else falls back to its first option. */
export const DEFAULTS = { material: 'antique-brass' }

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
