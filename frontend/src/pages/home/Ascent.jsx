import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { SplitLines } from '@/components/Reveal'
import { Arrow, ArrowDown, Bolt, Refresh, Shield } from '@/components/icons'
import { useReducedMotion, useScrollProgress } from '@/lib/hooks'
import { gsap, initGsap } from '@/lib/gsap'

import ContextWave from './ContextWave'

/* ==========================================================================
   01 · HERO — THE ELEVATOR
   Doors rest ajar on load; scrolling parts them onto the shaft beyond, while
   the floor indicator climbs. No image sequence exists yet, so the ascent is
   built from the real cabin photography plus a scroll-driven door mechanism.
   ========================================================================== */

const FLOORS = ['G', '2', '5', '9', '14', '19', '24', '31', '36']

/**
 * The doors rest slightly apart rather than shut. Closed, the fold was a black
 * rectangle with a headline on it and no product in sight; ajar, a band of the
 * real cabin shows down the centre and the gap tells you what scrolling does.
 */
const AJAR = 0.1

export function Hero() {
  const [ref, progress] = useScrollProgress()
  const reduced = useReducedMotion()

  // doors are fully open by 45% of the hero's travel
  const travel = reduced ? 1 : Math.min(1, progress / 0.45)
  const open = AJAR + travel * (1 - AJAR)
  const floor = FLOORS[Math.min(FLOORS.length - 1, Math.floor(travel * FLOORS.length))]

  return (
    <section ref={ref} className="hero" aria-label="Zion Lifts">
      <div className="hero__stage">
        {/* what lies beyond the doors */}
        <div
          className="hero__shaft"
          style={{ '--open': open, transform: `scale(${1.14 - travel * 0.14})` }}
        >
          <Img
            src="/media/frames/lekha-cabin.jpg"
            alt=""
            priority
            sizes="100vw"
            className="hero__shaft-img"
          />
        </div>

        {/* the doors themselves */}
        <div className="hero__doors" aria-hidden="true" style={{ '--open': open }}>
          <div className="hero__door hero__door--l">
            <span className="hero__door-seam" />
          </div>
          <div className="hero__door hero__door--r">
            <span className="hero__door-seam" />
          </div>
        </div>

        {/* floor indicator */}
        <div className="hero__ticker" aria-hidden="true">
          <span className="hero__ticker-arrow">&uarr;</span>
          <span className="hero__ticker-num">{floor}</span>
        </div>

        <div className="shell hero__content" style={{ opacity: 1 - travel * 0.55 }}>
          <Reveal variant="fade">
            <p className="eyebrow">Vertical transportation · Hyderabad</p>
          </Reveal>

          <SplitLines
            as="h1"
            className="display display--mega hero__title"
            lines={['Zion.', 'Engineered', 'to rise.']}
          />

          <Reveal delay={420}>
            <p className="lead hero__lead">
              Lifts designed, built, installed and maintained in Hyderabad — from a home elevator
              behind a brass door to a stretcher lift that never stops. 1,750 installations since
              2012.
            </p>
          </Reveal>

          <Reveal delay={520}>
            <div className="hero__actions">
              <Link to="/lifts" className="btn btn--accent">
                Explore the range <Arrow />
              </Link>
              <Link to="/projects" className="btn btn--ghost">
                See the work <Arrow />
              </Link>
            </div>
          </Reveal>
        </div>

        <div className="hero__scroll" aria-hidden="true" style={{ opacity: 1 - travel * 1.6 }}>
          <span className="mono">Scroll to ascend</span>
          <ArrowDown size={14} />
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   02 · THE WORLD BELOW
   ========================================================================== */

/**
 * Six building types in one pinned frame, crossfading as the visitor scrolls.
 *
 * The feature lines under each context are drawn from the application copy the
 * catalogue already carries ("tight shafts, finishes chosen to match the
 * interior", "stretcher-width cars, levelling accuracy"), so the strip states
 * things the rest of the site already states rather than inventing new claims.
 */
const CONTEXTS = [
  {
    key: 'villa',
    label: 'Villa',
    line: 'A private house, where the lift has to belong to the interior.',
    src: '/media/frames/lekha-hall.jpg',
    pos: 'center 45%',
    alt: 'A glazed home lift set into the hall of a private villa in Hyderabad',
    to: '/lifts/home-elevator',
    amp: 0.8,
    features: [
      ['Fits tight shafts', 'Two to five levels', 'in an existing core.'],
      ['Matched finishes', 'Chosen with the room,', 'not a catalogue.'],
      ['Runs quiet', 'Gearless drive,', 'no machine room.'],
    ],
  },
  {
    key: 'apartment',
    label: 'Apartment',
    line: 'A shared core, running from the basement to the terrace all day.',
    src: '/media/interiors/interior-02.jpg',
    pos: 'center 38%',
    alt: 'A lift lobby in a residential apartment tower',
    to: '/lifts/mrl-traction',
    amp: 0.9,
    features: [
      ['Daily duty', 'Sized for family use,', 'every hour of the day.'],
      ['Stretcher access', 'Cars proportioned', 'to take a stretcher.'],
      ['Fewer parts', 'A gearless machine', 'has less to wear out.'],
    ],
  },
  {
    key: 'hotel',
    label: 'Hospitality',
    line: 'Guests, service and kitchen traffic, on three different schedules.',
    src: '/media/frames/chath-entrance.jpg',
    pos: 'center 55%',
    alt: 'The lift entrance at Chath Restaurant, a hospitality project in Hyderabad',
    to: '/lifts/passenger-elevator',
    amp: 1,
    features: [
      ['Three schedules', 'Guest, service and', 'kitchen, kept apart.'],
      ['Quiet arrival', 'A closed-loop drive', 'shapes every stop.'],
      ['Finishes that last', 'Specified for', 'constant handling.'],
    ],
  },
  {
    key: 'office',
    label: 'Office',
    line: 'Judged entirely on its worst five minutes of the morning.',
    src: '/media/interiors/interior-04.jpg',
    pos: 'center 42%',
    alt: 'A black-framed panoramic lift in a commercial building',
    to: '/lifts/passenger-elevator',
    amp: 1.1,
    features: [
      ['Peak-hour ready', 'Group control for', 'the morning rush.'],
      ['Accurate stops', 'Levelling you cross', 'without noticing.'],
      ['Hard wearing', 'Finishes chosen for', 'heavy daily use.'],
    ],
  },
  {
    key: 'hospital',
    label: 'Hospital',
    line: 'Sized by the trolley, not the passenger count.',
    src: '/media/frames/owaisi-lobby.jpg',
    pos: 'center 48%',
    alt: 'A hospital lift lobby at Owaisi Hospitals, Hyderabad',
    to: '/lifts/hospital-elevator',
    amp: 0.75,
    features: [
      ['Stretcher width', 'Sized by the trolley,', 'not the passenger.'],
      ['Level every time', 'Accurate levelling', 'for wheeled loads.'],
      ['Fails safe', 'Dependable when the', 'power does not hold.'],
    ],
  },
  {
    key: 'industrial',
    label: 'Industrial',
    line: 'Loaded badly, in a hurry, every day of its life.',
    src: '/media/frames/kashi-machine.jpg',
    pos: 'center 40%',
    alt: 'The drive, sheave and structural steel frame at the head of a Zion shaft',
    to: '/lifts/goods-elevator',
    amp: 1.25,
    features: [
      ['Built tough', 'For heavy loads', 'and constant use.'],
      ['Moves fast', 'Made for time', 'that matters.'],
      ['Keeps going', 'Reliable, durable', 'and easy to service.'],
    ],
  },
]

const FEATURE_ICONS = [Shield, Bolt, Refresh]

/** Fraction of each context's slot spent crossfading into the next. */
const BLEND = 0.25

export function WorldBelow() {
  const sectionRef = useRef(null)
  const layersRef = useRef([])
  const copyRef = useRef(null)
  const waveRef = useRef(null)
  const [active, setActive] = useState(0)
  const reduced = useReducedMotion()
  const N = CONTEXTS.length

  // Show exactly one context, whatever is driving the choice.
  const showLayer = (a) => {
    for (let i = 0; i < N; i++) {
      const el = layersRef.current[i]
      if (!el) continue
      el.style.opacity = i === a ? 1 : 0
      el.style.transform = 'none'
    }
  }

  useEffect(() => {
    const section = sectionRef.current
    if (!section) return

    /* Reduced motion collapses every scroll runway on this page to zero
       height, which would leave this section permanently at progress 1 and
       strand five of the six contexts behind a scroll that can no longer
       happen. So when motion is reduced the rail drives the section directly
       and no ScrollTrigger is created (see the effect below). */
    if (reduced) return

    const { ScrollTrigger } = initGsap()

    const apply = (progress) => {
      const x = Math.min(N - 0.0001, Math.max(0, progress * N))
      const idx = Math.floor(x)
      const frac = x - idx
      // hold, then hand over during the tail of the slot
      const t = frac <= 1 - BLEND ? 0 : (frac - (1 - BLEND)) / BLEND
      const next = Math.min(N - 1, idx + 1)

      for (let i = 0; i < N; i++) {
        const el = layersRef.current[i]
        if (!el) continue
        let o = 0
        let s = 1.03
        if (i === idx) {
          o = 1 - t
          s = 1 + 0.03 * t
        } else if (i === next && t > 0) {
          o = t
          s = 1.03 - 0.03 * t
        }
        el.style.opacity = o
        el.style.transform = `scale(${s.toFixed(4)})`
      }

      const a = t > 0.5 ? next : idx
      setActive((prev) => (prev === a ? prev : a))
      waveRef.current?.setProgress(progress, CONTEXTS[a].amp)
    }

    const st = ScrollTrigger.create({
      trigger: section,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => apply(self.progress),
      onRefresh: (self) => apply(self.progress),
    })
    return () => st.kill()
    // deliberately not keyed on `active`: the trigger sets it, and rebuilding
    // the trigger on every context change would tear down mid-scroll
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [N, reduced])

  // reduced motion: the rail is the only thing that changes the context
  useEffect(() => {
    if (!reduced) return
    showLayer(active)
    waveRef.current?.setProgress(0, CONTEXTS[active].amp)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduced, active])

  // the copy block re-enters whenever the context changes
  useEffect(() => {
    if (reduced || !copyRef.current) return
    const tween = gsap.fromTo(
      copyRef.current.children,
      { autoAlpha: 0, y: 18 },
      { autoAlpha: 1, y: 0, duration: 0.5, stagger: 0.05, ease: 'power2.out', overwrite: true },
    )
    return () => tween.kill()
  }, [active, reduced])

  const goTo = (i) => {
    const section = sectionRef.current
    if (!section) return
    const runway = section.offsetHeight - window.innerHeight
    // no runway to travel along: switch the context in place
    if (reduced || runway <= 0) {
      setActive(i)
      return
    }
    const top = section.getBoundingClientRect().top + window.scrollY
    const target = top + runway * ((i + 0.5) / N)
    if (window.__lenis) window.__lenis.scrollTo(target, { duration: 1 })
    else window.scrollTo({ top: target, behavior: 'smooth' })
  }

  const current = CONTEXTS[active]

  return (
    <section ref={sectionRef} className="section section--flush world" aria-labelledby="world-title">
      <div className="world__pin">
        <div className="world__stage">
          {CONTEXTS.map((c, i) => (
            <div
              key={c.key}
              className="world__layer"
              ref={(el) => (layersRef.current[i] = el)}
              style={{ opacity: i === 0 ? 1 : 0 }}
            >
              <Img
                src={c.src}
                alt={i === active ? c.alt : ''}
                sizes="100vw"
                priority={i === 0}
                objectPosition={c.pos}
              />
            </div>
          ))}

          <div className="world__veil" aria-hidden="true" />
          <div className="world__floor" aria-hidden="true" />
          <ContextWave ref={waveRef} />

          <div className="shell world__content">
            <h2 className="world__title" id="world-title">
              Every building
              <br />
              has a different
              <br />
              <em>rhythm.</em>
            </h2>

            <div className="world__now" ref={copyRef}>
              <h3 className="world__label">{current.label}</h3>
              <p className="world__line">{current.line}</p>
              <Link to={current.to} className="world__cta">
                The lift for it <Arrow size={14} />
              </Link>
            </div>

            <ul className="world__features">
              {current.features.map(([title, l1, l2], i) => {
                const Icon = FEATURE_ICONS[i]
                return (
                  <li className="world__feature" key={title}>
                    <Icon size={18} className="world__feature-icon" />
                    <div>
                      <p className="world__feature-title">{title}.</p>
                      <p className="world__feature-body">
                        {l1}
                        <br />
                        {l2}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ul>

            <nav className="world__rail" aria-label="Building contexts">
              <ol>
                {CONTEXTS.map((c, i) => (
                  <li key={c.key} className={i === active ? 'is-on' : ''}>
                    <button
                      type="button"
                      onClick={() => goTo(i)}
                      aria-current={i === active ? 'true' : undefined}
                    >
                      <span className="world__rail-dot">{String(i + 1).padStart(2, '0')}</span>
                      <span className="world__rail-label">{c.label}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </nav>
          </div>
        </div>
      </div>
      {/* scroll runway that drives the pinned stage above */}
      <div className="world__runway" aria-hidden="true" />
    </section>
  )
}
