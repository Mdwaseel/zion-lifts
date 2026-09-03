import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { Arrow, Box, CogMark, Pin, UpDownMark, UsersMark } from '@/components/icons'

/* ==========================================================================
   08 · OUR PROCESS — four stages of one installation

   Four equal plates in a row, an arrow in each gap, and a caption
   under each. The cyan never jumps: one outline element is measured onto the
   active plate and translated to the next, so the active state physically
   travels the row. It is measured from rects rather than computed from column
   maths, which means the same element lands correctly on the 2x2 tablet grid
   and on the single stacked card of a phone without knowing about either.

   One timer drives the sequence, and it stops for any of four reasons: the
   section is off screen, the tab is hidden, the pointer is over the row, or
   somebody has just taken control.
   ========================================================================== */

const STAGES = [
  {
    n: '01',
    label: 'Blueprint',
    line: 'Every detail is considered before a single component is built.',
    src: '/media/process/process-blueprint.jpg',
    alt: 'Technical elevator shaft blueprint, dimensioned across four levels',
  },
  {
    n: '02',
    label: 'Structure',
    line: 'Rails, frame and machine installed with precision. The foundation takes shape.',
    src: '/media/process/process-structure.jpg',
    alt: 'Elevator shaft during structural installation, guide rails fixed to the concrete',
  },
  {
    n: '03',
    label: 'The finished lift',
    line: 'Finishes fitted, systems tested, safety assured. Ready for seamless performance.',
    src: '/media/process/process-finished.jpg',
    alt: 'Completed luxury elevator interior in walnut with a brass handrail',
  },
  {
    n: '04',
    label: 'In the building',
    line: 'The same lift, in daily use, becoming a natural part of the architecture.',
    src: '/media/process/process-building.jpg',
    alt: 'The completed elevator integrated into a building interior beside a seating area',
  },
]

const HOLD = 2400
const TRAVEL = 620
const RESUME = 7000
const LAST = STAGES.length - 1

