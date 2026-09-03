import { useCallback, useEffect, useRef, useState } from 'react'

import { CeilingMark, DoorMark, FloorMark, PanelMark, WallMark } from '@/components/cabin-marks'
import { gsap, initGsap } from '@/lib/gsap'
import { useMediaQuery, useReducedMotion } from '@/lib/hooks'
import { srcSet } from '@/lib/media'

/* ==========================================================================
   06 · THE CABIN
   ==========================================================================

   One cabin, five specifications, one render each — the section 2 set, built
   through assets-src/build_images.py. All five are stacked and crossfade in
   place, rather than swapping a src on one element, so the incoming frame is
   already decoded when it fades up and the transition never flashes empty.

   The silhouette is a clipped polygon rather than a rectangle. The left edge
   steps and both bottom corners are cut away, so the render sits in the page as
   a piece of architecture instead of a card in a grid. */

const SPECS = [
  {
    key: 'ceiling',
    label: ['Ceiling &', 'lighting'],
    aria: 'Ceiling and lighting',
    icon: CeilingMark,
    src: '/media/cabin/cabin-ceiling.jpg',
    alt: 'An illuminated cabin ceiling panel framed in brushed brass',
    pos: '50% 50%',
  },
  {
    key: 'walls',
    label: ['Walls &', 'finish'],
    aria: 'Walls and finish',
    icon: WallMark,
    src: '/media/cabin/cabin-walls.jpg',
    alt: 'Brushed bronze cabin wall panels meeting at a mitred corner',
    pos: '50% 45%',
  },
  {
    key: 'flooring',
    label: ['Flooring'],
    aria: 'Flooring',
    icon: FloorMark,
    src: '/media/cabin/cabin-flooring.jpg',
    alt: 'A marble cabin floor with a brass inlay border under downlights',
    pos: '50% 55%',
  },
  {
    key: 'panel',
    label: ['Control', 'panel'],
    aria: 'Control panel',
    icon: PanelMark,
    src: '/media/cabin/cabin-panel.jpg',
    alt: 'The car operating panel, with floor indicator and brass call buttons',
    pos: '50% 45%',
  },
  {
    key: 'doors',
    label: ['Doors &', 'entrance'],
    aria: 'Doors and entrance',
    icon: DoorMark,
    src: '/media/cabin/cabin-doors.jpg',
    alt: 'The lift entrance in a daylit hallway beside a stair',
    pos: '50% 50%',
  },
]

/* cubic-bezier(0.22, 1, 0.36, 1) is a quintic ease-out */
const EASE = 'power4.out'

/* Pinned, the section holds itself with `position: sticky` over a scroll
   runway — the same way every other pinned chapter on this page does. GSAP's
   own pinning is deliberately not used: two pinning systems fighting over the
   same document height is where the classic refresh-order bugs come from.
   One slot of scroll per specification, plus a tail so the last one is held
   rather than released the instant it arrives. */
const SLOT_SVH = 38
const TAIL_SLOTS = 1

/* --- drafting annotations -------------------------------------------------
   A leader line off the top-left corner and a compass rose low and right. Thin,
   low opacity, hidden from the accessibility tree — it should reward a second
   look rather than announce itself. */

function CabinDraft({ compassRef }) {
  return (
    <>
      <svg className="cabin__leader" viewBox="0 0 240 64" aria-hidden="true" focusable="false">
        <path d="M0 6H198L236 46" />
      </svg>

      <svg
        className="cabin__compass"
        viewBox="0 0 200 200"
        aria-hidden="true"
        focusable="false"
        ref={compassRef}
      >
        <circle className="cd-ring" cx="100" cy="100" r="86" />
        <circle className="cd-ring cd-ring--in" cx="100" cy="100" r="60" />
        <path className="cd-line" d="M100 14v172M14 100h172" />
        <path className="cd-line cd-dash" d="M39 39l122 122M161 39L39 161" />
        <circle className="cd-dot" cx="100" cy="14" r="3.2" />
        <circle className="cd-dot cd-dot--soft" cx="161" cy="39" r="2.4" />
        <circle className="cd-dot cd-dot--soft" cx="14" cy="100" r="2.4" />
      </svg>
    </>
  )
}

