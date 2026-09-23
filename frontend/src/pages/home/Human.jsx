import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow, PILLAR_ICONS, Shield } from '@/components/icons'
import { gsap } from '@/lib/gsap'
import { useReducedMotion, useScrollProgress } from '@/lib/hooks'

import { RiseIn, Scrub } from '../lift/shared'

/* ==========================================================================
   13 · AFTER THE INSTALLATION
   The deliberate tonal shift: technical to human.

   Five services, so a five-sided column: a prism of photographs standing in
   the dark, one service to a face. Scrolling turns it a face at a time — it
   holds square on each, then swings to the next — while the names run past
   behind it in outline, a line of type the column is turning through. The
   pointer leans it a few degrees; a click on a face seen edge-on brings it
   round.

   One number drives it: `cur`, the face in hand, read from the section's own
   rectangle every frame.
   ========================================================================== */

const clamp01 = (v) => Math.max(0, Math.min(1, v))
const pad2 = (n) => String(n).padStart(2, '0')
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
const TURN_DWELL = 0.52

const SERVICE_FRAMES = {
  'service-24-7': { src: '/media/frames/lacheta-cop.jpg', alt: 'A hand on the car operating panel' },
  amc: { src: '/media/process/process-structure.jpg', alt: 'Guide rails running up a lift shaft' },
  breakdown: { src: '/media/frames/owaisi-waiting.jpg', alt: 'A hospital lift lobby in use' },
  modernisation: { src: '/media/process/process-blueprint.jpg', alt: 'A dimensioned lift shaft drawing' },
  spares: { src: '/media/frames/lacheta-indicator.jpg', alt: 'A landing indicator set into marble' },
}
const SERVICE_FALLBACK = { src: '/media/frames/lekha-inuse.jpg', alt: '' }

