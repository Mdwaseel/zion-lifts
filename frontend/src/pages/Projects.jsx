import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoPlayer } from '@/components/Media'
import { Arrow } from '@/components/icons'
import { useApi, useReducedMotion } from '@/lib/hooks'

import { Rise, RiseIn, useLightHero, useScrollVar, whenIntroDone } from './lift/shared'
import { Installations } from './home/Installations'
import { FRAMES } from './projects/frames'

import './projects-index.css'

const pad = (n) => String(n).padStart(2, '0')

/* --- the opening: one building at a time ---------------------------------
   The case studies take turns in one large frame, their name and street
   beside it, and a row of all of them underneath to pick from. It says what
   the page is before the page says it: real buildings, one after another. */

const TURN = 4200 // how long each building holds the frame, in ms

function Opening({ projects, groups, onPick }) {
  const reduced = useReducedMotion()
  const [at, setAt] = useState(0)
  const [shown, setShown] = useState(false)
  const [paused, setPaused] = useState(false)
  const n = projects.length
  useLightHero()

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  useEffect(() => {
    if (reduced || paused || n < 2) return undefined
    const t = setTimeout(() => setAt((i) => (i + 1) % n), TURN)
    return () => clearTimeout(t)
  }, [at, reduced, paused, n])

  const cur = projects[at]

  return (
    <header className={`pr-hero ${shown ? 'is-in' : ''}`}>
      <div className="pr-hero__copy">
        <h1 className="pr-hero__title">
          <Rise text="Real buildings. Real installations." accent={false} />
        </h1>
        <p className="pr-hero__lead">
          Every photograph and film on this page is of a lift Zion designed, built and installed. Nothing here is a
          render standing in for a job we have not done.
        </p>
        {groups.length > 0 && (
          <ul className="pr-hero__sectors">
            {groups.map((g) => (
              <li key={g.slug}>
                <a
                  href="#cases"
                  onClick={(e) => {
                    e.preventDefault()
                    onPick(g.slug)
                  }}
                >
                  {g.name} <span>{g.items.length}</span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>

      {cur && (
        <div className="pr-hero__show" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
          <Link to={`/projects/${cur.slug}`} className="pr-hero__frame" aria-label={`${cur.name} — read the case study`}>
            {projects.map((p, i) => (
              <span key={p.slug} className={`pr-hero__shot ${i === at ? 'is-on' : ''}`} aria-hidden="true">
                <Img src={p.hero_image_url} alt="" sizes="(min-width: 900px) 46vw, 92vw" priority={i < 2} />
              </span>
            ))}
            <span className="pr-hero__caption" key={cur.slug}>
              <strong>{cur.name}</strong>
              <span>
                {cur.category?.name} in {cur.location}
              </span>
            </span>
          </Link>

          <ol className="pr-hero__picks" aria-label="Case studies">
            {projects.map((p, i) => (
              <li key={p.slug}>
                <button
                  type="button"
                  className={i === at ? 'is-on' : ''}
                  aria-current={i === at}
                  aria-label={p.name}
                  onClick={() => setAt(i)}
                  onFocus={() => setPaused(true)}
                  onBlur={() => setPaused(false)}
                  style={{ '--turn': `${TURN}ms` }}
                >
                  <Img src={p.hero_image_url} alt="" sizes="6vw" />
                  <span className="pr-hero__tick" />
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}
    </header>
  )
}

/* --- the case studies: a wall you can sort ---------------------------------
   Every building on one light wall, largest first, each card its photograph,
   its name and the lift that went in. The sectors along the top sort it, and
   the hero's sector chips sort it too. Resting on a card turns its photograph
   over to another from the same job. */

/* how wide each card is on the twelve-column wall, in the order they fall */
const SPANS = [7, 5, 4, 4, 4, 6, 6]

/* a second photograph of each job, from the frames the case studies are shot in */
function secondFrame(p) {
  const hero = p.hero_image_url
  const f = FRAMES.find(([slug, src]) => slug === p.slug && src !== hero)
  return f ? f[1] : null
}

const CARD_SPEC = [
  ['System', (p) => p.lift_type_name],
  ['Capacity', (p) => p.capacity],
  ['Travel', (p) => p.stops],
]

function Cases({ projects, groups, filter, setFilter }) {
  const shown = filter === 'all' ? projects : projects.filter((p) => p.category?.slug === filter)
  if (!projects.length) return null

  const chips = [{ slug: 'all', name: 'All', count: projects.length }, ...groups.map((g) => ({ ...g, count: g.items.length }))]

  return (
    <section className="section on-paper pc" id="cases" aria-labelledby="pc-title">
      <div className="shell">
        <header className="pc__head">
          <RiseIn as="h2" id="pc-title" className="pr-h2" text="Every building, and its lift." accent={false} />
          <p className="pr-lead">
            Homes, restaurants and a hospital across Hyderabad — each with the system that went into it and what it
            had to do.
          </p>
        </header>

        <div className="pc__sort" role="group" aria-label="Show case studies from">
          {chips.map((c) => (
            <button
              type="button"
              key={c.slug}
              className={filter === c.slug ? 'is-on' : ''}
              aria-pressed={filter === c.slug}
              onClick={() => setFilter(c.slug)}
            >
              {c.name} <span>{c.count}</span>
            </button>
          ))}
        </div>

        <ul className="pc__wall" key={filter}>
          {shown.map((p, i) => {
            const alt = secondFrame(p)
            const span = shown.length === 1 ? 12 : SPANS[i % SPANS.length]
            return (
              <li key={p.slug} className="pc-card" style={{ '--span': span, '--i': i }}>
                <Link to={`/projects/${p.slug}`} className="pc-card__link">
                  <span className="pc-card__media">
                    <Img src={p.hero_image_url} alt="" sizes={`(min-width: 900px) ${Math.round((span / 12) * 100)}vw, 92vw`} />
                    {alt && (
                      <span className="pc-card__alt" aria-hidden="true">
                        <Img src={alt} alt="" sizes={`(min-width: 900px) ${Math.round((span / 12) * 100)}vw, 92vw`} />
                      </span>
                    )}
                    <span className="pc-card__sector">
                      {p.category?.name}
                      {p.year ? `, ${p.year}` : ''}
                    </span>
                  </span>
                  <span className="pc-card__body">
                    <span className="pc-card__name">{p.name}</span>
                    <span className="pc-card__line">{p.statement}</span>
                    <span className="pc-card__spec">
                      {CARD_SPEC.filter(([, get]) => get(p)).map(([label, get]) => (
                        <span key={label}>
                          <em>{label}</em>
                          {get(p)}
                        </span>
                      ))}
                    </span>
                    <span className="pc-card__go">
                      Read the case study <Arrow size={14} />
                    </span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
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
  const [filter, setFilter] = useState('all')

  // a sector chip in the opening sorts the wall and takes you down to it
  const pick = (slug) => {
    setFilter(slug)
    const el = document.getElementById('cases')
    if (!el) return
    if (window.__lenis) window.__lenis.scrollTo(el, { offset: -40, duration: 1.1 })
    else el.scrollIntoView({ behavior: 'smooth' })
  }

  const groups = useMemo(
    () =>
      (categories ?? [])
        .map((c) => ({ ...c, items: all.filter((p) => p.category?.slug === c.slug) }))
        .filter((g) => g.items.length),
    [all, categories],
  )

  return (
    <div className="pr">
      <Opening projects={all} groups={groups} onPick={pick} />

      <Cases projects={all} groups={groups} filter={filter} setFilter={setFilter} />

      {all.length > 0 && <Films projects={all} />}
      <Installations />
      <Invitation />
    </div>
  )
}
