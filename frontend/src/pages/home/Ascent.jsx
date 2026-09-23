import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow, Bolt, Refresh, Shield } from '@/components/icons'
import { useReducedMotion } from '@/lib/hooks'
import { gsap, initGsap } from '@/lib/gsap'

import ContextWave from './ContextWave'

/* ==========================================================================
   01 · HERO — THE SEQUENCE
   One take of the lift, pinned, and the scroll is its timeline. It is a real
   image sequence: 135 stills drawn to a canvas, one per scroll position. Not a
   video being seeked — a still is either decoded or it is not, so a frame can
   never arrive late or land a few tenths off the one that was asked for, which
   is what makes a scrubbed <video> stutter on a flick and on iOS.

   The direction is editorial: the take is the page, the type is set into the
   shadow at the left of the lobby, and the lift is never covered.
   ========================================================================== */

/** the stills, at the two sizes they were written out in */
const SEQ_COUNT = 135
const seqSrc = (dir, i) => `/media/hero/seq/${dir}/${String(i + 1).padStart(4, '0')}.webp`

/** how much of the runway is spent before the sequence starts, and after it
    ends, so the first and last stills are held rather than flashed past */
const LEAD = 0.06
const TAIL = 0.08

/** how fast the sequence catches up with the scroll: lower is heavier, and
    hides the step between stills on a fast flick */
const EASE = 0.14

/** Runs `cb` once the intro overlay (if there is one) has left the page, so the
    sequence is not drawn behind it. */
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

const clamp01 = (n) => (n < 0 ? 0 : n > 1 ? 1 : n)

/**
 * Loads the stills coarse-to-fine — every eighth, then every fourth, and so on
 * — so the whole length of the take is scrubbable within the first few frames
 * and simply gets sharper as the rest arrive, instead of the visitor waiting on
 * a strictly-in-order load to reach the part they have already scrolled to.
 */
function loadSequence(dir, onFrame) {
  const frames = Array.from({ length: SEQ_COUNT }, () => null)
  const queued = new Set()
  const order = []
  for (const step of [8, 4, 2, 1]) {
    for (let i = 0; i < SEQ_COUNT; i += step) {
      if (!queued.has(i)) {
        queued.add(i)
        order.push(i)
      }
    }
  }

  let next = 0
  let live = 0
  let stopped = false
  const CONCURRENCY = 6

  const pump = () => {
    while (!stopped && live < CONCURRENCY && next < order.length) {
      const i = order[next++]
      live += 1
      const img = new Image()
      img.decoding = 'async'
      img.onload = () => {
        live -= 1
        if (stopped) return
        frames[i] = img
        onFrame(i)
        pump()
      }
      img.onerror = () => {
        live -= 1
        if (!stopped) pump()
      }
      img.src = seqSrc(dir, i)
    }
  }
  pump()

  return {
    frames,
    stop() {
      stopped = true
    },
  }
}

export function Hero() {
  const sectionRef = useRef(null)
  const canvasRef = useRef(null)
  const reduced = useReducedMotion()
  const [introGone, setIntroGone] = useState(false)
  // the phone gets the lighter set; decided once, at mount
  const [dir] = useState(() =>
    typeof window !== 'undefined' && window.innerWidth < 900 ? 'w900' : 'w1600'
  )

  useEffect(() => whenIntroDone(() => setIntroGone(true)), [])

  useEffect(() => {
    const el = sectionRef.current
    const cv = canvasRef.current
    if (!el || !cv || reduced) return undefined

    const ctx = cv.getContext('2d', { alpha: false })

    let cur = 0
    let shown = -1
    let wrote = -1
    let w = 0
    let h = 0

    const seq = loadSequence(dir, () => {
      shown = -1 // a better still for the current position may have just landed
    })

    // the phone frames the lift a little right of centre and higher up, the way
    // the old object-position did, so it stays in shot on a tall narrow screen
    const focus = window.innerWidth < 640 ? [0.56, 0.42] : [0.5, 0.5]

    const size = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = cv.clientWidth
      h = cv.clientHeight
      cv.width = Math.round(w * dpr)
      cv.height = Math.round(h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      shown = -1
    }

    /** the nearest still that has actually arrived, at or before `i` */
    const nearest = (i) => {
      for (let k = i; k >= 0; k--) if (seq.frames[k]) return seq.frames[k]
      for (let k = i + 1; k < SEQ_COUNT; k++) if (seq.frames[k]) return seq.frames[k]
      return null
    }

    const paint = (i) => {
      const img = nearest(i)
      if (!img || !w || !h) return
      const r = Math.max(w / img.naturalWidth, h / img.naturalHeight)
      const dw = img.naturalWidth * r
      const dh = img.naturalHeight * r
      ctx.drawImage(img, (w - dw) * focus[0], (h - dh) * focus[1], dw, dh)
    }

    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      // off-screen: nothing to draw
      if (r.bottom < 0 || r.top > vh) return

      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      if (Math.abs(p - wrote) > 0.0005) {
        wrote = p
        el.style.setProperty('--p', p.toFixed(4))
        // the type is transparent past this point; let its CTA go
        el.classList.toggle('is-past', p > 0.26)
      }

      cur += (p - cur) * EASE
      // the sequence runs over the middle of the runway; the ends hold a still
      const at = clamp01((cur - LEAD) / (1 - LEAD - TAIL))
      const i = Math.round(at * (SEQ_COUNT - 1))
      if (i === shown) return
      shown = i
      paint(i)
    }

    size()
    gsap.ticker.add(tick)
    window.addEventListener('resize', size)
    return () => {
      seq.stop()
      gsap.ticker.remove(tick)
      window.removeEventListener('resize', size)
    }
  }, [reduced, dir])

  return (
    <section ref={sectionRef} className="hero" aria-label="Zion Lifts">
      <div className="hero__stage">
        {reduced ? (
          <img className="hero__film" src="/media/hero/hero-new-poster.jpg" alt="" aria-hidden="true" />
        ) : (
          <canvas
            ref={canvasRef}
            className={`hero__film ${introGone ? 'is-in' : ''}`}
            aria-hidden="true"
          />
        )}
        <div className="hero__grade" aria-hidden="true" />

        <div className={`hero__copy ${introGone || reduced ? 'is-in' : ''}`}>
          <h1 className="hero__title">
            <span className="hero__line" style={{ '--d': '60ms' }}>
              More than movement.
            </span>
            <span className="hero__line hero__line--accent" style={{ '--d': '180ms' }}>
              A higher standard.
            </span>
          </h1>

          <p className="hero__lead" style={{ '--d': '320ms' }}>
            Thoughtfully engineered lifts for homes, commercial spaces and specialised needs.
            Built to perform. Designed to belong.
          </p>

          <Link to="/lifts" className="hero__cta" style={{ '--d': '420ms' }}>
            <span className="hero__cta-label">Explore our range</span>
            <span className="hero__cta-icon" aria-hidden="true">
              <Arrow size={15} />
            </span>
          </Link>
        </div>

        {/* the cue: a mouse, its wheel dropping through, the word beneath.
            It is the only thing in the frame that moves of its own accord. */}
        <div className="hero__cue" aria-hidden="true">
          <span className="hero__mouse">
            <span className="hero__wheel" />
          </span>
          <span className="hero__cue-label">Scroll</span>
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