export function Blueprint() {
  const [active, setActive] = useState(0)
  const [box, setBox] = useState(null)
  const [onScreen, setOnScreen] = useState(false)
  const [awake, setAwake] = useState(true)
  const [taken, setTaken] = useState(false)

  const sectionRef = useRef(null)
  const rowRef = useRef(null)
  const plateEls = useRef([])
  const swipeRef = useRef(null)

  /* Neither hovering nor a reduced-motion preference stops the sequence.
     Hovering used to, but the plates cover most of the row, so a cursor left
     resting anywhere over the section froze it. Reduced motion used to as
     well, which left the whole section looking broken for anyone with Windows
     "Animation effects" off — there, the stylesheet strips the travel and the
     slide instead, so the stages still advance and simply do not animate.
     Only a real interaction hands control over, and only for RESUME. */
  const playing = onScreen && awake && !taken

  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    // deliberately loose: the section is taller than a laptop viewport, and a
    // high threshold means it stops whenever it is only half on screen
    const io = new IntersectionObserver((es) => setOnScreen(es[0].isIntersecting), {
      threshold: 0.02,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    const onVis = () => setAwake(!document.hidden)
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  useEffect(() => {
    if (!playing) return
    const t = setTimeout(() => setActive((i) => (i + 1) % STAGES.length), HOLD + TRAVEL)
    return () => clearTimeout(t)
  }, [playing, active])

  // control comes back after a pause, and the sequence carries on from wherever
  // it was left rather than restarting at 01
  useEffect(() => {
    if (!taken) return
    const t = setTimeout(() => setTaken(false), RESUME)
    return () => clearTimeout(t)
  }, [taken, active])

  /* Rects, not offsetLeft: the plate's offset parent is its own wrapper, so an
     offset read would be relative to the wrong box on every card. */
  useLayoutEffect(() => {
    const wrap = rowRef.current
    const el = plateEls.current[active]
    if (!wrap || !el) return
    const measure = () => {
      const a = el.getBoundingClientRect()
      const b = wrap.getBoundingClientRect()
      setBox({ x: a.left - b.left, y: a.top - b.top, w: a.width, h: a.height })
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(wrap)
    return () => ro.disconnect()
  }, [active])

  const go = (i) => {
    setActive(((i % STAGES.length) + STAGES.length) % STAGES.length)
    setTaken(true)
  }

  const onKey = (e) => {
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    e.preventDefault()
    const n = (active + step + STAGES.length) % STAGES.length
    go(n)
    sectionRef.current?.querySelector(`#proc-plate-${n}`)?.focus()
  }

  const onDown = (e) => {
    swipeRef.current = { x: e.clientX, y: e.clientY }
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }
  const onUp = (e) => {
    const s = swipeRef.current
    swipeRef.current = null
    if (!s) return
    const dx = e.clientX - s.x
    if (Math.abs(dx) < 48 || Math.abs(e.clientY - s.y) > 64) return
    go(active + (dx < 0 ? 1 : -1))
  }

  return (
    <section
      className="section process"
      aria-labelledby="process-title"
      ref={sectionRef}
      style={{ '--proc-travel': `${TRAVEL}ms`, '--proc-step': `${HOLD + TRAVEL}ms` }}
    >
      <div className="proc__ground" aria-hidden="true" />

      <div className="shell proc__shell">
        <header className="proc__head">
          <Reveal variant="fade">
            <p className="proc__eyebrow">Our process</p>
            <h2 className="proc__title" id="process-title">
              <span>From a concept</span>
              <span>
                to <em>everyday</em> use<span className="proc__stop">.</span>
              </span>
            </h2>
          </Reveal>
          <Reveal className="proc__intro" variant="fade" delay={120}>
            <p>Four stages of one installation.</p>
            <p>Thoughtfully planned. Precisely built.</p>
            <p>Perfectly integrated.</p>
          </Reveal>
        </header>

        <Reveal className="proc__run" variant="fade" delay={180}>
          <div className="proc__row" ref={rowRef}>
            {STAGES.map((s, i) => (
              <article
                key={s.n}
                className={`proc__card ${i === active ? 'is-on' : ''} ${i < active ? 'is-done' : ''}`}
              >
                <div className="proc__plate-wrap">
                  <button
                    type="button"
                    id={`proc-plate-${i}`}
                    ref={(el) => {
                      plateEls.current[i] = el
                    }}
                    className="proc__plate"
                    aria-pressed={i === active}
                    onClick={() => go(i)}
                    onKeyDown={onKey}
                    onPointerDown={onDown}
                    onPointerUp={onUp}
                    onPointerCancel={() => (swipeRef.current = null)}
                  >
                    <Img
                      src={s.src}
                      alt={s.alt}
                      priority={i === 0}
                      sizes="(min-width: 1200px) 24vw, (min-width: 768px) 44vw, 88vw"
                    />
                    <span className="proc__plate-name">
                      Stage {s.n}, {s.label}
                    </span>
                  </button>

                  {/* the arrow sits in the gap before its own card, and is cyan
                      only where the journey is heading next */}
                  {i > 0 && (
                    <button
                      type="button"
                      className={`proc__arrow ${i === active + 1 ? 'is-on' : ''}`}
                      aria-label={`Go to stage ${s.n}, ${s.label}`}
                      onClick={() => go(i)}
                    >
                      <Arrow size={15} />
                    </button>
                  )}
                </div>

                <div className="proc__meta">
                  <span className="proc__n">{s.n}</span>
                  <h3 className="proc__label">{s.label}</h3>
                  <p className="proc__line">{s.line}</p>
                </div>
              </article>
            ))}

            <span
              className="proc__outline"
              aria-hidden="true"
              style={
                box
                  ? {
                      width: `${box.w}px`,
                      height: `${box.h}px`,
                      transform: `translate3d(${box.x}px, ${box.y}px, 0)`,
                    }
                  : { opacity: 0 }
              }
            />
          </div>

          {/* the row's arrows only make sense while the four sit side by side */}
          <div className="proc__steps">
            <button
              type="button"
              className="proc__arrow proc__arrow--step"
              aria-label="Previous stage"
              onClick={() => go(active - 1)}
            >
              <Arrow size={15} className="proc__arrow-back" />
            </button>
            <p className="proc__count">
              <span className="proc__count-n">{STAGES[active].n}</span>
              <span aria-hidden="true"> / {STAGES[LAST].n}</span>
            </p>
            <button
              type="button"
              className="proc__arrow proc__arrow--step is-on"
              aria-label="Next stage"
              onClick={() => go(active + 1)}
            >
              <Arrow size={15} />
            </button>
          </div>
        </Reveal>

        <Reveal className="proc__foot" variant="fade" delay={240}>
          <Link to="/projects" className="proc__cta">
            <Box size={17} className="proc__cta-mark" />
            <span>Explore the full journey</span>
            <Arrow size={15} className="proc__cta-arrow" />
          </Link>
        </Reveal>
      </div>
    </section>
  )
}

/* ==========================================================================
   09 · CERTIFIED FOR YOUR SAFETY

   Five approval marks, one per bordered card. Nothing is drawn around a mark:
   the card is a hairline rectangle and the logo sits in it. The artwork is the
   real certificate file painted through a CSS mask, which is what lets five
   logos that arrive in three different inks read as one quiet row on black.
   ========================================================================== */

const CERTS = [
  { slug: 'tuv-sud', name: 'TÜV SÜD', sub: 'Certified', scale: 1.18 },
  { slug: 'ce', name: 'CE', sub: 'Certified' },
  { slug: 'iso', name: 'ISO 9001:2015', sub: 'Quality management' },
  { slug: 'en', name: 'EN 81-20', sub: 'Safety standard' },
  { slug: 'isi', name: 'IS 14665', sub: 'Compliant' },
]

export function Certifications() {
  return (
    <section className="section certs" aria-labelledby="certs-title">
      <div className="shell certs__shell">
        <Reveal variant="fade">
          <p className="certs__eyebrow">Tested. Certified. Trusted.</p>
        </Reveal>
        <Reveal delay={70}>
          <h2 className="certs__title" id="certs-title">
            Certified for your safety.
          </h2>
        </Reveal>
        <Reveal delay={140}>
          <p className="certs__lead">
            Every lift is tested to the highest global standards — because safety isn’t an option,
            it’s our promise.
          </p>
        </Reveal>

        <ul className="certs__row">
          {CERTS.map((c, i) => (
            <Reveal as="li" key={c.slug} className="certs__item" delay={200 + i * 70}>
              <div className="cert">
                <span className="cert__logo">
                  <span
                    className="cert__mark"
                    style={{
                      '--mark': `url(/media/certs/cert-${c.slug}.png)`,
                      '--mark-scale': c.scale ?? 1,
                    }}
                    aria-hidden="true"
                  />
                </span>
                <p className="cert__name">{c.name}</p>
                <p className="cert__sub">{c.sub}</p>
              </div>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  )
}

/* ==========================================================================
   11 · THE PROJECTS
   One card per project, every card the same component: the photograph as the
   ground, a grade over it, the facts in a fixed order. A scroll-snap track
   does the carousel — the browser handles swipe and momentum, the arrows and
   dots just ask it to scroll — so there is one source of truth for where you
   are: the track's own scroll position.
   ========================================================================== */

const CARD_META = [
  ['Location', 'location', Pin],
  ['System', 'system', CogMark],
  ['Capacity', 'capacity', UsersMark],
  ['Stops', 'stops', UpDownMark],
]

function ProjectCard({ project: p, index, count }) {
  return (
    <li className="pj" aria-label={`Project ${index + 1} of ${count}`}>
      <Link to={`/projects/${p.slug}`} className="pj__link" aria-label={`${p.name} — view case study`}>
        <div className="pj__media">
          <Img src={p.hero_image_url || p.poster_url} alt="" sizes="(min-width: 1200px) 48vw, (min-width: 640px) 66vw, 92vw" />
        </div>
        <div className="pj__grade" aria-hidden="true" />

        <div className="pj__body">
          {p.category?.name && <span className="pj__badge">{p.category.name}</span>}
          {p.year && <p className="pj__year">{p.year}</p>}
          <h3 className="pj__title">{p.name}</h3>
          <span className="pj__rule" aria-hidden="true" />
          {p.statement && <p className="pj__desc">{p.statement}</p>}

          <dl className="pj__meta">
            {CARD_META.map(([label, key, Icon]) => (
              <div className="pj__cell" key={key}>
                <dt className="pj__label">
                  <Icon size={13} aria-hidden="true" />
                  {label}
                </dt>
                <dd className="pj__value">{p[key] || '—'}</dd>
              </div>
            ))}
          </dl>

          <div className="pj__foot">
            <span className="pj__cta">View case study</span>
            <span className="pj__go" aria-hidden="true">
              <Arrow size={15} />
            </span>
          </div>
        </div>
      </Link>
    </li>
  )
}

export function ProjectsReel({ projects = [] }) {
  const list = projects.slice(0, 12)
  const count = list.length
  const trackRef = useRef(null)
  // a page is one card-width of travel; the counter, the line and the dots all
  // speak in pages, so on a desktop showing four cards there are four positions
  // for seven projects, and on a phone showing one there are seven
  const [index, setIndex] = useState(0)
  const [pages, setPages] = useState(count)
  const drag = useRef(null)
  const justDragged = useRef(false)

  const geometry = () => {
    const t = trackRef.current
    if (!t || !t.firstElementChild) return null
    const cs = getComputedStyle(t)
    const gap = parseFloat(cs.columnGap || '0')
    const step = t.firstElementChild.offsetWidth + gap
    const inner = t.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)
    const visible = Math.max(1, Math.round((inner + gap) / step))
    return { t, step, max: t.scrollWidth - t.clientWidth, pages: Math.max(1, count - visible + 1) }
  }

  const measure = useCallback(() => {
    const g = geometry()
    if (!g) return
    const atEnd = g.max > 0 && g.t.scrollLeft >= g.max - 2
    const i = atEnd ? g.pages - 1 : Math.round(g.t.scrollLeft / g.step)
    setPages(g.pages)
    setIndex(Math.max(0, Math.min(g.pages - 1, i)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count])

  useEffect(() => {
    const t = trackRef.current
    if (!t) return undefined
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(measure)
    }
    t.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', measure)
    measure()
    return () => {
      cancelAnimationFrame(raf)
      t.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', measure)
    }
  }, [measure])

  const goTo = (i) => {
    const g = geometry()
    if (!g) return
    const next = Math.max(0, Math.min(g.pages - 1, i))
    g.t.scrollTo({ left: Math.min(next * g.step, g.max), behavior: 'smooth' })
  }

  // Horizontal wheel — shift+wheel, or a sideways trackpad swipe — steps the
  // track one card. It has to be handled here: the page's smooth scroller
  // (Lenis) claims every wheel event on the window and spends it vertically,
  // so a nested scroll container never receives one. The event is stopped
  // before it reaches the window; a vertical wheel over the cards is left
  // alone so the page still scrolls. One gesture is one step: a trackpad
  // sends dozens of small deltas, so they are pooled and then held off until
  // the smooth scroll has settled.
  const wheel = useRef({ pool: 0, until: 0 })
  useEffect(() => {
    const t = trackRef.current
    if (!t) return undefined
    const onWheel = (e) => {
      const sideways = Math.abs(e.deltaX) > Math.abs(e.deltaY)
      if (!sideways && !e.shiftKey) return
      const delta = sideways ? e.deltaX : e.deltaY
      if (!delta) return
      const g = geometry()
      if (!g) return
      // at either end, let the page have the gesture
      if ((delta < 0 && g.t.scrollLeft <= 0) || (delta > 0 && g.t.scrollLeft >= g.max - 1)) return
      e.preventDefault()
      e.stopPropagation()
      const w = wheel.current
      const now = performance.now()
      if (now < w.until) return
      w.pool += delta
      if (Math.abs(w.pool) < 40) return
      const dir = w.pool > 0 ? 1 : -1
      w.pool = 0
      w.until = now + 650
      goTo(Math.round(g.t.scrollLeft / g.step) + dir)
    }
    t.addEventListener('wheel', onWheel, { passive: false })
    return () => t.removeEventListener('wheel', onWheel)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count])

  // mouse drag on desktop — touch already scrolls natively. Snap is lifted
  // for the duration so the track follows the hand, then put back so it
  // settles on a card.
  const onPointerDown = (e) => {
    if (e.pointerType !== 'mouse' || e.button !== 0) return
    const t = trackRef.current
    drag.current = { x: e.clientX, left: t.scrollLeft, moved: false }
    t.classList.add('is-dragging')
  }
  const onPointerMove = (e) => {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.x
    if (Math.abs(dx) > 4) d.moved = true
    trackRef.current.scrollLeft = d.left - dx
  }
  const endDrag = () => {
    const d = drag.current
    const t = trackRef.current
    if (!d || !t) return
    drag.current = null
    t.classList.remove('is-dragging')
    if (d.moved) {
      const g = geometry()
      if (g) goTo(Math.round(g.t.scrollLeft / g.step))
      // the click that follows this pointerup belongs to the drag, not the card
      justDragged.current = true
      setTimeout(() => {
        justDragged.current = false
      }, 0)
    }
  }
  const onClickCapture = (e) => {
    if (justDragged.current) {
      e.preventDefault()
      e.stopPropagation()
    }
  }

  if (!count) return null
  const atStart = index <= 0
  const atEnd = index >= pages - 1
  const pad = (n) => String(n).padStart(2, '0')

  return (
    <section className="section reel" aria-labelledby="reel-title">
      <div className="shell">
        <header className="reel__head">
          <div className="reel__intro">
            <Reveal variant="fade">
              <p className="reel__eyebrow">The projects</p>
              <span className="reel__eyebrow-rule" aria-hidden="true" />
            </Reveal>
            <Reveal delay={60}>
              <h2 className="reel__title" id="reel-title">
                Real buildings.
                <br />
                Real installations.
              </h2>
            </Reveal>
            <Reveal delay={130}>
              <p className="reel__lead">
                High-performance lift solutions,
                <br />
                engineered for real-world environments.
              </p>
            </Reveal>
          </div>

          <Reveal className="reel__nav" variant="fade" delay={180}>
            <div className="reel__count" aria-live="polite">
              <span className="reel__count-n">{pad(index + 1)}</span>
              <span className="reel__progress" aria-hidden="true">
                <span className="reel__progress-fill" style={{ transform: `scaleX(${(index + 1) / pages})` }} />
              </span>
              <span className="reel__count-of">{pad(pages)}</span>
            </div>
            <div className="reel__arrows">
              <button
                type="button"
                className="reel__arrow reel__arrow--prev"
                onClick={() => goTo(index - 1)}
                disabled={atStart}
                aria-label="Previous project"
              >
                <Arrow size={16} />
              </button>
              <button
                type="button"
                className="reel__arrow"
                onClick={() => goTo(index + 1)}
                disabled={atEnd}
                aria-label="Next project"
              >
                <Arrow size={16} />
              </button>
            </div>
          </Reveal>
        </header>
      </div>

      <div className="reel__viewport">
        <ul
          className="reel__track"
          ref={trackRef}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerLeave={endDrag}
          onPointerCancel={endDrag}
          onClickCapture={onClickCapture}
        >
          {list.map((p, i) => (
            <ProjectCard key={p.slug} project={p} index={i} count={count} />
          ))}
        </ul>
      </div>

      <div className="shell">
        <ol className="reel__dots" aria-label="Carousel position">
          {Array.from({ length: pages }, (_, i) => (
            <li key={i}>
              <button
                type="button"
                className={`reel__dot ${i === index ? 'is-on' : ''}`}
                onClick={() => goTo(i)}
                aria-label={`Position ${i + 1} of ${pages}`}
                aria-current={i === index ? 'true' : undefined}
              />
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

/* ==========================================================================
   12 · THE DETAILS
   Eight macro plates. The photography carries it; almost no motion.
   ========================================================================== */

const DETAILS = [
  { label: 'The door', src: '/media/frames/lekha-hall.jpg' },
  { label: 'The button', src: '/media/frames/lacheta-indicator.jpg' },
  { label: 'Brass', src: '/media/frames/lacheta-lobby.jpg' },
  { label: 'Glass', src: '/media/frames/kashi-shaft.jpg' },
  { label: 'Light', src: '/media/frames/lekha-ceiling.jpg' },
  { label: 'The floor', src: '/media/frames/kashi-floor.jpg' },
  { label: 'The handrail', src: '/media/frames/chath-cabin.jpg' },
  { label: 'The ceiling', src: '/media/frames/lacheta-ceiling.jpg' },
]

export function Details() {
  return (
    <section className="section on-paper details" aria-labelledby="details-title">
      <div className="shell">
        <div className="section-head section-head--split">
          <div>
            <Reveal variant="fade">
              <p className="eyebrow">The details</p>
            </Reveal>
            <Reveal delay={60}>
              <h2 className="h2" id="details-title" style={{ marginTop: '1.1rem' }}>
                Details make
                <br />
                the difference.
              </h2>
            </Reveal>
          </div>
          <Reveal delay={130}>
            <p className="body">
              The parts of a lift people actually touch: the button, the handrail, the sill you step
              over without looking. Everything else is engineering nobody should have to notice.
            </p>
          </Reveal>
        </div>

        <RevealGroup className="details__grid" step={70} variant="wipe">
          {DETAILS.map((d) => (
            <figure className="details__cell" key={d.label}>
              <Img
                src={d.src}
                alt={d.label}
                ratio="1 / 1"
                sizes="(min-width: 1000px) 23vw, (min-width: 620px) 46vw, 92vw"
              />
              <figcaption className="details__cap">{d.label}</figcaption>
            </figure>
          ))}
        </RevealGroup>
      </div>
    </section>
  )
}
