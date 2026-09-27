import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Img, VideoPlayer } from '@/components/Media'
import { DoorMark } from '@/components/cabin-marks'
import { AskBand, Asks, quoteHref } from '@/components/Asks'
import { Arrow, CogMark, Phone, Plus, UpDownMark, UsersMark, Wrench } from '@/components/icons'
import { LIFT_ICONS } from '@/components/lift-marks'
import { useApi } from '@/lib/hooks'
import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import { Rise, RiseIn, Scrub, useLightHero, useScrollVar, whenIntroDone } from './lift/shared'
import { Lightbox } from './gallery/pieces'
import { sizeOf } from './projects/frames'

import './gallery.css'
import './projects-index.css'
import './project-detail.css'

const STAGE_LABEL = {
  site: 'The site',
  installation: 'Installation',
  interior: 'Interior',
  detail: 'Details',
  completion: 'Completed',
}
const STAGE_ORDER = ['site', 'installation', 'interior', 'detail', 'completion']

/* the three chapters of every job, and the kind of photograph each is told
   with — first choice first */
const CHAPTERS = [
  ['The challenge', 'challenge', ['site', 'installation', 'interior']],
  ['The solution', 'solution', ['installation', 'interior', 'detail']],
  ['The result', 'result', ['completion', 'interior', 'detail']],
]

/* --- the opening: the name, then the building -----------------------------
   Set like the first page of a monograph: the building's name large on ivory
   with its statement beside it, and under them the building itself, a wide
   frame that opens out from its middle and drifts as the page moves. The
   lift's figures sit on a plate across the frame's lower edge. */
