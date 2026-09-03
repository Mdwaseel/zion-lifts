import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { SplitLines } from '@/components/Reveal'
import { Arrow, Bolt, Refresh, Shield } from '@/components/icons'
import { useReducedMotion, useScrollProgress } from '@/lib/hooks'
import { gsap, initGsap } from '@/lib/gsap'

import ContextWave from './ContextWave'

/* ==========================================================================
   01 · HERO — THE FILM
   One take of the lift, pinned. It runs to its first stop on its own; each
   scroll-step past a threshold releases the next chapter, which plays in real
   time to its own stop, and scrolling back up rewinds to the stop before.
   Nothing is scrubbed — the film always plays at speed; the scroll only
   decides how far it is allowed to go.
   ========================================================================== */

/** where the film holds, in seconds */
const STOPS = [4.1, 9.07, 13.26]

/** scroll progress across the runway (0–1) at which each later chapter releases.
    Spaced so a chapter has room to play out before the next threshold, with
    the last stretch left for the final one to finish before the pin lets go. */
const RELEASE = [0, 0.22, 0.58]

/** how close to a stop counts as arrived — one frame at 30fps is 33ms */
const EPS = 0.03

/** Runs `cb` once the intro overlay (if there is one) has left the page, so the
    first chapter does not play out behind it. */
function whenIntroDone(cb) {
  if (!document.querySelector('.preloader')) {
    cb()
    return () => {}
  }
  const mo = new MutationObserver(() => {
    if (!document.querySelector('.preloader')) {
      mo.disconnect()
      cb()
    }
  })
  mo.observe(document.body, { childList: true, subtree: true })
  return () => mo.disconnect()
}

export function Hero() {
  const [ref, progress] = useScrollProgress()
  const reduced = useReducedMotion()
  const videoRef = useRef(null)
  const rafRef = useRef(0)
  const headingRef = useRef(STOPS[0])
  const [introGone, setIntroGone] = useState(false)
  const [canPlay, setCanPlay] = useState(false)
  // the phone gets the lighter encode; decided once, at mount
  const [src] = useState(() =>
    typeof window !== 'undefined' && window.innerWidth < 900
      ? '/media/hero/hero-720.mp4'
      : '/media/hero/hero-1080.mp4'
  )

  // which stop the film is heading for, from where the visitor is on the runway
  const chapter = progress >= RELEASE[2] ? 2 : progress >= RELEASE[1] ? 1 : 0

  // copy leaves as the first chapter is released; the cue goes sooner
  const fade = reduced ? 0 : Math.min(1, progress / 0.2)

  useEffect(() => whenIntroDone(() => setIntroGone(true)), [])

  useEffect(() => {
    const v = videoRef.current
    if (!v || reduced || !introGone || !canPlay) return undefined

    const target = STOPS[chapter]
    const before = headingRef.current
    headingRef.current = target
    cancelAnimationFrame(rafRef.current)

    // scrolled back up: hold on the previous stop rather than replaying
    if (target < before - EPS) {
      v.pause()
      v.currentTime = target
      return undefined
    }
    if (v.currentTime >= target - EPS) {
      v.pause()
      return undefined
    }

    const tick = () => {
      if (v.currentTime >= target - EPS) {
        v.pause()
        v.currentTime = target
        return
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    v.play()
      .then(() => {
        rafRef.current = requestAnimationFrame(tick)
      })
      .catch(() => {
        /* autoplay refused — the poster stands in and the film waits for the next release */
      })

    return () => cancelAnimationFrame(rafRef.current)
  }, [chapter, reduced, introGone, canPlay])

  useEffect(() => () => cancelAnimationFrame(rafRef.current), [])

  return (
    <section ref={ref} className="hero" aria-label="Zion Lifts">
      <div className="hero__stage">
        <video
          ref={videoRef}
          className="hero__film"
          src={src}
          poster="/media/hero/hero-poster.jpg"
          muted
          playsInline
          preload={reduced ? 'none' : 'auto'}
          disablePictureInPicture
          aria-hidden="true"
          tabIndex={-1}
          onCanPlay={() => setCanPlay(true)}
        />
        <div className="hero__grade" aria-hidden="true" style={{ opacity: 1 - fade * 0.45 }} />

        <div className="shell hero__content" style={{ opacity: 1 - fade }}>
          <Reveal variant="fade">
            <p className="eyebrow">Vertical transportation · Hyderabad</p>
          </Reveal>

          <SplitLines
            as="h1"
            className="display hero__title"
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

        {/* the cue: a mouse, its wheel dropping through, the word beneath */}
        <div className="hero__cue" aria-hidden="true" style={{ opacity: 1 - fade * 1.6 }}>
          <span className="hero__mouse">
            <span className="hero__wheel" />
          </span>
          <span className="hero__cue-label">Scroll</span>
        </div>

        {/* the three stops */}
        <ol className="hero__stops" aria-hidden="true">
          {STOPS.map((s, i) => (
            <li key={s} className={i <= chapter ? 'is-on' : ''} />
          ))}
        </ol>
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
 * interior", "stretcher-width lifts, levelling accuracy"), so the strip states
 * things the rest of the site already states rather than inventing new claims.
 */
const CONTEXTS = [
  {
    key: 'villa',
    label: 'Villa',
    line: 'A private house, where the lift has to belong to the interior.',
    src: '/media/contexts/context-villa.jpg',
    pos: 'center 50%',
    alt: 'A glazed home lift beside the stair in a double-height villa living room',
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
    src: '/media/contexts/context-apartment.jpg',
    pos: 'center 50%',
    alt: 'A lift on a residential apartment landing, off a shared corridor',
    to: '/lifts/mrl-traction',
    amp: 0.9,
    features: [
      ['Daily duty', 'Sized for family use,', 'every hour of the day.'],
      ['Stretcher access', 'Lifts proportioned', 'to take a stretcher.'],
      ['Fewer parts', 'A gearless machine', 'has less to wear out.'],
    ],
  },
  {
    key: 'hotel',
    label: 'Hospitality',
    line: 'Guests, service and kitchen traffic, on three different schedules.',
    src: '/media/contexts/context-hotel.jpg',
    pos: 'center 50%',
    alt: 'Guests crossing a hotel lobby towards the lift',
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
    src: '/media/contexts/context-office.jpg',
    pos: 'center 50%',
    alt: 'An office floor at the lift landing, with staff arriving',
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
    src: '/media/contexts/context-hospital.jpg',
    pos: 'center 50%',
    alt: 'A hospital corridor where a patient is wheeled into a stretcher-width lift',
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
    src: '/media/contexts/context-industrial.jpg',
    pos: 'center 50%',
    alt: 'A goods lift on a factory floor, loaded by workers between machine bays',
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
      const last = idx === N - 1
      // Hold, then hand over during the tail of the slot — except in the last
      // slot, which has nothing to hand over to. `next` clamps back onto `idx`
      // there, so blending would fade the only visible layer to nothing and
      // leave an empty stage for the final quarter of the section.
      const t = last || frac <= 1 - BLEND ? 0 : (frac - (1 - BLEND)) / BLEND
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
    <section
      ref={sectionRef}
      className="section section--flush world"
      aria-labelledby="world-title"
    >
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
