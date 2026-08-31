import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { CtaBand, JournalCard, SectionHead } from '@/components/sections'
import { Arrow } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import './journal.css'

/**
 * The body is stored as light markup: `## ` opens a section, `> ` is a pull
 * quote, `**bold**` is inline emphasis, blank lines split paragraphs.
 */
function parseBody(body = '') {
  const blocks = []
  for (const raw of body.split('\n\n')) {
    const chunk = raw.trim()
    if (!chunk) continue
    if (chunk.startsWith('## ')) {
      blocks.push({ type: 'h2', text: chunk.slice(3).trim() })
    } else if (chunk.startsWith('> ')) {
      blocks.push({ type: 'quote', text: chunk.slice(2).trim() })
    } else {
      blocks.push({ type: 'p', text: chunk })
    }
  }
  return blocks
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

/** Renders **bold** spans without dropping to dangerouslySetInnerHTML. */
function Rich({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  )
}

export default function JournalDetail() {
  const { slug } = useParams()
  const { data: post, loading, error } = useApi(slug ? `journal/${slug}/` : null)
  const [activeHeading, setActiveHeading] = useState(null)

  useEffect(() => {
    if (post) document.title = `${post.title} — Zion Journal`
  }, [post])

  const blocks = useMemo(() => parseBody(post?.body), [post?.body])
  const headings = useMemo(
    () => blocks.filter((b) => b.type === 'h2').map((b) => ({ id: slugify(b.text), text: b.text })),
    [blocks],
  )

  // highlight the section currently under the masthead
  useEffect(() => {
    if (!headings.length) return
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActiveHeading(visible[0].target.id)
      },
      { rootMargin: '-20% 0px -70% 0px' },
    )
    for (const h of headings) {
      const el = document.getElementById(h.id)
      if (el) io.observe(el)
    }
    return () => io.disconnect()
  }, [headings])

  if (loading) {
    return (
      <div className="section">
        <div className="shell">
          <div className="skeleton" style={{ height: '60vh' }} />
        </div>
      </div>
    )
  }

  if (error || !post) {
    return (
      <section className="section">
        <div className="shell state">
          <p className="state__title">We could not find that article.</p>
          <Link to="/journal" className="btn btn--accent btn--sm">
            All articles <Arrow size={14} />
          </Link>
        </div>
      </section>
    )
  }

  const date = post.published_at
    ? new Date(post.published_at).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    : ''

  return (
    <>
      <header className="jhero">
        <div className="shell jhero__inner">
          <nav className="pagehero__crumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span aria-hidden="true">/</span>
            <Link to="/journal">Journal</Link>
          </nav>
          <p className="eyebrow">{post.category?.name}</p>
          <h1 className="display jhero__title">{post.title}</h1>
          <p className="lead jhero__excerpt">{post.excerpt}</p>
          <p className="jhero__meta mono">
            {date} · {post.read_minutes} min read
          </p>
        </div>
        {post.hero_image_url && (
          <div className="shell">
            <Reveal variant="wipe" className="jhero__media">
              <Img
                src={post.hero_image_url}
                alt=""
                ratio="21 / 9"
                priority
                sizes="100vw"
              />
            </Reveal>
          </div>
        )}
      </header>

      <section className="section section--tight">
        <div className="shell jlayout">
          {headings.length > 1 && (
            <aside className="jtoc">
              <p className="jtoc__title mono">Contents</p>
              <ol className="jtoc__list">
                {headings.map((h, i) => (
                  <li key={h.id}>
                    <a
                      href={`#${h.id}`}
                      className={activeHeading === h.id ? 'is-on' : ''}
                    >
                      <span className="jtoc__n">{String(i + 1).padStart(2, '0')}</span>
                      {h.text}
                    </a>
                  </li>
                ))}
              </ol>
            </aside>
          )}

          <article className="jbody">
            {blocks.map((b, i) => {
              if (b.type === 'h2') {
                return (
                  <h2 className="jbody__h2" id={slugify(b.text)} key={i}>
                    {b.text}
                  </h2>
                )
              }
              if (b.type === 'quote') {
                return (
                  <blockquote className="jbody__quote" key={i}>
                    <Rich text={b.text} />
                  </blockquote>
                )
              }
              return (
                <p className="jbody__p" key={i}>
                  <Rich text={b.text} />
                </p>
              )
            })}
          </article>
        </div>
      </section>

      {post.related?.length > 0 && (
        <section className="section on-stone">
          <div className="shell">
            <SectionHead
              eyebrow="Keep reading"
              title="Related articles."
              action={
                <Link to="/journal" className="link">
                  All articles <Arrow size={14} />
                </Link>
              }
            />
            <RevealGroup className="jgrid" step={70}>
              {post.related.map((p) => (
                <JournalCard key={p.slug} post={p} />
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      <CtaBand
        eyebrow="Next step"
        title="Have a building in mind?"
        lead="Send a plan and the number of levels. We will answer the version of this question that applies to you."
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{ to: '/lifts', label: 'See the range' }}
      />
    </>
  )
}
