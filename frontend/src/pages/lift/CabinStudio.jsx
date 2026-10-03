import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal from '@/components/Reveal'
import { Arrow, CardMark, Check, FingerprintMark, IntercomMark, Lock, SignalMark } from '@/components/icons'
import { HelpMark } from '@/components/place-marks'
import { gsap } from '@/lib/gsap'
import { useMediaQuery, useReducedMotion } from '@/lib/hooks'

import { DEFAULTS, GROUPS, plateFor } from '../home/Machine'
import { RiseIn, useScrollVar } from './shared'
import './cabin-studio.css'

/* ==========================================================================
   The cabin — five decisions, held like a hand of cards
   Each decision is a tall plate showing the render of whatever is chosen for
   it. The five stand in perspective: the one being decided comes forward, the
   rest angle away behind it. The scroll deals them out from a single stack,
   the pointer tips the whole hand, and choosing a finish sends the new render
   up its plate the way a car arrives at a landing.

   No 3D library — the depth is CSS perspective, the easing is GSAP's ticker.
   ========================================================================== */

const pad = (n) => String(n).padStart(2, '0')

/* "Not sure yet" is a real answer to every decision, and travels with the
   enquiry as one — choosing is part of what Zion does. */
const UNSURE = { slug: 'unsure', name: 'Not sure yet', description: "We'll suggest one", unsure: true }

/** what any operating panel can be fitted with, whichever one is chosen */
const PANEL_FEATURES = [
  [Lock, 'Password access'],
  [SignalMark, 'GSM auto-dialler'],
  [CardMark, 'RFID card access'],
  [FingerprintMark, 'Biometric access'],
  [IntercomMark, 'Intercom'],
]

/** the render a choice puts on its plate; "not sure" shows what it is between */
const shotFor = (key, option) => (option.unsure ? `unsure:${key}` : plateFor(key, option.slug))

/** the "not sure" plate: the decision's own options side by side, and a question mark */
function UnsureShot({ group }) {
  const picks = group.options.filter((o) => !o.unsure).slice(0, 4)
  return (
    <span className="cs__unsure">
      <span className="cs__unsure-grid">
        {picks.map((o) => (
          <span key={o.slug}>
            <Img src={plateFor(group.key, o.slug)} alt="" sizes="(min-width: 900px) 12vw, 31vw" objectPosition={group.pos} />
          </span>
        ))}
      </span>
      <span className="cs__unsure-mark" aria-hidden="true">
        <HelpMark size={30} />
      </span>
      <span className="cs__unsure-note">We'll suggest one</span>
    </span>
  )
}

