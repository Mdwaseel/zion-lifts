import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { CtaBand, JournalCard, PageHero, SectionHead } from '@/components/sections'
import { Arrow } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import './journal.css'

export default function Journal() {
  const { data: posts } = useApi('journal/')
  const { data: categories } = useApi('journal-categories/')
  const [category, setCategory] = useState('all')

  useEffect(() => {
    document.title = 'Journal — Zion Lifts'
  }, [])

  const all = posts ?? []
  const featured = all.find((p) => p.is_featured) ?? all[0]
  const rest = all.filter((p) => p.slug !== featured?.slug)

  const usableCats = useMemo(
    () => (categories ?? []).filter((c) => all.some((p) => p.category?.slug === c.slug)),
    [categories, all],
  )

  const filtered = useMemo(
    () => (category === 'all' ? rest : rest.filter((p) => p.category?.slug === category)),
    [rest, category],
  )

  return (
    <>
      <PageHero
        eyebrow="Zion Journal"
        title="Ideas on vertical mobility."
        lead="Notes from the survey, the factory floor and the service van. Written for architects, builders and anyone about to specify a lift."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Journal' }]}
      />

      {all.length === 0 ? (
        <section className="section">
          <div className="shell state">
            <p className="state__title">Something worth reading is coming.</p>
            <p className="body">
              We&rsquo;re preparing our first collection of insights from the world of vertical
              mobility.
            </p>
            <Link to="/projects" className="btn btn--accent btn--sm">
              Explore our projects <Arrow size={14} />
            </Link>
          </div>
        </section>
      ) : (
        <>
          {featured && (
            <section className="section section--tight">
              <div className="shell">
                <Reveal variant="wipe">
                  <article className="jfeature">
                    <div className="jfeature__media">
                      <Img
                        src={featured.hero_image_url}
                        alt={featured.title}
                        ratio="4 / 3"
                        sizes="(min-width: 900px) 56vw, 100vw"
                      />
                    </div>
                    <div className="jfeature__body">
                      <p className="mono">
                        {featured.category?.name} · {featured.read_minutes} min read
                      </p>
                      <h2 className="jfeature__title">
                        <Link to={`/journal/${featured.slug}`} className="card__link">
                          {featured.title}
                        </Link>
                      </h2>
                      <p className="lead">{featured.excerpt}</p>
                      <span className="link">
                        Read the article <Arrow size={14} />
                      </span>
                    </div>
                  </article>
                </Reveal>
              </div>
            </section>
          )}

          <section className="section">
            <div className="shell">
              <SectionHead eyebrow="Everything else" title="More reading." split={false} />

              {usableCats.length > 1 && (
                <div className="filters jfilters">
                  <button
                    type="button"
                    className={`filters__btn ${category === 'all' ? 'is-on' : ''}`}
                    onClick={() => setCategory('all')}
                  >
                    All<sup>{rest.length}</sup>
                  </button>
                  {usableCats.map((c) => (
                    <button
                      key={c.slug}
                      type="button"
                      className={`filters__btn ${category === c.slug ? 'is-on' : ''}`}
                      onClick={() => setCategory(c.slug)}
                    >
                      {c.name}
                      <sup>{rest.filter((p) => p.category?.slug === c.slug).length}</sup>
                    </button>
                  ))}
                </div>
              )}

              <RevealGroup className="jgrid" step={70}>
                {filtered.map((p) => (
                  <JournalCard key={p.slug} post={p} />
                ))}
              </RevealGroup>
            </div>
          </section>
        </>
      )}

      <CtaBand
        eyebrow="Next step"
        title="Reading is no substitute for a survey."
        lead="If one of these described your situation, the next useful step is putting an engineer in front of the actual building."
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{ to: '/faq', label: 'More questions' }}
      />
    </>
  )
}
