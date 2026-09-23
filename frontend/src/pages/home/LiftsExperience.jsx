import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoLoop } from '@/components/Media'
import { Arrow, ArrowDown, CogMark, GaugeMark, UpDownMark, UsersMark } from '@/components/icons'
import { LIFT_ICONS } from '@/components/lift-marks'
import { gsap } from '@/lib/gsap'
import { useMediaQuery, useReducedMotion } from '@/lib/hooks'

/* ==========================================================================
   03 · THE LIFTS — nine systems, one room at a time
   A full-screen scene: the architecture fills the viewport, the editorial copy
   for the lift in view sits down the left, and a glass rail of the nine marks
   stands on the right. The section is held at the top of the screen over a
   runway of scroll; each stretch of that runway is one lift, and crossing into
   the next one dissolves the room and the copy into the next room and its
   copy — the same move the rail and the Next control make, by scrolling there.

   Pinning is `position: sticky` over a runway, like every other pinned section
   on this page; the section's own rectangle is read each frame and eased
   towards, which is what a scrubbed ScrollTrigger does under the hood, without
   a second pinning system on the document.
   ========================================================================== */

/* The room each lift is shown in on a wide screen: a landscape frame from the
   project's own photography. On a phone the portrait loops stand in. */
export const ROOMS = {
  'home-elevator': { src: '/media/frames/lekha-hall.jpg', pos: '50% 50%' },
  'capsule-elevator': { src: '/media/products/capsule-02.jpg', pos: '50% 40%' },
  'mrl-traction': { src: '/media/contexts/context-apartment.jpg', pos: '50% 50%' },
  'hydraulic-elevator': { src: '/media/contexts/context-office.jpg', pos: '50% 50%' },
  'passenger-elevator': { src: '/media/frames/chath-entrance.jpg', pos: '50% 50%' },
  'hospital-elevator': { src: '/media/contexts/context-hospital.jpg', pos: '50% 50%' },
  'goods-elevator': { src: '/media/contexts/context-industrial.jpg', pos: '50% 50%' },
  dumbwaiter: { src: '/media/products/dumbwaiter-02.jpg', pos: '50% 50%' },
  'car-stacker': { src: '/media/products/car-stacker-02.jpg', pos: '50% 50%' },
}

export const FEATURES = [
  ['Capacity', 'capacity', UsersMark],
  ['Speed', 'speed', GaugeMark],
  ['Stops', 'stops', UpDownMark],
  ['Drive', 'drive', CogMark],
]

/* one lift's stretch of the runway, in timeline units */
const SEG = 10
/* how far into a stretch the room has fully changed */
const CROSS = 3
/* where a rail click or Next lands: the room settled, the copy up */
const LANDED = 4.5

const clamp01 = (v) => Math.max(0, Math.min(1, v))
const pad = (n) => String(n).padStart(2, '0')

/** the tagline as a headline: every word on its own rise, the last one set in
    italic — the one word the line turns on */
function Headline({ text }) {
  const words = text.split(' ')
  return words.map((w, i) => (
    /* the space lives outside the clipped word, or it is trimmed with it */
    <span key={i}>
      <span className="lx__word">
        <span className="lx__word-in">{i === words.length - 1 ? <em>{w}</em> : w}</span>
      </span>
      {i < words.length - 1 ? ' ' : ''}
    </span>
  ))
}

