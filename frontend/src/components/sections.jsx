import { useId, useState } from 'react'
import { Link } from 'react-router-dom'

import { useCountUp } from '@/lib/hooks'
import { parseStat } from '@/lib/media'

import { Img, VideoLoop } from './Media'
import Reveal, { RevealGroup } from './Reveal'
import { Arrow, Plus } from './icons'

/* ==========================================================================
   Page hero — every page except Home opens with this
   ========================================================================== */

export function PageHero({
  eyebrow,
  title,
  lead,
  crumbs = [],
  image,
  video,
  poster,
  meta,
  children,
  align = 'end',
}) {
  const hasMedia = Boolean(image || video)
  return (
    <header className={`pagehero ${hasMedia ? 'pagehero--media' : ''}`} data-align={align}>
      {hasMedia && (
        <div className="pagehero__bg">
          {video ? (
            <VideoLoop src={video} poster={poster ?? image} className="pagehero__media" />
          ) : (
            <Img src={image} alt="" priority sizes="100vw" className="pagehero__media" />
          )}
        </div>
      )}
      <div className="shell pagehero__inner">
        {crumbs.length > 0 && (
          <nav className="pagehero__crumb" aria-label="Breadcrumb">
            {crumbs.map((c, i) => (
              <span key={c.label}>
                {i > 0 && <span aria-hidden="true"> / </span>}
                {c.to ? <Link to={c.to}>{c.label}</Link> : c.label}
              </span>
            ))}
          </nav>
        )}
        {eyebrow && (
          <Reveal variant="fade">
            <p className="eyebrow">{eyebrow}</p>
          </Reveal>
        )}
        <Reveal delay={70}>
          <h1 className="display pagehero__title">{title}</h1>
        </Reveal>
        {lead && (
          <Reveal delay={150}>
            <p className="lead pagehero__lead">{lead}</p>
          </Reveal>
        )}
        {children}
        {meta && <div className="pagehero__meta">{meta}</div>}
      </div>
    </header>
  )
}

/* ==========================================================================
   Stat row
   ========================================================================== */

function Stat({ stat }) {
  const { number, suffix } = parseStat(stat.value)
  const animate = stat.count_from !== '' && number !== null
  const [ref, n] = useCountUp(number ?? 0, { start: Number(stat.count_from || 0) })

  return (
    <div className="stat" ref={animate ? ref : undefined}>
      <span className="stat__value">
        {animate ? new Intl.NumberFormat('en-IN').format(n) : stat.value}
        {animate ? suffix : ''}
      </span>
      <span className="stat__label">{stat.label}</span>
      {stat.caption && <span className="stat__caption">{stat.caption}</span>}
    </div>
  )
}

export function StatRow({ stats = [] }) {
  if (!stats.length) return null
  return (
    <div className="stats">
      {stats.map((s) => (
        <Stat key={s.id ?? s.label} stat={s} />
      ))}
    </div>
  )
}

/* ==========================================================================
   Section heading
   ========================================================================== */

/**
 * `index` is accepted and ignored. Sections used to carry a decorative number
 * that never formed a real sequence — a product page ran 03, 04, 05, 07, 08,
 * 10 — so it implied an order that did not exist. The heading carries the
 * hierarchy on its own.
 */
export function SectionHead({ eyebrow, title, lead, action, split = true }) {
  return (
    <div className={`section-head ${split ? 'section-head--split' : ''}`}>
      <div>
        {eyebrow && (
          <Reveal variant="fade">
            <p className="eyebrow">{eyebrow}</p>
          </Reveal>
        )}
        <Reveal delay={60}>
          <h2 className="h2" style={{ marginTop: '1.1rem' }}>
            {title}
          </h2>
        </Reveal>
      </div>
      {(lead || action) && (
        <Reveal delay={130}>
          <div className="stack" style={{ '--flow': '1.5rem' }}>
            {lead && <p className="body">{lead}</p>}
            {action}
          </div>
        </Reveal>
      )}
    </div>
  )
}

/* ==========================================================================
   Accordion (FAQ)
   ========================================================================== */

