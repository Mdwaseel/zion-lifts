import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoLoop } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { CtaBand, PageHero, ProjectCard, SectionHead, StatRow } from '@/components/sections'
import { Arrow } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import './projects.css'

export default function Projects() {
  const { data: projects } = useApi('projects/')
  const { data: categories } = useApi('project-categories/')
  const { data: lifts } = useApi('lifts/')
  const { data: stats } = useApi('stats/', { group: 'projects' })

  const [category, setCategory] = useState('all')
  const [liftType, setLiftType] = useState('all')

  useEffect(() => {
    document.title = 'Projects — Zion Lifts'
  }, [])

  const all = projects ?? []
  const featured = all.find((p) => p.is_featured) ?? all[0]

  const filtered = useMemo(
    () =>
      all.filter(
        (p) =>
          (category === 'all' || p.category?.slug === category) &&
          (liftType === 'all' || p.lift_type_slug === liftType),
      ),
    [all, category, liftType],
  )

  // only offer filters that would actually return something
  const usableCats = (categories ?? []).filter((c) => c.count > 0)
  const usableLifts = (lifts ?? []).filter((l) => all.some((p) => p.lift_type_slug === l.slug))

  return (
    <>
      <PageHero
        eyebrow="Proof of delivery"
        title="Real buildings. Real installations."
        lead="Every photograph and film on this page is of a lift Zion designed, built and installed. Nothing here is a render standing in for a job we have not done."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Projects' }]}
        image="/media/frames/lekha-aerial.jpg"
      />

      <section className="section section--tight">
        <div className="shell">
          <StatRow stats={stats ?? []} />
        </div>
      </section>

      {/* --- featured case study --- */}
      {featured && (
        <section className="section section--tight">
          <div className="shell">
            <SectionHead eyebrow="Featured" title="The one to start with." split={false} />
            <Reveal variant="wipe" className="feature">
              <div className="feature__media">
                {featured.loop_video_url ? (
                  <VideoLoop
                    src={featured.loop_video_url}
                    poster={featured.poster_url || featured.hero_image_url}
                    ratio="16 / 9"
                  />
                ) : (
                  <Img
                    src={featured.hero_image_url}
                    alt={featured.name}
                    ratio="16 / 9"
                    sizes="100vw"
                  />
                )}
              </div>
              <div className="feature__body">
                <p className="mono">
                  {featured.category?.name}
                  {featured.year ? ` · ${featured.year}` : ''}
                </p>
                <h3 className="feature__title">{featured.name}</h3>
                <p className="lead">{featured.statement}</p>
                <dl className="feature__meta">
                  {[
                    ['Location', featured.location],
                    ['System', featured.system],
                    ['Capacity', featured.capacity],
                    ['Stops', featured.stops],
                  ]
                    .filter(([, v]) => v)
                    .map(([k, v]) => (
                      <div key={k}>
                        <dt>{k}</dt>
                        <dd>{v}</dd>
                      </div>
                    ))}
                </dl>
                <Link to={`/projects/${featured.slug}`} className="btn btn--accent btn--sm">
                  View case study <Arrow size={14} />
                </Link>
              </div>
            </Reveal>
          </div>
        </section>
      )}

      {/* --- filters + grid --- */}
      <section className="section">
        <div className="shell">
          <SectionHead eyebrow="Every project" title="Browse the work." split={false} />

          <div className="projectfilters">
            <div className="filters">
              <span className="projectfilters__label mono">Building</span>
              <button
                type="button"
                className={`filters__btn ${category === 'all' ? 'is-on' : ''}`}
                onClick={() => setCategory('all')}
              >
                All<sup>{all.length}</sup>
              </button>
              {usableCats.map((c) => (
                <button
                  key={c.slug}
                  type="button"
                  className={`filters__btn ${category === c.slug ? 'is-on' : ''}`}
                  onClick={() => setCategory(c.slug)}
                >
                  {c.name}
                  <sup>{c.count}</sup>
                </button>
              ))}
            </div>

            {usableLifts.length > 1 && (
              <div className="filters">
                <span className="projectfilters__label mono">System</span>
                <button
                  type="button"
                  className={`filters__btn ${liftType === 'all' ? 'is-on' : ''}`}
                  onClick={() => setLiftType('all')}
                >
                  All
                </button>
                {usableLifts.map((l) => (
                  <button
                    key={l.slug}
                    type="button"
                    className={`filters__btn ${liftType === l.slug ? 'is-on' : ''}`}
                    onClick={() => setLiftType(l.slug)}
                  >
                    {l.short_name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {filtered.length ? (
            <RevealGroup className="projectgrid" step={70}>
              {filtered.map((p) => (
                <ProjectCard key={p.slug} project={p} />
              ))}
            </RevealGroup>
          ) : (
            <div className="state">
              <p className="state__title">No projects match that combination yet.</p>
              <button
                type="button"
                className="link"
                onClick={() => {
                  setCategory('all')
                  setLiftType('all')
                }}
              >
                Clear the filters <Arrow size={14} />
              </button>
            </div>
          )}
        </div>
      </section>

      <CtaBand
        eyebrow="Next step"
        title="Planning something similar?"
        lead="Send the building type and the number of levels. We will tell you which of these projects yours most resembles, and what it would take."
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{ to: '/gallery', label: 'See the gallery' }}
      />
    </>
  )
}
