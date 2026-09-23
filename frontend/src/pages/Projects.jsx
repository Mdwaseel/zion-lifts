import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoPlayer } from '@/components/Media'
import { Arrow } from '@/components/icons'
import { useApi, useReducedMotion } from '@/lib/hooks'
import { gsap } from '@/lib/gsap'

import { Rise, RiseIn, clamp01, useScrollVar } from './lift/shared'
import { WallHero } from './gallery/pieces'
import { FRAMES } from './projects/frames'

import './projects-index.css'
import './gallery-index.css'

const pad = (n) => String(n).padStart(2, '0')

/* the wall mixes the projects, so no column is one building over and over */
function wallItems() {
  const byProject = new Map()
  FRAMES.forEach(([slug, src, width, height], i) => {
    if (!byProject.has(slug)) byProject.set(slug, [])
    byProject.get(slug).push({ id: i, src, width, height })
  })
  const lists = [...byProject.values()]
  const out = []
  for (let k = 0; out.length < FRAMES.length; k++) {
    for (const list of lists) if (list[k]) out.push(list[k])
  }
  return out
}

/* a line on each sector, read on the rail */
const LINES = {
  residential: 'Villas and family houses, where the lift is part of the architecture.',
  hospitality: 'Restaurants and cafes, where it runs all day on the front of house.',
  healthcare: 'Hospitals, specified for stretchers and for never stopping.',
  commercial: 'Offices and retail, sized for the morning rush.',
  institutional: 'Public buildings, built for queues and for decades.',
  industrial: 'Factories and parking structures, built for the load.',
}

const SPEC = [
  ['Location', (p) => p.location],
  ['System', (p) => p.lift_type_name],
  ['Capacity', (p) => p.capacity],
  ['Travel', (p) => p.stops],
]

/** how much of a slot is spent handing over to the next building */
const BLEND = 0.26

/* --- the buildings, held --------------------------------------------------
   The case studies are shown the way the home page shows the world below: one
   photograph held full-frame, the next crossfading in under the scroll, the
   copy re-entering each time, and a rail down the right you can move by hand.
   That is the pattern this site already speaks in, so the page reads as part
   of it rather than as a portfolio grid bolted on.

   What makes it this section and not that one: here the headline IS the
   building. On the home page the title is fixed and the contexts change under
   it; here the name changes with the photograph, set in the editorial serif,
   because the building is the subject rather than an example of one. The rail
   is grouped by sector, so a sector with one case study is simply one line on
   it — which is what finally kills the strip that used to wrap a drag rail
   around a single card. */