export function Accordion({ items = [], defaultOpen = null }) {
  const [open, setOpen] = useState(defaultOpen)
  const uid = useId()

  return (
    <div className="acc">
      {items.map((item, i) => {
        const isOpen = open === i
        return (
          <div className={`acc__item ${isOpen ? 'is-open' : ''}`} key={item.id ?? i}>
            <h3>
              <button
                type="button"
                className="acc__btn"
                aria-expanded={isOpen}
                aria-controls={`${uid}-${i}`}
                onClick={() => setOpen(isOpen ? null : i)}
              >
                <span className="acc__q">{item.question}</span>
                <Plus className="acc__icon" size={18} />
              </button>
            </h3>
            <div className="acc__panel" id={`${uid}-${i}`} role="region">
              <div className="acc__panel-inner">
                <div className="acc__a">
                  <p>{item.answer}</p>
                  {item.link_url && item.link_label && (
                    <Link to={item.link_url} className="link">
                      {item.link_label} <Arrow size={14} />
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ==========================================================================
   Cards
   ========================================================================== */

export function LiftCard({ lift, index }) {
  return (
    <article className="card">
      <div className="card__media">
        <Img
          src={lift.hero_image_url}
          alt={lift.name}
          sizes="(min-width: 1100px) 30vw, (min-width: 700px) 46vw, 92vw"
        />
      </div>
      <div className="card__body">
        <p className="card__eyebrow">
          {index != null && <span style={{ opacity: 0.6 }}>{String(index).padStart(2, '0')} · </span>}
          {lift.eyebrow || 'Lift system'}
        </p>
        <h3 className="card__title">
          <Link to={`/lifts/${lift.slug}`} className="card__link">
            {lift.name}
          </Link>
        </h3>
        <p className="card__text">{lift.summary}</p>
        <div className="card__foot">
          {lift.capacity && (
            <span className="card__spec">
              Load <b>{lift.capacity}</b>
            </span>
          )}
          {lift.speed && (
            <span className="card__spec">
              Speed <b>{lift.speed}</b>
            </span>
          )}
          {lift.stops && (
            <span className="card__spec">
              Stops <b>{lift.stops}</b>
            </span>
          )}
        </div>
      </div>
    </article>
  )
}

export function ProjectCard({ project }) {
  return (
    <article className="card">
      <div className="card__media">
        <Img
          src={project.hero_image_url || project.poster_url}
          alt={project.name}
          sizes="(min-width: 1100px) 32vw, (min-width: 700px) 46vw, 92vw"
        />
      </div>
      <div className="card__body">
        <p className="card__eyebrow">
          {project.category?.name}
          {project.year ? ` · ${project.year}` : ''}
        </p>
        <h3 className="card__title">
          <Link to={`/projects/${project.slug}`} className="card__link">
            {project.name}
          </Link>
        </h3>
        <p className="card__text">{project.statement || project.summary}</p>
        <div className="card__foot">
          <span className="card__spec">{project.location}</span>
          {project.system && <span className="card__spec">{project.system}</span>}
        </div>
      </div>
    </article>
  )
}

export function JournalCard({ post }) {
  const date = post.published_at
    ? new Date(post.published_at).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : ''
  return (
    <article className="card">
      <div className="card__media">
        <Img
          src={post.hero_image_url}
          alt={post.title}
          sizes="(min-width: 1100px) 32vw, (min-width: 700px) 46vw, 92vw"
        />
      </div>
      <div className="card__body">
        <p className="card__eyebrow">
          {post.category?.name} · {post.read_minutes} min read
        </p>
        <h3 className="card__title">
          <Link to={`/journal/${post.slug}`} className="card__link">
            {post.title}
          </Link>
        </h3>
        <p className="card__text">{post.excerpt}</p>
        <div className="card__foot">
          <span className="card__spec">{date}</span>
        </div>
      </div>
    </article>
  )
}

/* ==========================================================================
   Testimonials
   ========================================================================== */

export function TestimonialRow({ testimonials = [], title = 'In their words' }) {
  if (!testimonials.length) return null
  return (
    <section className="section on-stone">
      <div className="shell">
        <SectionHead eyebrow="Clients" title={title} split={false} />
        <RevealGroup className="quotegrid">
          {testimonials.map((t) => (
            <figure className="quote" key={t.id}>
              <blockquote className="quote__text">&ldquo;{t.quote}&rdquo;</blockquote>
              <figcaption className="quote__by">
                <strong>{t.organisation || t.name}</strong>
                <span>
                  {t.role}
                  {t.location ? ` · ${t.location}` : ''}
                </span>
                {t.project_slug && (
                  <Link to={`/projects/${t.project_slug}`} className="link">
                    View the project <Arrow size={13} />
                  </Link>
                )}
              </figcaption>
            </figure>
          ))}
        </RevealGroup>
      </div>
    </section>
  )
}

/* ==========================================================================
   Closing CTA used mid-page (the footer carries the site-wide one)
   ========================================================================== */

export function CtaBand({
  eyebrow = 'Next step',
  title,
  lead,
  primary = { to: '/contact', label: 'Get a quote' },
  secondary,
  tone = '',
}) {
  return (
    <section className={`section ctaband ${tone}`}>
      <div className="shell ctaband__inner">
        <Reveal variant="fade">
          <p className="eyebrow">{eyebrow}</p>
        </Reveal>
        <Reveal delay={70}>
          <h2 className="h2 ctaband__title">{title}</h2>
        </Reveal>
        {lead && (
          <Reveal delay={130}>
            <p className="lead">{lead}</p>
          </Reveal>
        )}
        <Reveal delay={190}>
          <div className="ctaband__actions">
            <Link to={primary.to} className="btn btn--accent">
              {primary.label} <Arrow />
            </Link>
            {secondary && (
              <Link to={secondary.to} className="btn btn--ghost">
                {secondary.label} <Arrow />
              </Link>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