export function Cabin() {
  const [active, setActive] = useState(0)
  const reduced = useReducedMotion()

  const wide = useMediaQuery('(min-width: 1180px)')
  const pinned = wide && !reduced

  const sectionRef = useRef(null)
  const scrollerRef = useRef(null)
  const frameRef = useRef(null)
  const stackRef = useRef(null)
  const layerRefs = useRef([])
  const titleRef = useRef(null)
  const leadRef = useRef(null)
  const railRef = useRef(null)
  const metaRef = useRef(null)
  const dotsRef = useRef(null)
  const compassRef = useRef(null)
  const tabRefs = useRef([])
  const played = useRef(false)
  const shown = useRef(-1)

  /* --- changing specification --------------------------------------------
     Every layer is mounted, so the change is only ever a crossfade between two
     elements that are both already decoded. `shown` starts at -1 so the first
     pass sets the opening state without animating — and it is a ref, which
     StrictMode's remount preserves, so the seeding below resets it. */
  useEffect(() => {
    const layers = layerRefs.current
    if (!layers[active]) return
    const from = shown.current
    shown.current = active

    if (from === -1 || reduced) {
      layers.forEach((el, i) => el && gsap.set(el, { autoAlpha: i === active ? 1 : 0, scale: 1 }))
      return
    }
    if (from === active) return

    const tl = gsap.timeline()
    tl.to(layers[from], { autoAlpha: 0, duration: 0.55, ease: 'power2.inOut' }, 0).fromTo(
      layers[active],
      { autoAlpha: 0, scale: 1.02 },
      { autoAlpha: 1, scale: 1, duration: 0.72, ease: EASE },
      0.04,
    )
    return () => tl.kill()
  }, [active, reduced])

  /* StrictMode remounts on the same instance and the refs survive it, so the
     guards are re-seeded here or the second pass animates a non-change. */
  useEffect(() => {
    shown.current = -1
    return () => {
      shown.current = -1
    }
  }, [])

  /* --- entrance and parallax --------------------------------------------- */
  useEffect(() => {
    if (reduced || played.current) return
    const section = sectionRef.current
    if (!section) return
    played.current = true

    const { gsap: g } = initGsap()
    const ctx = g.context(() => {
      const strokes = section.querySelectorAll('.cd-line, .cd-ring, .cabin__leader path')
      strokes.forEach((el) => {
        const len = el.getTotalLength?.() ?? 0
        if (len) g.set(el, { strokeDasharray: len, strokeDashoffset: len })
      })

      const tl = g.timeline({
        scrollTrigger: { trigger: section, start: 'top 78%', once: true },
        defaults: { ease: 'power3.out' },
      })

      tl.from(frameRef.current, { autoAlpha: 0, scale: 1.04, duration: 1.1, ease: 'power2.out' }, 0)
        .from(
          titleRef.current.querySelectorAll('.cabin__line'),
          { yPercent: 108, duration: 0.9, stagger: 0.08 },
          0.18,
        )
        .from(leadRef.current, { y: 15, autoAlpha: 0, duration: 0.7 }, 0.36)
        .from(
          railRef.current.querySelectorAll('.cabin__spec'),
          { y: 14, autoAlpha: 0, duration: 0.6, stagger: 0.08 },
          0.5,
        )
        .from(metaRef.current, { y: 10, autoAlpha: 0, duration: 0.6 }, 0.8)
        .from(dotsRef.current, { autoAlpha: 0, duration: 0.8 }, 0.88)
        .to(strokes, { strokeDashoffset: 0, duration: 1.4, stagger: 0.05 }, 0.55)

      // anchored, not floating: 14px of drift. Pointless while pinned — the
      // frame is standing still — so it is only wired up when it is not.
      if (pinned) return
      g.fromTo(
        stackRef.current,
        { y: -14 },
        {
          y: 14,
          ease: 'none',
          scrollTrigger: { trigger: section, start: 'top bottom', end: 'bottom top', scrub: 0.6 },
        },
      )
    }, section)

    return () => {
      ctx.revert()
      played.current = false
    }
  }, [reduced, pinned])

  /* --- scroll picks the specification while the frame is held ------------
     Measured off the live rect rather than a ScrollTrigger. This section sits
     roughly 13,000px down a page that keeps growing as lazy images above it
     decode, so a trigger's start/end — cached at creation and only corrected
     on refresh — read stale here and clamp progress to 1, which pins the
     section on its last specification. A rect read costs nothing and cannot go
     stale; the rAF gate keeps it to one measurement per frame, and `active`
     only changes on a slot boundary. */
  useEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller || !pinned) return
    const slots = SPECS.length + TAIL_SLOTS
    let raf = 0
    const measure = () => {
      raf = 0
      const rect = scroller.getBoundingClientRect()
      const runway = Math.max(1, rect.height - window.innerHeight)
      const progress = Math.min(1, Math.max(0, -rect.top / runway))
      const i = Math.min(SPECS.length - 1, Math.floor(progress * slots))
      setActive((prev) => (prev === i ? prev : i))
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(measure)
    }
    measure()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [pinned])

  /* --- selecting ---------------------------------------------------------
     Pinned, a click cannot just set the index: scroll owns it, and the next
     scroll event would snap it straight back. It moves the page to that slot
     instead and lets the trigger above do the setting. */
  const select = useCallback(
    (i) => {
      const n = ((i % SPECS.length) + SPECS.length) % SPECS.length
      const scroller = scrollerRef.current
      const runway = scroller ? scroller.offsetHeight - window.innerHeight : 0
      if (pinned && scroller && runway > 0) {
        const top = scroller.getBoundingClientRect().top + window.scrollY
        const target = top + runway * ((n + 0.5) / (SPECS.length + TAIL_SLOTS))
        if (window.__lenis) window.__lenis.scrollTo(target, { duration: 0.8 })
        else window.scrollTo({ top: target, behavior: 'smooth' })
      } else {
        setActive(n)
      }
      tabRefs.current[n]?.focus({ preventScroll: true })
    },
    [pinned],
  )

  const onKeyDown = (e) => {
    const map = {
      ArrowRight: active + 1,
      ArrowDown: active + 1,
      ArrowLeft: active - 1,
      ArrowUp: active - 1,
      Home: 0,
      End: SPECS.length - 1,
    }
    if (!(e.key in map)) return
    e.preventDefault()
    select(map[e.key])
  }

  const current = SPECS[active]

  return (
    <section ref={sectionRef} className="section cabin" aria-labelledby="cabin-title">
      <div
        className={`cabin__scroller ${pinned ? 'is-pinned' : ''}`}
        ref={scrollerRef}
        style={pinned ? { '--cabin-runway': `${(SPECS.length + TAIL_SLOTS) * SLOT_SVH}svh` } : undefined}
      >
        <div className="cabin__pin">
          <div className="cabin__grid">
            <div className="cabin__copy">
              <h2 className="cabin__title" id="cabin-title" ref={titleRef}>
                <span className="cabin__line-mask">
                  <span className="cabin__line">Designed around</span>
                </span>
                <span className="cabin__line-mask">
                  <span className="cabin__line">
                    your architecture<span className="cabin__stop">.</span>
                  </span>
                </span>
              </h2>
              <p className="cabin__lead" ref={leadRef}>
                Wall material, flooring, ceiling, lighting, handrail and control panel are specified
                separately — with the interior, not from a fixed catalogue.
              </p>
            </div>

            <div
              className="cabin__rail"
              role="tablist"
              aria-label="Cabin specification"
              aria-orientation="horizontal"
              onKeyDown={onKeyDown}
              ref={railRef}
            >
              {SPECS.map((s, i) => {
                const Icon = s.icon
                const on = i === active
                return (
                  <button
                    key={s.key}
                    type="button"
                    role="tab"
                    id={`cabin-tab-${s.key}`}
                    aria-selected={on}
                    aria-label={s.aria}
                    aria-controls="cabin-panel"
                    tabIndex={on ? 0 : -1}
                    ref={(el) => {
                      tabRefs.current[i] = el
                    }}
                    className={`cabin__spec ${on ? 'is-on' : ''}`}
                    onClick={() => select(i)}
                  >
                    <Icon size={40} className="cabin__spec-icon" />
                    <span className="cabin__spec-rule" aria-hidden="true" />
                    <span className="cabin__spec-name">
                      {s.label.map((l) => (
                        <span key={l}>{l}</span>
                      ))}
                    </span>
                  </button>
                )
              })}
            </div>

            <div className="cabin__meta" ref={metaRef}>
              <p className="cabin__count">
                <span className="cabin__count-n">{String(active + 1).padStart(2, '0')}</span>
                <span className="cabin__count-of"> / {String(SPECS.length).padStart(2, '0')}</span>
              </p>
              <span className="cabin__track" aria-hidden="true">
                <span
                  className="cabin__track-fill"
                  style={{ transform: `scaleX(${(active + 1) / SPECS.length})` }}
                />
              </span>
            </div>

            <div
              className="cabin__visual"
              id="cabin-panel"
              role="tabpanel"
              aria-labelledby={`cabin-tab-${current.key}`}
              tabIndex={0}
            >
              <div className="cabin__frame" ref={frameRef}>
                <div className="cabin__stack" ref={stackRef}>
                  {SPECS.map((sp, i) => (
                    <div
                      key={sp.key}
                      className="cabin__layer"
                      ref={(el) => {
                        layerRefs.current[i] = el
                      }}
                      aria-hidden={i === active ? undefined : true}
                    >
                      <img
                        className="cabin__img"
                        src={sp.src}
                        srcSet={srcSet(sp.src)}
                        sizes="(min-width: 1180px) 46vw, 100vw"
                        style={{ objectPosition: sp.pos }}
                        alt={i === active ? sp.alt : ''}
                        loading={i === 0 ? 'eager' : 'lazy'}
                        decoding="async"
                      />
                    </div>
                  ))}
                </div>
                <span className="cabin__grade" aria-hidden="true" />
              </div>
              <CabinDraft compassRef={compassRef} />
              <p className="cabin__note" aria-hidden="true">
                Every detail specified.
                <br />
                Every space respected.
              </p>
            </div>

            <ol className="cabin__dots" ref={dotsRef} aria-hidden="true">
              {SPECS.map((sp, i) => (
                <li key={sp.key} className={i === active ? 'is-on' : ''} />
              ))}
            </ol>
          </div>
        </div>
        <div className="cabin__runway" aria-hidden="true" />
      </div>
    </section>
  )
}