export function LiftsExperience({ lifts = [] }) {
  const items = lifts.filter((l) => ROOMS[l.slug])
  const count = items.length
  const [active, setActive] = useState(0)
  const reduced = useReducedMotion()
  const small = useMediaQuery('(max-width: 767px)')

  const sectionRef = useRef(null)
  const layerRefs = useRef([])
  const panelRefs = useRef([])
  const fillRef = useRef(null)
  const countRef = useRef(null)
  const st = useRef({ tl: null, shown: -1, seg: -1, total: 1 }).current

  useEffect(() => {
    const section = sectionRef.current
    if (!section || !count || reduced) return undefined
    const vh = () => window.innerHeight

    const build = () => {
      st.tl?.kill()
      const layers = layerRefs.current.filter(Boolean)
      const tl = gsap.timeline({ paused: true, defaults: { ease: 'none' } })

      items.forEach((l, i) => {
        const at = i * SEG
        const layer = layers[i]
        const panel = panelRefs.current[i]
        const label = panel.querySelector('.lx__label')
        const words = panel.querySelectorAll('.lx__word-in')
        const desc = panel.querySelector('.lx__desc')
        const feats = panel.querySelectorAll('.lx__feat')
        const cta = panel.querySelector('.lx__cta')

        /* the room: the next one dissolves in over the last, settling from a
           breath larger, then drifts slower than the eye through the hold */
        gsap.set(layer, { opacity: i === 0 ? 1 : 0, scale: 1.06 })
        if (i > 0) tl.to(layer, { opacity: 1, duration: CROSS, ease: 'power2.inOut' }, at)
        tl.to(layer, { scale: 1, duration: SEG, ease: 'none' }, at)
        if (i > 0) tl.set(layers[i - 1], { opacity: 0 }, at + CROSS)

        /* the copy: in after the room has changed, out as the next begins */
        gsap.set(panel, { autoAlpha: 0, pointerEvents: 'none' })
        gsap.set(label, { opacity: 0, y: 10 })
        gsap.set(words, { yPercent: 110 })
        gsap.set(desc, { opacity: 0, y: 14 })
        gsap.set(feats, { opacity: 0, y: 10 })
        gsap.set(cta, { opacity: 0, y: 8 })
        const inAt = at + (i === 0 ? 0.3 : CROSS * 0.55)
        tl.set(panel, { autoAlpha: 1, pointerEvents: 'auto' }, inAt)
          .to(label, { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }, inAt)
          .to(words, { yPercent: 0, duration: 1.1, stagger: 0.07, ease: 'power3.out' }, inAt + 0.15)
          .to(desc, { opacity: 1, y: 0, duration: 0.9, ease: 'power2.out' }, inAt + 0.7)
          .to(feats, { opacity: 1, y: 0, duration: 0.7, stagger: 0.1, ease: 'power2.out' }, inAt + 1.0)
          .to(cta, { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out' }, inAt + 1.4)
        if (i < count - 1) {
          const outAt = at + SEG
          tl.to([label, desc, cta], { opacity: 0, y: -8, duration: 0.7, ease: 'power2.in' }, outAt)
            .to(words, { yPercent: -110, duration: 0.6, stagger: 0.04, ease: 'power2.in' }, outAt)
            .to(feats, { opacity: 0, duration: 0.5, ease: 'power2.in' }, outAt)
            .set(panel, { autoAlpha: 0, pointerEvents: 'none' }, outAt + 0.9)
        }

        /* the progress: a line that lengthens by one lift each time */
        tl.to(fillRef.current, { scaleX: (i + 1) / count, duration: CROSS, ease: 'power2.inOut' }, i === 0 ? 0 : at)
      })
      /* a beat on the last room before the pin lets go */
      tl.to({}, { duration: 2 }, count * SEG)

      gsap.set(fillRef.current, { scaleX: 1 / count, transformOrigin: '0 50%' })
      st.tl = tl
      st.total = tl.duration()
    }
    build()

    const paint = (p) => {
      if (!st.tl) return
      st.tl.progress(p)
      const seg = Math.min(count - 1, Math.floor((p * st.total) / SEG))
      if (seg !== st.seg) {
        st.seg = seg
        if (countRef.current) countRef.current.textContent = pad(seg + 1)
        setActive(seg)
      }
    }
    const tick = () => {
      const r = section.getBoundingClientRect()
      if (r.bottom < -vh() || r.top > vh() * 2) return
      const target = clamp01(-r.top / Math.max(1, r.height - vh()))
      const next = st.shown < 0 ? target : st.shown + (target - st.shown) * 0.1
      if (st.shown >= 0 && Math.abs(next - st.shown) < 0.0004) return
      st.shown = next
      paint(next)
    }
    gsap.ticker.add(tick)

    /* a rail mark or Next travels the runway to where that lift is settled */
    st.travel = (i) => {
      const r = section.getBoundingClientRect()
      const runway = Math.max(1, r.height - vh())
      const p = (i * SEG + LANDED) / st.total
      const y = Math.round(r.top + window.scrollY + p * runway)
      if (window.__lenis) window.__lenis.scrollTo(y, { duration: 1.3 })
      else window.scrollTo({ top: y, behavior: 'smooth' })
    }

    let raf = 0
    const onResize = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        build()
        st.shown = -1
        st.seg = -1
      })
    }
    window.addEventListener('resize', onResize)
    return () => {
      gsap.ticker.remove(tick)
      window.removeEventListener('resize', onResize)
      cancelAnimationFrame(raf)
      st.tl?.kill()
      st.tl = null
      st.seg = -1
      st.shown = -1
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count, reduced, small])

  if (!count) return null

  const pick = (i) => {
    const n = ((i % count) + count) % count
    if (reduced) setActive(n)
    else st.travel?.(n)
  }
  const current = items[Math.min(active, count - 1)]

  return (
    <section
      ref={sectionRef}
      className={`section lx ${reduced ? 'lx--still' : ''}`}
      aria-labelledby={`lx-title-${current.slug}`}
      id="lifts"
      style={{ '--lifts': count }}
    >
      <div className="lx__stage">
        {/* the rooms */}
        <div className="lx__scene" aria-hidden="true">
          {items.map((l, i) => {
            const room = ROOMS[l.slug]
            const on = i === active
            return (
              <div
                className={`lx__layer ${on ? 'is-on' : ''}`}
                key={l.slug}
                ref={(el) => {
                  layerRefs.current[i] = el
                }}
              >
                {small ? (
                  on && !reduced ? (
                    <VideoLoop src={`/media/lifts/${l.slug}.mp4`} poster={`/media/lifts/${l.slug}.jpg`} />
                  ) : (
                    <Img src={`/media/lifts/${l.slug}.jpg`} alt="" sizes="100vw" priority={i === 0} />
                  )
                ) : (
                  <Img src={room.src} alt="" sizes="100vw" objectPosition={room.pos} priority={i === 0} />
                )}
              </div>
            )
          })}
          <div className="lx__grade" />
        </div>

        {/* the copy, one panel per lift, stacked in the same place */}
        <div className="lx__copy">
          {items.map((l, i) => (
            <article
              className={`lx__panel ${i === active ? 'is-on' : ''}`}
              key={l.slug}
              aria-hidden={i !== active}
              ref={(el) => {
                panelRefs.current[i] = el
              }}
            >
              <p className="lx__label">
                {l.eyebrow} · {l.name}
              </p>
              <h2 className="lx__title" id={`lx-title-${l.slug}`}>
                <Headline text={l.tagline || l.name} />
              </h2>
              <p className="lx__desc">{l.summary}</p>
              <ul className="lx__feats">
                {FEATURES.filter(([, key]) => l[key]).map(([label, key, Icon]) => (
                  <li className="lx__feat" key={key}>
                    <Icon size={22} aria-hidden="true" />
                    <span className="lx__feat-k">{label}</span>
                    <span className="lx__feat-v">{l[key]}</span>
                  </li>
                ))}
              </ul>
              <Link to={`/lifts/${l.slug}`} className="lx__cta" tabIndex={i === active ? 0 : -1}>
                <span className="lx__cta-ring" aria-hidden="true">
                  <Arrow size={14} />
                </span>
                Explore the {l.short_name || l.name}
              </Link>
            </article>
          ))}
        </div>

        {/* the rail: the nine, in glass */}
        <nav className="lx__rail" aria-label="Lift systems">
          <ol className="lx__glass">
            {items.map((l, i) => {
              const Icon = LIFT_ICONS[l.slug]
              const on = i === active
              return (
                <li key={l.slug}>
                  <button
                    type="button"
                    className={`lx__pick ${on ? 'is-on' : ''}`}
                    onClick={() => pick(i)}
                    aria-label={`${l.name}${on ? ', shown' : ''}`}
                    aria-current={on ? 'true' : undefined}
                  >
                    <span className="lx__pick-icon">{Icon ? <Icon size={24} /> : pad(i + 1)}</span>
                    {/* the name is a flag that comes out beside the mark on
                        hover; the button carries it for screen readers */}
                    <span className="lx__pick-name" aria-hidden="true">
                      {l.short_name || l.name}
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
        </nav>

        {/* where you are in the nine */}
        <p className="lx__progress" aria-hidden="true">
          <span className="lx__progress-n" ref={countRef}>
            {pad(active + 1)}
          </span>
          <span className="lx__progress-bar">
            <span className="lx__progress-fill" ref={fillRef} />
          </span>
          <span className="lx__progress-of">{pad(count)}</span>
        </p>

        {/* on to the next room */}
        <button type="button" className="lx__next" onClick={() => pick(active + 1)}>
          <span className="lx__next-ring" aria-hidden="true">
            <ArrowDown size={16} />
          </span>
          <span className="lx__next-label">Next lift</span>
        </button>
      </div>
    </section>
  )
}