function Stage({ groups }) {
  const sectionRef = useRef(null)
  const layersRef = useRef([])
  const copyRef = useRef(null)
  const reduced = useReducedMotion()
  const [active, setActive] = useState(0)

  const all = useMemo(() => groups.flatMap((g) => g.items), [groups])
  const N = all.length

  // the crossfade is written straight onto the layers, so no CSS transition
  // fights the scrub
  useEffect(() => {
    const section = sectionRef.current
    if (!section || reduced || !N) return undefined

    const apply = (progress) => {
      const x = Math.min(N - 0.0001, Math.max(0, progress * N))
      const idx = Math.floor(x)
      const frac = x - idx
      const last = idx === N - 1
      // hold, then hand over in the tail of the slot. The last slot has
      // nothing to hand to, so `t` stays 0 there rather than fading the only
      // visible layer out and leaving an empty stage.
      const t = last || frac <= 1 - BLEND ? 0 : (frac - (1 - BLEND)) / BLEND
      const next = Math.min(N - 1, idx + 1)

      for (let i = 0; i < N; i++) {
        const el = layersRef.current[i]
        if (!el) continue
        let o = 0
        let sc = 1.04
        if (i === idx) {
          o = 1 - t
          sc = 1 + 0.04 * t
        } else if (i === next && t > 0) {
          o = t
          sc = 1.04 - 0.04 * t
        }
        el.style.opacity = o
        el.style.transform = `scale(${sc.toFixed(4)})`
      }

      const a = t > 0.5 ? next : idx
      setActive((prev) => (prev === a ? prev : a))
    }

    const tick = () => {
      const r = section.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < 0 || r.top > vh) return
      apply(clamp01(-r.top / Math.max(1, r.height - vh)))
    }

    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [N, reduced])

  // reduced motion: the rail is the only thing that changes the building
  useEffect(() => {
    if (!reduced) return
    for (let i = 0; i < N; i++) {
      const el = layersRef.current[i]
      if (el) {
        el.style.opacity = i === active ? 1 : 0
        el.style.transform = 'none'
      }
    }
  }, [reduced, active, N])

  // the copy re-enters whenever the building changes
  useEffect(() => {
    if (reduced || !copyRef.current) return undefined
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
    if (reduced || runway <= 0) {
      setActive(i)
      return
    }
    const top = section.getBoundingClientRect().top + window.scrollY
    const target = top + runway * ((i + 0.5) / N)
    if (window.__lenis) window.__lenis.scrollTo(target, { duration: 1 })
    else window.scrollTo({ top: target, behavior: 'smooth' })
  }

  if (!N) return null
  const p = all[Math.min(active, N - 1)]

  return (
    <section ref={sectionRef} className="pw" aria-labelledby="pw-title">
      <div className="pw__pin">
        <div className="pw__stage">
          {all.map((it, i) => (
            <div
              key={it.slug}
              className="pw__layer"
              ref={(el) => (layersRef.current[i] = el)}
              style={{ opacity: i === 0 ? 1 : 0 }}
            >
              <Img
                src={it.hero_image_url || it.poster_url}
                alt={i === active ? `${it.name} — ${it.statement}` : ''}
                sizes="100vw"
                priority={i === 0}
                objectPosition={it.is_portrait ? 'center 30%' : 'center'}
              />
            </div>
          ))}

          <div className="pw__veil" aria-hidden="true" />
          <div className="pw__floor" aria-hidden="true" />

          <div className="shell pw__content">
            <p className="ld-label pw__kicker" id="pw-title">
              Case studies · {pad(N)} buildings
            </p>

            <div className="pw__now" ref={copyRef}>
              <p className="pw__sector">
                <span className="pw__sector-n">{pad(active + 1)}</span>
                {p.category?.name}
                {p.year ? ` · ${p.year}` : ''}
              </p>
              <h2 className="pw__name">{p.name}</h2>
              <p className="pw__line">{p.statement}</p>
              <Link to={`/projects/${p.slug}`} className="pw__cta">
                Read the case study <Arrow size={14} />
              </Link>
            </div>

            <dl className="pw__spec">
              {SPEC.filter(([, get]) => get(p)).map(([label, get]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{get(p)}</dd>
                </div>
              ))}
            </dl>

            <nav className="pw__rail" aria-label="Case studies">
              {groups.map((g) => (
                <div className="pw__rail-group" key={g.slug}>
                  <p className="pw__rail-sector" title={LINES[g.slug] ?? g.description}>
                    {g.name}
                  </p>
                  <ol>
                    {g.items.map((it) => {
                      const i = all.indexOf(it)
                      return (
                        <li key={it.slug} className={i === active ? 'is-on' : ''}>
                          <button
                            type="button"
                            onClick={() => goTo(i)}
                            aria-current={i === active ? 'true' : undefined}
                          >
                            <span className="pw__rail-n">{pad(i + 1)}</span>
                            <span className="pw__rail-name">{it.name}</span>
                          </button>
                        </li>
                      )
                    })}
                  </ol>
                </div>
              ))}
            </nav>
          </div>
        </div>
      </div>
      {/* the runway the held stage above is read from */}
      <div className="pw__runway" aria-hidden="true" />
    </section>
  )
}

/* --- on film ----------------------------------------------------------------
   The films of the finished installations, one at a time on a screen, with the
   others racked under it. Choosing one is a cut, not a scroll. */

/* the index API carries a project's poster but not its film; the film sits
   beside the poster under the same name */
const filmOf = (p) =>
  p.hero_video_url || (p.poster_url ? p.poster_url.replace('/media/poster/', '/media/video/').replace(/\.\w+$/, '.mp4') : null)

function Films({ projects }) {
  const films = projects.map((p) => ({ ...p, hero_video_url: filmOf(p) })).filter((p) => p.hero_video_url)
  const [cur, setCur] = useState(() => Math.max(0, films.findIndex((p) => p.is_featured)))
  if (!films.length) return null
  const p = films[Math.min(cur, films.length - 1)]

  return (
    <section className="pf" aria-labelledby="pf-title">
      <div className="pf__head">
        <div>
          <p className="ld-label">On film · {pad(films.length)} reels</p>
          <RiseIn id="pf-title" text="Shot on site, after handover." className="pr-h2" />
        </div>
        <p className="pr-lead">
          Every reel here was made at the finished installation, with the client&rsquo;s lift running. No renders, no
          stock, nothing staged in a showroom.
        </p>
      </div>

      <div className={`pf__stage ${p.is_portrait ? 'is-tall' : 'is-wide'}`} key={p.slug}>
        <div className="pf__back" aria-hidden="true">
          <Img src={p.poster_url || p.hero_image_url} alt="" sizes="60vw" />
        </div>
        <div className="pf__player" style={{ aspectRatio: p.is_portrait ? '9 / 16' : '16 / 9' }}>
          <VideoPlayer
            src={p.hero_video_url}
            poster={p.poster_url || p.hero_image_url}
            ratio={p.is_portrait ? '9 / 16' : '16 / 9'}
            label={`Play the ${p.name} film`}
          />
        </div>
      </div>

      <div className="pf__foot">
        <div className="pf__acct" key={p.slug}>
          <p className="pf__kicker">
            <span>
              {pad(cur + 1)} / {pad(films.length)}
            </span>
            {p.category?.name}
            {p.year ? ` · ${p.year}` : ''}
          </p>
          <h3 className="pf__name">{p.name}</h3>
          <p className="pf__line">{p.statement}</p>
          <Link to={`/projects/${p.slug}`} className="pf__go">
            View case study <Arrow size={14} />
          </Link>
        </div>

        <ol className="pf__strip" aria-label="Choose a film">
          {films.map((f, i) => (
            <li key={f.slug}>
              <button
                type="button"
                className={`pf__take ${i === cur ? 'is-on' : ''}`}
                aria-pressed={i === cur}
                onClick={() => setCur(i)}
                aria-label={`${f.name} film`}
              >
                <span className="pf__take-img">
                  <Img src={f.poster_url || f.hero_image_url} alt="" ratio="4 / 5" sizes="8vw" />
                </span>
                <span className="pf__take-n">{pad(i + 1)}</span>
              </button>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

/* --- the ask: a frame that opens ------------------------------------------ */

function Invitation() {
  const wrap = useRef(null)
  useScrollVar(wrap, { from: 1, to: 0.15 })

  return (
    <div ref={wrap} className="pr-invite-wrap">
      <section className="pr-invite">
        <div className="pr-invite__scene">
          <Img src="/media/frames/lekha-approach.jpg" alt="" sizes="100vw" />
        </div>
        <div className="pr-invite__copy">
          <p className="ld-label">Next step</p>
          <h2 className="pr-invite__title ld-rise">
            <Rise text="Planning something similar?" />
          </h2>
          <p className="pr-invite__lead">
            Send the building type and the number of levels. We will tell you which of these projects yours most
            resembles, and what it would take.
          </p>
          <div className="pr-invite__actions">
            <Link to="/contact" className="pr-go">
              <span>Get a quote</span>
              <span className="pr-go__ring">
                <Arrow size={16} />
              </span>
            </Link>
            <Link to="/gallery" className="pr-invite__alt">
              See the gallery
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

/* --- page -------------------------------------------------------------------
   The same taste as the gallery: a tilted, drifting wall of every case-study
   photograph to open, then the case studies themselves, one strip a sector,
   moved by hand — then the films, and the way on. */

export default function Projects() {
  const { data: projects } = useApi('projects/')
  const { data: categories } = useApi('project-categories/')

  useEffect(() => {
    document.title = 'Projects — Zion Lifts'
  }, [])

  const all = useMemo(() => projects ?? [], [projects])
  const wall = useMemo(wallItems, [])

  const groups = useMemo(
    () =>
      (categories ?? [])
        .map((c) => ({ ...c, items: all.filter((p) => p.category?.slug === c.slug) }))
        .filter((g) => g.items.length),
    [all, categories],
  )

  return (
    <div className="pr ga">
      <WallHero
        items={wall}
        index={groups.map((g) => ({ key: g.slug, name: g.name, count: g.items.length }))}
        label={`Proof of delivery · ${pad(all.length)} buildings`}
        title="Real buildings. Real installations."
        lead="Every photograph and film on this page is of a lift Zion designed, built and installed. Nothing here is a render standing in for a job we have not done."
        cueHref={groups[0] ? `#${groups[0].slug}` : '#'}
        cueLabel="Scroll to the case studies"
      />

      <Stage groups={groups} />

      {all.length > 0 && <Films projects={all} />}
      <Invitation />
    </div>
  )
}