function Opening({ project: p }) {
  const ref = useRef(null)
  const [shown, setShown] = useState(false)
  useScrollVar(ref, { from: 0, to: -1, ease: 1 })
  useLightHero()
  useEffect(() => whenIntroDone(() => setShown(true)), [])

  // each figure with the mark it is read by: the system by its own lift's mark
  const specs = [
    ['System', p.system || p.lift_type_name, LIFT_ICONS[p.lift_type_slug] ?? CogMark],
    ['Capacity', p.capacity, UsersMark],
    ['Stops', p.stops, UpDownMark],
    ['Doors', p.door, DoorMark],
    ['Drive', p.drive, CogMark],
    ['Scope', p.scope, Wrench],
  ].filter(([, v]) => v)
  const where = [p.category?.name, p.location].filter(Boolean).join(' in ')

  return (
    <header ref={ref} className={`pd-hero ${shown ? 'is-in' : ''}`}>
      <div className="pd-hero__top">
        <nav className="pd-crumb" aria-label="Breadcrumb">
          <Link to="/projects">Projects</Link>
          <span aria-hidden="true">/</span>
          <span>{p.name}</span>
        </nav>
        <h1 className={`pd-hero__name ld-rise ${shown ? 'is-in' : ''}`}>
          <Rise text={p.name} accent={false} />
        </h1>
        <div className="pd-hero__aside">
          <div className="pd-hero__say">
            <p className="pd-hero__statement">{p.statement}</p>
            <p className="pd-hero__kicker">
              {where}
              {p.year ? `, ${p.year}` : ''}
            </p>
          </div>
          <Asks to={quoteOf(p)} label="Get a quote for a lift like this" short="Get a quote" whatsapp={chatOf(p)} compact />
        </div>
      </div>

      <div className="pd-hero__view">
        <div className="pd-hero__scene" aria-hidden="true">
          <Img src={p.hero_image_url || p.poster_url} alt="" priority sizes="100vw" />
        </div>
        <dl className="pd-plate">
          {specs.map(([k, v, Icon], i) => (
            <div key={k} style={{ '--i': i }}>
              <span className="pd-plate__icon" aria-hidden="true">
                <Icon size={20} />
              </span>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </header>
  )
}

/* --- the asks ----------------------------------------------------------------
   A case study is read by someone deciding whether their building could have
   the same. So the way to ask is offered where that decision is made: under
   the name, on the job sheet, after the story, and in a small bar that rides
   along between them. Every one of them lands on the enquiry form with this
   lift chosen and this building named in the brief. */

const quoteOf = (p) => quoteHref({ lift: p.lift_type_slug, like: p.name })
const chatOf = (p) => `Hello Zion Lifts — I saw ${p.name} on your site and would like something similar.`

/* the bar that rides along: shown once the opening has gone, put away again
   when the page's own way on comes up */
function StickyAsk({ project: p }) {
  const site = useSite()
  const [shown, setShown] = useState(false)

  useEffect(() => {
    const hero = document.querySelector('.pd-hero')
    const end = document.querySelector('.pd-next')
    if (!hero) return undefined
    let past = false
    let atEnd = false
    const apply = () => setShown(past && !atEnd)
    const io1 = new IntersectionObserver(([e]) => {
      past = !e.isIntersecting && e.boundingClientRect.top < 0
      apply()
    })
    const io2 = new IntersectionObserver(([e]) => {
      atEnd = e.isIntersecting
      apply()
    })
    io1.observe(hero)
    if (end) io2.observe(end)
    return () => {
      io1.disconnect()
      io2.disconnect()
    }
  }, [])

  return (
    <aside className={`pd-stick ${shown ? 'is-on' : ''}`} aria-label="Enquire about a lift like this" aria-hidden={!shown}>
      <p className="pd-stick__text">
        Like <strong>{p.name}</strong>?
      </p>
      <Link to={quoteOf(p)} className="pd-stick__go" tabIndex={shown ? 0 : -1}>
        Get a quote <Arrow size={14} />
      </Link>
      {site?.phone && (
        <a href={telHref(site.phone)} className="pd-stick__call" aria-label={`Call ${site.phone}`} tabIndex={shown ? 0 : -1}>
          <Phone size={16} />
        </a>
      )}
    </aside>
  )
}

/* --- the brief, and the job sheet beside it --------------------------------
   What the building asked for, set large; beside it the facts a site engineer
   would want on one card. */
function Brief({ project: p }) {
  const facts = [
    ['Where', p.location],
    ['Completed', p.year],
    ['Building', p.category?.name],
    ['System', p.system || p.lift_type_name],
    ['Scope', p.scope],
  ].filter(([, v]) => v)

  return (
    <section className="pd-brief" aria-label="The brief">
      <div className="pd-brief__in">
        <div className="pd-brief__say">
          <p className="ld-label">The brief</p>
          <Scrub as="p" className="pd-brief__text" text={p.summary} span={0.5} />
        </div>
        {facts.length > 0 && (
          <div className="pd-sheet">
            <dl>
              {facts.map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
            <Link to={quoteOf(p)} className="pd-sheet__go">
              Get this spec quoted for your building <Arrow size={14} />
            </Link>
          </div>
        )}
      </div>
    </section>
  )
}

/* --- the story: challenge, solution, result, side by side -------------------
   Three tall cards in one row, each the photograph that proves its part and
   the few lines that tell it. They come up one after another as the row
   reaches the middle of the screen. */
function Story({ chapters }) {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.35 })

  return (
    <section className="pd-story" aria-labelledby="pd-story-title">
      <header className="pd-story__head">
        <RiseIn as="h2" id="pd-story-title" text="How it came together." className="pd-h2" accent={false} />
      </header>
      <ol ref={ref} className="pd-tri">
        {chapters.map((c, i) => (
          <li className="pd-tri__card" key={c.title} style={{ '--i': i }}>
            <figure className="pd-tri__fig">
              {c.image && <Img src={c.image.src} alt={c.image.alt || ''} sizes="(min-width: 900px) 32vw, 92vw" />}
              <span className="pd-tri__tag">{c.title}</span>
            </figure>
            <div className="pd-tri__text">
              <h3>{c.title}</h3>
              <p>{c.body}</p>
              {c.image?.caption && <p className="pd-tri__cap">{c.image.caption}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

/* --- the archive: every photograph, packed ---------------------------------
   A masonry wall: each photograph keeps its own shape, so a tall cabin and a
   wide facade sit together without either being cropped to a tile. The first
   frame takes two columns, the rest fall in behind it in the order the job
   happened. Everything is one number wide, so the spans are worked out from
   the column width every time the wall is resized. */

const ROW = 10 // the grid's row unit, px; must match --row in the stylesheet

function Shots({ project, shots, onOpen }) {
  const grid = useRef(null)

  useLayoutEffect(() => {
    const el = grid.current
    if (!el) return undefined
    const layout = () => {
      const cs = getComputedStyle(el)
      const gap = parseFloat(cs.rowGap) || 0
      const cols = cs.gridTemplateColumns.split(' ').filter(Boolean).length
      const colW = (el.clientWidth - gap * (cols - 1)) / cols
      for (const li of el.children) {
        const ratio = Number(li.dataset.ratio) || 4 / 3
        const wide = li.dataset.wide !== undefined && cols > 1
        const w = wide ? colW * 2 + gap : colW
        const span = Math.max(1, Math.round((w / ratio + gap) / (ROW + gap)))
        li.style.setProperty('--span', span)
      }
    }
    layout()
    const ro = new ResizeObserver(layout)
    ro.observe(el)
    return () => ro.disconnect()
  }, [shots])

  // each frame is uncovered as it reaches the screen, in threes across a row
  useEffect(() => {
    const el = grid.current
    if (!el) return undefined
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue
          e.target.classList.add('is-in')
          io.unobserve(e.target)
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
    )
    for (const li of el.children) io.observe(li)
    return () => io.disconnect()
  }, [shots])

  return (
    <section className="pd-shots on-paper" aria-labelledby="pd-shots-title">
      <div className="pd-shots__head">
        <div>
          <p className="ld-label">The archive</p>
          <RiseIn id="pd-shots-title" text="Every photograph." className="pd-h2" />
        </div>
        <p className="pd-shots__line">
          Everything we photographed at {project.name}, from the first visit to the finished lift. Select one to open it
          full size.
        </p>
      </div>

      <ul ref={grid} className="pd-grid">
        {shots.map((it, i) => (
          <li
            key={it.id}
            className="pd-shot"
            style={{ '--i': i % 3 }}
            data-ratio={(it.width / it.height).toFixed(4)}
            /* the opening frame takes two columns, but only when it lies wide:
               a portrait blown to double width would fill the screen twice over */
            data-wide={i === 0 && it.width / it.height > 1.2 ? '' : undefined}
          >
            <button type="button" className="pd-shot__btn" onClick={() => onOpen(i)} aria-label={`${it.caption} — open full size`}>
              <span className="pd-shot__img">
                <Img src={it.src} alt={it.alt || ''} sizes="(min-width: 900px) 34vw, 48vw" draggable={false} />
              </span>
              <span className="pd-shot__veil" aria-hidden="true" />
              <span className="pd-shot__tag" aria-hidden="true">
                {STAGE_LABEL[it.stage]}
              </span>
              <span className="pd-shot__cap" aria-hidden="true">
                <span className="pd-shot__title">{it.caption}</span>
                <span className="pd-shot__ring">
                  <Plus size={14} />
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/* --- the film: the finished lift, running --------------------------------- */
function Film({ project: p }) {
  const tall = !!p.is_portrait
  return (
    <section className="pd-film" aria-labelledby="pd-film-title">
      <div className={`pd-film__in ${tall ? 'is-tall' : 'is-wide'}`}>
        <div className="pd-film__copy">
          <p className="ld-label">On film</p>
          <RiseIn as="h2" id="pd-film-title" text={`${p.name}, on site.`} className="pd-h2" accent={false} />
          <p className="pd-film__lead">
            Shot at the finished installation, with the lift running. No renders, no stock.
          </p>
        </div>
        <div className="pd-film__screen">
          <VideoPlayer
            src={p.hero_video_url}
            poster={p.poster_url || p.hero_image_url}
            ratio={tall ? '9 / 16' : '16 / 9'}
            label={`Play the ${p.name} film`}
          />
        </div>
      </div>
    </section>
  )
}

/* --- the way on: the next building in the same sector ----------------------- */
function NextProject({ project }) {
  const next = project.related?.[0]
  const scene = next ? next.hero_image_url || next.poster_url : '/media/frames/lekha-approach.jpg'

  return (
    <section className="pd-next" aria-label={next ? 'Next project' : 'Next step'}>
      <div className="pd-next__card">
        <div className="pd-next__copy">
          <p className="ld-label">{next ? 'Next project' : 'Next step'}</p>
          <h2 className="pd-next__title">{next ? next.name : 'Planning something similar?'}</h2>
          <p className="pd-next__lead">
            {next
              ? next.statement
              : `If your building resembles ${project.name}, we already know most of the questions worth asking.`}
          </p>
          <div className="pd-next__actions">
            <Link to={next ? `/projects/${next.slug}` : '/contact'} className="pd-next__go">
              {next ? 'View the case study' : 'Get a quote'} <Arrow size={14} />
            </Link>
            {next && <Link to="/contact">Get a quote</Link>}
            <Link to="/projects">All projects</Link>
          </div>
        </div>
        <Link
          to={next ? `/projects/${next.slug}` : '/contact'}
          className="pd-next__media"
          aria-hidden="true"
          tabIndex={-1}
        >
          <Img src={scene} alt="" sizes="(min-width: 900px) 50vw, 92vw" />
        </Link>
      </div>
    </section>
  )
}

/* --- page ------------------------------------------------------------------
   One building, on light ground throughout: the name and the building, the
   brief beside its job sheet, the story as three cards side by side, the
   film, every photograph, what the client said, and the next building. */
export default function ProjectDetail() {
  const { slug } = useParams()
  const { data: project, loading, error } = useApi(slug ? `projects/${slug}/` : null)
  const { data: testimonials } = useApi('testimonials/')
  const [open, setOpen] = useState(null)

  useEffect(() => {
    if (project) document.title = `${project.name} — Zion Lifts`
  }, [project])

  useEffect(() => {
    window.scrollTo(0, 0)
    setOpen(null)
  }, [slug])

  const images = useMemo(() => {
    const list = project?.images ?? []
    return [...list].sort((a, b) => STAGE_ORDER.indexOf(a.stage) - STAGE_ORDER.indexOf(b.stage))
  }, [project])

  // each chapter takes the first unused photograph of its kind
  const chapters = useMemo(() => {
    if (!project) return []
    const used = new Set()
    return CHAPTERS.map(([title, key, stages]) => {
      let img = null
      for (const st of stages) {
        img = images.find((i) => i.stage === st && !used.has(i.id))
        if (img) break
      }
      if (!img) img = images.find((i) => !used.has(i.id)) ?? null
      if (img) used.add(img.id)
      return { title, body: project[key], image: img }
    }).filter((c) => c.body)
  }, [project, images])

  const shots = useMemo(
    () =>
      images.map((i) => ({
        ...i,
        ...sizeOf(i.src),
        title: i.caption,
        meta: STAGE_LABEL[i.stage],
      })),
    [images],
  )
  const move = useCallback((d) => setOpen((i) => (i === null ? null : (i + d + shots.length) % shots.length)), [shots.length])

  if (loading) {
    return (
      <div className="pd pd--wait" aria-busy="true">
        <div className="pd-wait" />
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="pd pd--wait">
        <div className="pd-missing">
          <p className="pd-missing__title">We could not find that project.</p>
          <Link to="/projects" className="pr-go">
            <span>All projects</span>
            <span className="pr-go__ring">
              <Arrow size={16} />
            </span>
          </Link>
        </div>
      </div>
    )
  }

  const quote = (testimonials ?? []).find((t) => t.project_slug === project.slug)

  return (
    <div className="pd">
      <Opening project={project} />

      {project.summary && <Brief project={project} />}

      {chapters.length > 0 && <Story chapters={chapters} />}

      <AskBand
        id="pd-ask-title"
        className="pd-ask"
        title={`Want a lift like ${project.name}’s?`}
        lead="Tell us about your building — floors, shaft, what the lift has to carry. An engineer reads every enquiry and replies within one working day."
        to={quoteOf(project)}
        label="Start your enquiry"
        whatsapp={chatOf(project)}
      />

      {project.hero_video_url && <Film project={project} />}

      {shots.length > 0 && <Shots project={project} shots={shots} onOpen={setOpen} />}

      {quote && (
        <section className="pd-quote" aria-label="What the client said">
          <figure className="pd-quote__fig">
            <span className="pd-quote__mark" aria-hidden="true">
              &ldquo;
            </span>
            <blockquote className="pd-quote__text">
              <Scrub as="p" text={quote.quote} span={0.4} />
            </blockquote>
            <figcaption className="pd-quote__by">
              <strong>{quote.organisation || quote.name}</strong>
              <span>
                {quote.role}
                {quote.location ? `, ${quote.location}` : ''}
              </span>
            </figcaption>
          </figure>
        </section>
      )}

      <NextProject project={project} />
      <StickyAsk project={project} />

      {open !== null && <Lightbox items={shots} index={open} onClose={() => setOpen(null)} onMove={move} />}
    </div>
  )
}