export function AfterInstall({ pillars = [] }) {
  const reduced = useReducedMotion()
  const sec = useRef(null)
  const [active, setActive] = useState(0)
  const n = pillars.length
  const step = n ? 360 / n : 0

  useEffect(() => {
    const el = sec.current
    if (!el || !n) return undefined
    const ring = el.querySelector('.sp-ring')
    const faces = [...el.querySelectorAll('.sp-face')]
    const band = el.querySelector('.sp-band__run')
    const stage = el.querySelector('.sp-stage')
    let cur = 0
    let last = -1
    let act = 0
    let lean = 0
    let leanTo = 0

    const onMove = (e) => {
      leanTo = ((e.clientX / window.innerWidth) * 2 - 1) * -7
    }
    if (!reduced) window.addEventListener('pointermove', onMove, { passive: true })

    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh || r.top > vh * 2) return
      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      const seg = Math.min(n - 1e-6, p * n)
      const i = Math.floor(seg)
      const f = seg - i
      const pos = i + (i < n - 1 ? easeInOut(clamp01((f - TURN_DWELL) / (1 - TURN_DWELL))) : 0)
      cur = reduced ? pos : cur + (pos - cur) * 0.1
      lean += (leanTo - lean) * 0.06
      const key = cur + lean * 0.001
      if (Math.abs(key - last) < 0.00005) return
      last = key
      ring.style.transform = `translateZ(calc(var(--apo) * -1)) rotateY(${(-cur * step + lean).toFixed(3)}deg)`
      faces.forEach((face, k) => {
        // how square-on this face is: 1 facing us, 0 edge-on or behind
        let d = Math.abs(k - cur) % n
        if (d > n / 2) d = n - d
        face.style.setProperty('--f', Math.max(0, Math.cos((d * step * Math.PI) / 180)).toFixed(4))
      })
      if (band) {
        const travel = Math.max(0, band.scrollWidth - stage.clientWidth * 0.6)
        band.style.transform = `translate3d(${(-(cur / Math.max(1, n - 1)) * travel).toFixed(1)}px, 0, 0)`
      }
      const a = Math.round(cur)
      if (a !== act) {
        act = a
        setActive(a)
      }
    }
    gsap.ticker.add(tick)
    return () => {
      gsap.ticker.remove(tick)
      window.removeEventListener('pointermove', onMove)
    }
  }, [n, step, reduced])

  const go = (i) => {
    const el = sec.current
    if (!el) return
    const k = Math.max(0, Math.min(n - 1, i))
    const runway = el.offsetHeight - window.innerHeight
    const y = el.getBoundingClientRect().top + window.scrollY + ((k + 0.2) / n) * runway
    if (window.__lenis && !reduced) window.__lenis.scrollTo(y, { duration: 1.1 })
    else window.scrollTo({ top: y, behavior: reduced ? 'auto' : 'smooth' })
  }

  const cur = pillars[Math.min(active, Math.max(0, n - 1))]
  const Icon = cur ? (PILLAR_ICONS[cur.icon] ?? Shield) : Shield

  return (
    <div className="sp">
      <div className="sp__head">
        <div>
          <p className="sp__eyebrow">After the installation</p>
          <Scrub as="h2" className="sp__title" text="Our work doesn’t end when the doors open." span={0.3} />
        </div>
        <div className="sp__intro">
          <p className="sp__lead">
            A lift runs for twenty to twenty-five years before it needs modernising. Most of its life happens after
            the handover, which is the part a maintenance contract is actually for.
          </p>
          <Link to="/service" className="btn btn--accent btn--sm">
            Request service <Arrow size={14} />
          </Link>
        </div>
      </div>

      {n > 0 && (
        <section ref={sec} className="sp-run" style={{ '--n': n, '--step': `${step}deg` }} aria-label="What we do after handover">
          <div className="sp-stage">
            <div className="sp-band" aria-hidden="true">
              <p className="sp-band__run">
                {pillars.map((p) => (
                  <span key={p.slug}>{p.name}</span>
                ))}
              </p>
            </div>

            <div className="sp-scene">
              <div className="sp-ring">
                {pillars.map((p, i) => {
                  const frame = SERVICE_FRAMES[p.slug] ?? SERVICE_FALLBACK
                  return (
                    <button
                      type="button"
                      key={p.slug}
                      className={`sp-face ${i === active ? 'is-on' : ''}`}
                      style={{ '--i': i }}
                      tabIndex={i === active ? 0 : -1}
                      aria-label={`${pad2(i + 1)} — ${p.name}`}
                      onClick={() => go(i)}
                    >
                      <Img src={frame.src} alt={frame.alt} sizes="(min-width: 900px) 30vw, 66vw" />
                      <span className="sp-face__n">{pad2(i + 1)}</span>
                      <span className="sp-face__name">{p.name}</span>
                    </button>
                  )
                })}
              </div>
              <span className="sp-floor" aria-hidden="true" />
            </div>

            {cur && (
              <div className="sp-acct" key={cur.slug}>
                <p className="sp-acct__n">
                  <Icon className="sp-acct__icon" />
                  <span>
                    {pad2(active + 1)} / {pad2(n)}
                  </span>
                </p>
                <h3 className="sp-acct__name">{cur.name}</h3>
                <p className="sp-acct__desc">{cur.description}</p>
                {cur.detail && <p className="sp-acct__detail">{cur.detail}</p>}
              </div>
            )}

            <div className="sp-foot">
              <button type="button" className="sp-step sp-step--prev" onClick={() => go(active - 1)} disabled={active === 0} aria-label="Previous service">
                <Arrow size={15} />
              </button>
              <ol className="sp-dots" aria-hidden="true">
                {pillars.map((p, i) => (
                  <li key={p.slug} className={i === active ? 'is-on' : ''} />
                ))}
              </ol>
              <button type="button" className="sp-step" onClick={() => go(active + 1)} disabled={active === n - 1} aria-label="Next service">
                <Arrow size={15} />
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

/* ==========================================================================
   14 · THE PEOPLE
   Four crews in the order a lift meets them, so the section reads the way a
   job runs: left to right. The stage holds while the scroll carries one long
   strip across it — the headline first, then a large photograph for each crew.
   Everything on the strip moves at its own speed: the photograph drifts inside
   its frame, and the crew's name, set across the frame's edge, slides against
   it. A line along the foot fills as the job goes from survey to service.
   ========================================================================== */

export function People({ team = [] }) {
  // the strip measures itself from mount, so it only mounts once there is one
  return team.length ? <Crews team={team} /> : null
}

function Crews({ team }) {
  const reduced = useReducedMotion()
  const sec = useRef(null)
  const n = team.length

  useEffect(() => {
    const el = sec.current
    if (!el || reduced) return undefined
    const track = el.querySelector('.fs-track')
    const slides = [...el.querySelectorAll('.fs-slide')]
    const fill = el.querySelector('.fs-line__fill')
    let cur = 0
    let last = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      const vw = window.innerWidth
      if (r.bottom < -vh || r.top > vh * 2) return
      const p = clamp01(-r.top / Math.max(1, r.height - vh))
      cur += (p - cur) * 0.12
      if (Math.abs(cur - last) < 0.0003) return
      last = cur
      const travel = Math.max(0, track.scrollWidth - vw)
      track.style.transform = `translate3d(${(-cur * travel).toFixed(1)}px, 0, 0)`
      slides.forEach((slide) => {
        const b = slide.getBoundingClientRect()
        // −1 coming in from the right, 0 in the middle of the screen, 1 leaving
        const sx = Math.max(-1.4, Math.min(1.4, (vw / 2 - (b.left + b.width / 2)) / vw))
        slide.style.setProperty('--sx', sx.toFixed(4))
      })
      if (fill) fill.style.transform = `scaleX(${cur.toFixed(4)})`
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced, n])

  return (
    <section ref={sec} className="on-paper fs" style={{ '--n': n }} aria-label="The people">
      <div className="fs-stage">
        <div className="fs-track">
          <div className="fs-intro">
            <p className="fs__eyebrow">The people</p>
            <RiseIn as="h2" className="fs__title" text="Engineered by people. Built for people." />
            <p className="fs__lead">
              Every lift passes through four crews — before it carries anyone, and for as long as it does.
            </p>
            <p className="fs__cue" aria-hidden="true">
              <span>Keep scrolling</span>
              <Arrow size={14} />
            </p>
          </div>

          {team.map((m, i) => (
            <article className="fs-slide" key={m.id}>
              <div className="fs-slide__frame">
                <Img src={m.photo} alt="" sizes="(min-width: 900px) 46vw, 80vw" />
              </div>
              <p className="fs-slide__ghost" aria-hidden="true">
                {m.name}
              </p>
              <div className="fs-slide__copy">
                <p className="fs-slide__role">
                  {pad2(i + 1)} · {m.role}
                </p>
                <h3 className="fs-slide__name">{m.name}</h3>
                {m.bio && <p className="fs-slide__bio">{m.bio}</p>}
              </div>
            </article>
          ))}
        </div>

        <div className="fs-line" aria-hidden="true">
          <span className="fs-line__fill" />
          <ol className="fs-line__stops">
            {team.map((m) => (
              <li key={m.id}>{m.name}</li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   15 · IN THEIR WORDS
   A carousel that runs itself. One client's card holds the middle of the
   stage — the photograph of their lift on one side, what they said on the
   other — with the next and the last standing either side of it, turned away
   and dimmed. Every few seconds the row slides on by one. The line under the
   counter is the clock; a pointer resting on the row stops it, and the arrows,
   the dots, a swipe or the arrow keys move it by hand.

   The row is a ring: each card is placed by its distance from the one in hand,
   wrapped, so it runs on past the last client back to the first.
   ========================================================================== */

const VOICE_FRAMES = {
  'niloufer-cafe': '/media/frames/niloufer-cabin.jpg',
  'lekha-nilayam': '/media/frames/lekha-hall.jpg',
  'owaisi-hospitals': '/media/frames/owaisi-lobby.jpg',
  'kashi-yadhav-residence': '/media/frames/kashi-cabin.jpg',
  'chath-restaurant': '/media/frames/chath-facade.jpg',
}
const VOICE_HOLD = 5500

export function Voices({ testimonials = [] }) {
  const reduced = useReducedMotion()
  const sec = useRef(null)
  const swipe = useRef(null)
  const [active, setActive] = useState(0)
  const [onScreen, setOnScreen] = useState(false)
  const [hover, setHover] = useState(false)
  const n = testimonials.length

  useEffect(() => {
    const el = sec.current
    if (!el) return undefined
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting), { threshold: 0.3 })
    io.observe(el)
    return () => io.disconnect()
  }, [n])

  const playing = onScreen && !hover && !reduced && n > 1
  useEffect(() => {
    if (!playing) return undefined
    const t = setTimeout(() => setActive((i) => (i + 1) % n), VOICE_HOLD)
    return () => clearTimeout(t)
  }, [playing, active, n])

  if (!n) return null

  const go = (i) => setActive(((i % n) + n) % n)
  const onKey = (e) => {
    if (e.key === 'ArrowRight') go(active + 1)
    else if (e.key === 'ArrowLeft') go(active - 1)
  }

  return (
    <section ref={sec} className={`tc ${playing ? 'is-playing' : ''}`} aria-label="Clients, in their words">
      <div className="tc__head">
        <div>
          <p className="tc__eyebrow">Clients</p>
          <RiseIn as="h2" className="tc__title" text="In their words." />
        </div>
        <div className="tc__nav">
          <p className="tc__count" aria-live="polite">
            <strong>{pad2(active + 1)}</strong>
            <span className="tc__clock" style={{ '--hold': `${VOICE_HOLD}ms` }} aria-hidden="true">
              <span key={active} />
            </span>
            <span>{pad2(n)}</span>
          </p>
          <button type="button" className="tc__step tc__step--prev" onClick={() => go(active - 1)} aria-label="Previous client">
            <Arrow size={15} />
          </button>
          <button type="button" className="tc__step" onClick={() => go(active + 1)} aria-label="Next client">
            <Arrow size={15} />
          </button>
        </div>
      </div>

      <div
        className="tc__stage"
        role="group"
        aria-roledescription="carousel"
        tabIndex={0}
        onKeyDown={onKey}
        onPointerEnter={(e) => e.pointerType === 'mouse' && setHover(true)}
        onPointerLeave={() => setHover(false)}
        onPointerDown={(e) => {
          swipe.current = { x: e.clientX, y: e.clientY }
        }}
        onPointerUp={(e) => {
          const st = swipe.current
          swipe.current = null
          if (!st) return
          const dx = e.clientX - st.x
          if (Math.abs(dx) > 44 && Math.abs(e.clientY - st.y) < 80) go(active + (dx < 0 ? 1 : -1))
        }}
      >
        {testimonials.map((t, i) => {
          // distance from the card in hand, the short way round the ring
          let d = i - active
          if (d > n / 2) d -= n
          if (d < -n / 2) d += n
          const on = d === 0
          const words = t.quote.split(' ')
          return (
            <figure
              key={t.id}
              className={`tc-card ${on ? 'is-on' : ''}`}
              style={{ '--d': d, '--a': Math.abs(d) }}
              aria-hidden={!on}
              onClick={() => !on && go(i)}
            >
              <div className="tc-card__media">
                <Img src={VOICE_FRAMES[t.project_slug] || t.poster_url} alt="" sizes="(min-width: 900px) 26vw, 84vw" />
              </div>
              <div className="tc-card__copy">
                <span className="tc-card__mark" aria-hidden="true">
                  “
                </span>
                <blockquote className="tc-card__quote" key={on ? `on-${active}` : 'off'}>
                  {words.map((w, k) => (
                    <span className="tc-w" key={k}>
                      <span style={{ '--i': k }}>{w}</span>{' '}
                    </span>
                  ))}
                </blockquote>
                <figcaption className="tc-card__by">
                  <strong>{t.organisation || t.name}</strong>
                  <span>
                    {t.role}
                    {t.location ? ` · ${t.location}` : ''}
                  </span>
                  {t.project_slug && (
                    <Link to={`/projects/${t.project_slug}`} className="tc-card__link" tabIndex={on ? 0 : -1}>
                      View the project <Arrow size={13} />
                    </Link>
                  )}
                </figcaption>
              </div>
            </figure>
          )
        })}
      </div>

      <ol className="tc__dots">
        {testimonials.map((t, i) => (
          <li key={t.id}>
            <button
              type="button"
              className={`tc__dot ${i === active ? 'is-on' : ''}`}
              onClick={() => go(i)}
              aria-label={`${t.organisation || t.name}`}
              aria-current={i === active ? 'true' : undefined}
            />
          </li>
        ))}
      </ol>
    </section>
  )
}

/* ==========================================================================
   16 · FINAL ASCENT
   Loops back to the hero cabin: doors close, the floors climb, the doors open
   onto a skyline.
   ========================================================================== */

const CLIMB = ['12', '17', '23', '28', '31', '34', '36']

export function FinalAscent() {
  const [ref, progress] = useScrollProgress()
  // doors close over the first 40%, then open onto the skyline after 70%
  const close = Math.min(1, progress / 0.4)
  const reveal = Math.max(0, Math.min(1, (progress - 0.68) / 0.3))
  const shut = Math.max(0, close - reveal * 1.6)
  const floor = CLIMB[Math.min(CLIMB.length - 1, Math.floor(progress * CLIMB.length))]

  return (
    <section ref={ref} className="section section--flush ascent" aria-labelledby="ascent-title">
      <div className="ascent__pin">
        <div className="ascent__stage">
          <div className="ascent__sky" style={{ opacity: 0.35 + reveal * 0.65 }}>
            <Img src="/media/sourced/skyline-hyderabad.jpg" alt="" sizes="100vw" />
          </div>

          <div className="ascent__doors" aria-hidden="true" style={{ '--shut': shut }}>
            <div className="ascent__door ascent__door--l" />
            <div className="ascent__door ascent__door--r" />
          </div>

          <div className="ascent__ticker" aria-hidden="true">
            <span>&uarr;</span>
            <span className="ascent__floor">{floor}</span>
          </div>

          <div className="shell ascent__content" style={{ opacity: reveal }}>
            <p className="eyebrow">
              Final ascent
            </p>
            <h2 className="display ascent__title" id="ascent-title">
              Where should
              <br />
              we take you?
            </h2>
            <div className="ascent__actions">
              <Link to="/contact" className="btn btn--accent">
                Get a quote <Arrow />
              </Link>
              <Link to="/contact#visit" className="btn btn--ghost">
                Arrange a visit <Arrow />
              </Link>
            </div>
          </div>
        </div>
      </div>
      <div className="ascent__runway" aria-hidden="true" />
    </section>
  )
}