export default function CabinStudio({ lift, finishes }) {
  const groups = useMemo(
    () =>
      GROUPS.map((g) => ({ ...g, options: (finishes ?? []).filter((f) => f.category === g.key) }))
        .filter((g) => g.options.length)
        .map((g) => ({ ...g, options: [...g.options, UNSURE] })),
    [finishes],
  )

  const sec = useRef(null)
  const deck = useRef(null)
  const swipe = useRef(null)
  const reduced = useReducedMotion()
  const fine = useMediaQuery('(hover: hover) and (pointer: fine)')
  const [active, setActive] = useState(1)
  const [choice, setChoice] = useState({})
  // every render a plate has shown stays mounted, so a change crossfades instead of flashing
  const [seen, setSeen] = useState({})

  useScrollVar(sec, { from: 0.85, to: 0.1 })

  const chosen = (g) =>
    g.options.find((o) => o.slug === choice[g.key]) ?? g.options.find((o) => o.slug === DEFAULTS[g.key]) ?? g.options[0]

  // the pointer tips the hand: a few degrees, eased, and level again when it leaves
  useEffect(() => {
    if (!fine || reduced || !deck.current) return undefined
    const el = deck.current
    const rx = gsap.quickTo(el, '--tx', { duration: 0.9, ease: 'power3.out' })
    const ry = gsap.quickTo(el, '--ty', { duration: 0.9, ease: 'power3.out' })
    const move = (e) => {
      const r = el.getBoundingClientRect()
      ry(((e.clientX - r.left) / r.width - 0.5) * 9)
      rx(((e.clientY - r.top) / r.height - 0.5) * -6)
    }
    const leave = () => {
      rx(0)
      ry(0)
    }
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerleave', leave)
    return () => {
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerleave', leave)
    }
  }, [fine, reduced, groups.length])

  if (!groups.length) return null

  const at = Math.min(active, groups.length - 1)
  const current = groups[at]
  const step = (d) => setActive((i) => Math.max(0, Math.min(groups.length - 1, i + d)))

  const pick = (g, o) => {
    setSeen((old) => {
      const was = old[g.key] ?? [shotFor(g.key, chosen(g))]
      const src = shotFor(g.key, o)
      return { ...old, [g.key]: was.includes(src) ? was : [...was, src] }
    })
    setChoice((c) => ({ ...c, [g.key]: o.slug }))
  }

  const enquiryHref = `/contact?${new URLSearchParams({
    config: groups.map((g) => `${g.key}=${chosen(g)?.slug ?? ''}`).join(','),
    ...(lift?.slug ? { lift: lift.slug } : {}),
  })}`

  const onKey = (e) => {
    if (e.key === 'ArrowRight') step(1)
    else if (e.key === 'ArrowLeft') step(-1)
    else return
    e.preventDefault()
  }

  // a sideways drag on the hand moves to the next decision
  const onDown = (e) => {
    swipe.current = { x: e.clientX, y: e.clientY }
  }
  const onUp = (e) => {
    const s = swipe.current
    swipe.current = null
    if (!s) return
    const dx = e.clientX - s.x
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(e.clientY - s.y) * 1.4) step(dx < 0 ? 1 : -1)
  }

  return (
    <section ref={sec} className="cs" id="configure">
      <div className="cs__glow" aria-hidden="true" />

      <header className="cs__head">
        <Reveal variant="fade">
          <p className="ld-label">The cabin</p>
        </Reveal>
        <RiseIn
          as="h2"
          className="cs__title"
          text={lift ? `Finish the ${lift.short_name} your way.` : 'Finish the cabin your way.'}
        />
        <Reveal delay={120}>
          <p className="cs__lead">
            Five decisions — ceiling, walls, floor, panel and doors. Not sure about one? Say so, and we will
            suggest it. Whatever you land on travels with your enquiry.
          </p>
        </Reveal>
      </header>

      <div
        ref={deck}
        className="cs__deck"
        style={{ '--n': groups.length }}
        onPointerDown={onDown}
        onPointerUp={onUp}
        onPointerCancel={() => (swipe.current = null)}
      >
        <div className="cs__hand">
          {groups.map((g, i) => {
            const sel = chosen(g)
            const now = shotFor(g.key, sel)
            const plates = seen[g.key] ?? [now]
            const d = i - at
            const Mark = g.icon
            return (
              <button
                key={g.key}
                type="button"
                className={`cs__plate ${d === 0 ? 'is-on' : ''}`}
                style={{ '--d': d, '--a': Math.abs(d), zIndex: 10 - Math.abs(d) }}
                onClick={() => setActive(i)}
                aria-pressed={d === 0}
                aria-label={`${g.label}: ${sel.name}`}
              >
                <span className="cs__plate-in">
                  {plates.map((src) => (
                    <span key={src} className={`cs__shot ${src === now ? 'is-on' : ''}`}>
                      {src.startsWith('unsure:') ? (
                        <UnsureShot group={g} />
                      ) : (
                        <Img src={src} alt="" sizes="(min-width: 900px) 24vw, 62vw" objectPosition={g.pos} />
                      )}
                    </span>
                  ))}
                  <span className="cs__sheen" key={now} aria-hidden="true" />
                  <span className="cs__plate-top">
                    <span>{pad(i + 1)}</span>
                    <Mark size={18} aria-hidden="true" />
                  </span>
                  <span className="cs__plate-foot">
                    <em>{g.label}</em>
                    <strong key={sel.slug}>{sel.name}</strong>
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="cs__controls">
        <div className="cs__tabs" role="tablist" aria-label="Cabin decisions" onKeyDown={onKey}>
          {groups.map((g, i) => {
            const Mark = g.icon
            const on = i === at
            return (
              <button
                key={g.key}
                type="button"
                role="tab"
                id={`cs-tab-${g.key}`}
                aria-selected={on}
                aria-controls="cs-panel"
                tabIndex={on ? 0 : -1}
                className={`cs__tab ${on ? 'is-on' : ''}`}
                onClick={() => setActive(i)}
              >
                <Mark size={20} aria-hidden="true" />
                <span>{g.nav.join(' ')}</span>
              </button>
            )
          })}
        </div>

        <div className="cs__panel" role="tabpanel" id="cs-panel" aria-labelledby={`cs-tab-${current.key}`} key={current.key}>
          <div className="cs__opts">
            {current.options.map((o, i) => {
              const on = chosen(current).slug === o.slug
              return (
                <button
                  key={o.slug}
                  type="button"
                  className={`cs__opt ${on ? 'is-on' : ''} ${o.unsure ? 'is-unsure' : ''}`}
                  style={{ '--i': i }}
                  onClick={() => pick(current, o)}
                  aria-pressed={on}
                  title={o.description}
                >
                  <span
                    className="cs__swatch"
                    style={
                      o.unsure
                        ? undefined
                        : { background: `linear-gradient(142deg, ${o.swatch_hex}, ${o.swatch_hex_2 || o.swatch_hex})` }
                    }
                    aria-hidden="true"
                  >
                    {on ? <Check size={13} /> : o.unsure && <HelpMark size={20} />}
                  </span>
                  <span className="cs__opt-name">{o.name}</span>
                  {o.tier && o.tier !== 'standard' && <span className="cs__tier">{o.tier}</span>}
                </button>
              )
            })}
          </div>

          {current.key === 'control' && (
            <div className="cs__feats">
              <p className="cs__feats-title">Any panel can also carry</p>
              <ul>
                {PANEL_FEATURES.map(([Icon, label]) => (
                  <li key={label}>
                    <Icon size={18} aria-hidden="true" />
                    {label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="cs__bar">
          <ul className="cs__spec" aria-live="polite">
            {groups.map((g, i) => (
              <li key={g.key} className={i === at ? 'is-on' : ''}>
                <span>{g.label}</span>
                <strong key={chosen(g).slug}>{chosen(g).name}</strong>
              </li>
            ))}
          </ul>
          <Link to={enquiryHref} className="cs__cta">
            <span>Request this design</span>
            <span className="cs__cta-ring">
              <Arrow size={16} />
            </span>
          </Link>
        </div>
      </div>
    </section>
  )
}
