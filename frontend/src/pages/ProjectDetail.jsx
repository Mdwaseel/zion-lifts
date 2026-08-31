import { useEffect, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Img, VideoPlayer } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { CtaBand, ProjectCard, SectionHead } from '@/components/sections'
import { Arrow } from '@/components/icons'
import { useApi, useScrollProgress } from '@/lib/hooks'

import './projects.css'

const STAGE_ORDER = ['site', 'installation', 'interior', 'detail', 'completion']
const STAGE_LABEL = {
  site: 'The site',
  installation: 'Installation',
  interior: 'Interior',
  detail: 'Details',
  completion: 'Completed',
}

/** The pinned stage sequence: site → installation → interior → completion. */
function Sequence({ images }) {
  const [ref, progress] = useScrollProgress()
  const ordered = useMemo(() => {
    const byStage = new Map()
    for (const img of images) {
      if (!byStage.has(img.stage)) byStage.set(img.stage, img)
    }
    return STAGE_ORDER.filter((s) => byStage.has(s)).map((s) => byStage.get(s))
  }, [images])

  if (ordered.length < 2) return null
  const active = Math.min(ordered.length - 1, Math.floor(progress * ordered.length * 1.02))

  return (
    <section ref={ref} className="section section--flush pseq">
      <div className="pseq__pin">
        <div className="pseq__stage">
          {ordered.map((img, i) => (
            <div key={img.id} className={`pseq__layer ${i === active ? 'is-on' : ''}`}>
              <Img src={img.src} alt={img.alt} sizes="100vw" />
            </div>
          ))}
          <div className="pseq__veil" aria-hidden="true" />
          <div className="shell pseq__content">
            <p className="eyebrow">How it came together</p>
            <h2 className="h2 pseq__label">{STAGE_LABEL[ordered[active].stage]}</h2>
            <p className="lead pseq__caption">{ordered[active].caption}</p>
            <ol className="pseq__rail">
              {ordered.map((img, i) => (
                <li key={img.id} className={i === active ? 'is-on' : ''}>
                  <span className="pseq__rail-bar" />
                  <span className="pseq__rail-label">{STAGE_LABEL[img.stage]}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
      <div className="pseq__runway" aria-hidden="true" />
    </section>
  )
}

export default function ProjectDetail() {
  const { slug } = useParams()
  const { data: project, loading, error } = useApi(slug ? `projects/${slug}/` : null)
  const { data: testimonials } = useApi('testimonials/')

  useEffect(() => {
    if (project) document.title = `${project.name} — Zion Lifts`
  }, [project])

  if (loading) {
    return (
      <div className="section">
        <div className="shell">
          <div className="skeleton" style={{ height: '60vh' }} />
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <section className="section">
        <div className="shell state">
          <p className="state__title">We could not find that project.</p>
          <Link to="/projects" className="btn btn--accent btn--sm">
            All projects <Arrow size={14} />
          </Link>
        </div>
      </section>
    )
  }

  const quote = (testimonials ?? []).find((t) => t.project_slug === project.slug)
  const gallery = project.images ?? []

  return (
    <>
      {/* --- hero --- */}
      <header className="phero">
        <div className="phero__bg">
          <Img
            src={project.hero_image_url || project.poster_url}
            alt={project.name}
            priority
            sizes="100vw"
          />
          <div className="phero__veil" aria-hidden="true" />
        </div>
        <div className="shell phero__inner">
          <nav className="pagehero__crumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span aria-hidden="true">/</span>
            <Link to="/projects">Projects</Link>
            <span aria-hidden="true">/</span>
            <span>{project.name}</span>
          </nav>
          <p className="eyebrow">
            {project.category?.name}
            {project.year ? ` · ${project.year}` : ''}
          </p>
          <h1 className="display phero__title">{project.name}</h1>
          <p className="lead phero__statement">{project.statement}</p>
          <dl className="phero__meta">
            {[
              ['Location', project.location],
              ['System', project.system],
              ['Capacity', project.capacity],
              ['Stops', project.stops],
              ['Doors', project.door],
              ['Drive', project.drive],
            ]
              .filter(([, v]) => v)
              .map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
          </dl>
        </div>
      </header>

      {/* --- challenge / solution / result --- */}
      <section className="section on-paper">
        <div className="shell">
          {project.summary && (
            <Reveal>
              <p className="lead csr__summary">{project.summary}</p>
            </Reveal>
          )}
          <RevealGroup className="csr" step={90}>
            {[
              ['The challenge', project.challenge],
              ['The solution', project.solution],
              ['The result', project.result],
            ]
              .filter(([, v]) => v)
              .map(([title, body], i) => (
                <div className="csr__cell" key={title}>
                  <span className="index-num">{String(i + 1).padStart(2, '0')}</span>
                  <h2 className="csr__title">{title}</h2>
                  <p className="csr__body">{body}</p>
                </div>
              ))}
          </RevealGroup>
        </div>
      </section>

      <Sequence images={gallery} />

      {/* --- the film --- */}
      {project.hero_video_url && (
        <section className="section">
          <div className="shell">
            <SectionHead
              eyebrow="The film"
              title={`${project.name}, on site.`}
              lead="Shot at the completed installation. No renders, no stock."
            />
            <Reveal variant="wipe">
              <VideoPlayer
                src={project.hero_video_url}
                poster={project.poster_url || project.hero_image_url}
                ratio={project.is_portrait ? '9 / 16' : '16 / 9'}
                className={project.is_portrait ? 'videoplayer--portrait' : ''}
                label="Play the project film"
              />
            </Reveal>
          </div>
        </section>
      )}

      {/* --- gallery --- */}
      {gallery.length > 0 && (
        <section className="section on-stone">
          <div className="shell">
            <SectionHead eyebrow="Gallery" title="Everything we photographed." split={false} />
            <RevealGroup className="pgallery" step={60} variant="wipe">
              {gallery.map((img) => (
                <figure className="pgallery__cell" key={img.id}>
                  <Img
                    src={img.src}
                    alt={img.alt}
                    ratio="4 / 3"
                    sizes="(min-width: 1000px) 32vw, (min-width: 640px) 48vw, 92vw"
                  />
                  <figcaption>
                    <span className="mono">{STAGE_LABEL[img.stage]}</span>
                    {img.caption}
                  </figcaption>
                </figure>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {/* --- client quote --- */}
      {quote && (
        <section className="section pquote">
          <div className="shell shell--text">
            <Reveal>
              <figure className="pquote__fig">
                <blockquote className="pquote__text">&ldquo;{quote.quote}&rdquo;</blockquote>
                <figcaption className="pquote__by">
                  <strong>{quote.organisation || quote.name}</strong>
                  <span>
                    {quote.role}
                    {quote.location ? ` · ${quote.location}` : ''}
                  </span>
                </figcaption>
              </figure>
            </Reveal>
          </div>
        </section>
      )}

      {/* --- related --- */}
      {project.related?.length > 0 && (
        <section className="section">
          <div className="shell">
            <SectionHead
              eyebrow="More work"
              title="Related projects."
              action={
                <Link to="/projects" className="link">
                  All projects <Arrow size={14} />
                </Link>
              }
            />
            <RevealGroup className="projectgrid" step={70}>
              {project.related.map((p) => (
                <ProjectCard key={p.slug} project={p} />
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      <CtaBand
        eyebrow="Next step"
        title="Planning something similar?"
        lead={`If your building resembles ${project.name}, we already know most of the questions worth asking.`}
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{
          to: project.lift_type_slug ? `/lifts/${project.lift_type_slug}` : '/lifts',
          label: project.lift_type_name ? `About the ${project.lift_type_name}` : 'See the range',
        }}
      />
    </>
  )
}
