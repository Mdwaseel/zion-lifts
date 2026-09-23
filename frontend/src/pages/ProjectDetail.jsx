import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Img, VideoPlayer } from '@/components/Media'
import { Arrow, Plus } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import { Rise, RiseIn, Scrub, useScrollVar, whenIntroDone } from './lift/shared'
import { Lightbox } from './gallery/pieces'
import { sizeOf } from './projects/frames'

import './gallery.css'
import './projects-index.css'
import './project-detail.css'

const pad = (n) => String(n).padStart(2, '0')

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

/* --- the opening: the building, and the lift's nameplate -----------------
   The photograph fills the screen and drifts up as the page moves; the name
   stands at the foot of it in the serif, with the statement beside it, and
   the lift's figures run along the bottom edge like the plate in a car. */
function Opening({ project: p }) {
  const ref = useRef(null)
  const [shown, setShown] = useState(false)
  useScrollVar(ref, { from: 0, to: -1, ease: 1 })
  useEffect(() => whenIntroDone(() => setShown(true)), [])

  const specs = [
    ['System', p.system || p.lift_type_name],
    ['Capacity', p.capacity],
    ['Stops', p.stops],
    ['Doors', p.door],
    ['Drive', p.drive],
    ['Scope', p.scope],
  ].filter(([, v]) => v)

  return (
    <header ref={ref} className={`pd-hero ${shown ? 'is-in' : ''}`}>
      <div className="pd-hero__scene" aria-hidden="true">
        <Img src={p.hero_image_url || p.poster_url} alt="" priority sizes="100vw" />
      </div>
      <div className="pd-hero__grade" aria-hidden="true" />

      <nav className="pd-crumb" aria-label="Breadcrumb">
        <Link to="/projects">Projects</Link>
        <span aria-hidden="true">/</span>
        <span>{p.category?.name}</span>
      </nav>

      <div className="pd-hero__copy">
        <p className="pd-hero__kicker">
          {p.category?.name}
          {p.year ? ` · ${p.year}` : ''}
          {p.location ? ` · ${p.location}` : ''}
        </p>
        <h1 className={`pd-hero__name ld-rise ${shown ? 'is-in' : ''}`}>
          <Rise text={p.name} accent={false} />
        </h1>
        <p className="pd-hero__statement">{p.statement}</p>
      </div>

      <dl className="pd-plate">
        {specs.map(([k, v], i) => (
          <div key={k} style={{ '--i': i }}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </header>
  )
}

/* --- a chapter: one photograph and what it shows ----------------------------
   The frame tips up into place as it comes up the screen; the text beside it
   is short enough to read while it does. */
function Chapter({ title, body, image, flip, index }) {
  const ref = useRef(null)
  useScrollVar(ref, { from: 1, to: 0.4 })
  const size = image ? sizeOf(image.src) : null
  const portrait = size ? size.height > size.width : false

  return (
    <article ref={ref} className={`pd-ch ${flip ? 'is-flip' : ''} ${portrait ? 'is-tall' : ''}`}>
      {image && (
        <figure className="pd-ch__fig">
          <span className="pd-ch__frame">
            <Img
              src={image.src}
              alt={image.alt || ''}
              ratio={portrait ? '4 / 5' : '4 / 3'}
              sizes="(min-width: 900px) 50vw, 100vw"
            />
          </span>
          {image.caption && <figcaption className="pd-ch__cap">{image.caption}</figcaption>}
        </figure>
      )}
      <div className="pd-ch__text">
        <p className="pd-ch__n">{pad(index + 1)}</p>
        <RiseIn as="h2" text={`${title}.`} className="pd-h2" />
        <p className="pd-ch__body">{body}</p>
      </div>
    </article>
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
    <section className="pf pd-film" aria-labelledby="pd-film-title">
      <div className="pf__head">
        <div>
          <p className="ld-label">On film</p>
          <RiseIn id="pd-film-title" text={`${p.name}, on site.`} className="pr-h2" />
        </div>
        <p className="pr-lead">Shot at the finished installation, with the lift running. No renders, no stock.</p>
      </div>
      <div className={`pf__stage ${tall ? 'is-tall' : 'is-wide'}`}>
        <div className="pf__back" aria-hidden="true">
          <Img src={p.poster_url || p.hero_image_url} alt="" sizes="60vw" />
        </div>
        <div className="pf__player" style={{ aspectRatio: tall ? '9 / 16' : '16 / 9' }}>
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
  const wrap = useRef(null)
  useScrollVar(wrap, { from: 1, to: 0.15 })
  const next = project.related?.[0]
  const scene = next ? next.hero_image_url || next.poster_url : '/media/frames/lekha-approach.jpg'

  return (
    <div ref={wrap} className="pr-invite-wrap">
      <section className="pr-invite" aria-label={next ? 'Next project' : 'Next step'}>
        <div className="pr-invite__scene">
          <Img src={scene} alt="" sizes="100vw" />
        </div>
        <div className="pr-invite__copy">
          <p className="ld-label">{next ? `Next project · ${next.category?.name ?? ''}` : 'Next step'}</p>
          <h2 className="pr-invite__title ld-rise">
            <Rise text={next ? next.name : 'Planning something similar?'} accent={!next} />
          </h2>
          <p className="pr-invite__lead">
            {next
              ? next.statement
              : `If your building resembles ${project.name}, we already know most of the questions worth asking.`}
          </p>
          <div className="pr-invite__actions">
            <Link to={next ? `/projects/${next.slug}` : '/contact'} className="pr-go">
              <span>{next ? 'View the case study' : 'Get a quote'}</span>
              <span className="pr-go__ring">
                <Arrow size={16} />
              </span>
            </Link>
            {next && (
              <Link to="/contact" className="pr-invite__alt">
                Get a quote
              </Link>
            )}
            <Link to="/projects" className="pr-invite__alt">
              All projects
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

/* --- page ------------------------------------------------------------------
   One building, told the way the site tells everything: the photograph first
   (dark), the brief read into focus (ivory), the three chapters each with the
   photograph that proves it (paper), the film (dark), every photograph on a
   strip (paper), what the client said (dark), and the next building. */
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

      {project.summary && (
        <section className="pd-brief on-stone" aria-label="The brief">
          <p className="ld-label">The brief</p>
          <Scrub as="p" className="pd-brief__text" text={project.summary} span={0.5} />
        </section>
      )}

      {chapters.length > 0 && (
        <section className="pd-story on-paper" aria-label="How it came together">
          {chapters.map((c, i) => (
            <Chapter key={c.title} index={i} title={c.title} body={c.body} image={c.image} flip={i % 2 === 1} />
          ))}
        </section>
      )}

      {project.hero_video_url && <Film project={project} />}

      {shots.length > 0 && <Shots project={project} shots={shots} onOpen={setOpen} />}

      {quote && (
        <section className="pd-quote" aria-label="What the client said">
          <figure className="pd-quote__fig">
            <blockquote className="pd-quote__text">
              <Scrub as="p" text={`“${quote.quote}”`} span={0.4} />
            </blockquote>
            <figcaption className="pd-quote__by">
              <strong>{quote.organisation || quote.name}</strong>
              <span>
                {quote.role}
                {quote.location ? ` · ${quote.location}` : ''}
              </span>
            </figcaption>
          </figure>
        </section>
      )}

      <NextProject project={project} />

      {open !== null && <Lightbox items={shots} index={open} onClose={() => setOpen(null)} onMove={move} />}
    </div>
  )
}
