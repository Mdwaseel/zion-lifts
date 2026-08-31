import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal from '@/components/Reveal'
import { CtaBand, PageHero, SectionHead } from '@/components/sections'
import { Arrow, Close } from '@/components/icons'
import { useApi, useEscape, useScrollLock } from '@/lib/hooks'
import { srcSet } from '@/lib/media'

import './gallery.css'

const LABELS = {
  all: 'All',
  residential: 'Residential',
  commercial: 'Commercial',
  institutional: 'Institutional',
  interiors: 'Interiors',
  installation: 'Installation',
  factory: 'Factory',
  people: 'People',
  awards: 'Awards',
}

function Lightbox({ items, index, onClose, onMove }) {
  useScrollLock(true)
  useEscape(onClose)

  const onKey = useCallback(
    (e) => {
      if (e.key === 'ArrowRight') onMove(1)
      if (e.key === 'ArrowLeft') onMove(-1)
    },
    [onMove],
  )

  useEffect(() => {
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onKey])

  const item = items[index]
  if (!item) return null

  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label={item.title || 'Image'}>
      <button type="button" className="lightbox__scrim" onClick={onClose} aria-label="Close" />
      <button type="button" className="lightbox__close" onClick={onClose}>
        <Close size={20} />
        <span className="sr-only">Close</span>
      </button>

      <button
        type="button"
        className="lightbox__nav lightbox__nav--prev"
        onClick={() => onMove(-1)}
        aria-label="Previous image"
      >
        <Arrow size={20} style={{ transform: 'rotate(180deg)' }} />
      </button>

      <figure className="lightbox__fig">
        <img src={item.src} srcSet={srcSet(item.src)} sizes="90vw" alt={item.title || ''} />
        <figcaption className="lightbox__cap">
          <span className="lightbox__title">{item.title}</span>
          {item.meta && <span className="lightbox__meta">{item.meta}</span>}
          <span className="lightbox__count mono">
            {index + 1} / {items.length}
          </span>
          {item.project_slug && (
            <Link to={`/projects/${item.project_slug}`} className="link">
              View the project <Arrow size={13} />
            </Link>
          )}
        </figcaption>
      </figure>

      <button
        type="button"
        className="lightbox__nav lightbox__nav--next"
        onClick={() => onMove(1)}
        aria-label="Next image"
      >
        <Arrow size={20} />
      </button>
    </div>
  )
}

export default function Gallery() {
  const { data: items } = useApi('gallery/')
  const [category, setCategory] = useState('all')
  const [open, setOpen] = useState(null)

  useEffect(() => {
    document.title = 'Gallery — Zion Lifts'
  }, [])

  const all = items ?? []

  const categories = useMemo(() => {
    const counts = new Map()
    for (const i of all) counts.set(i.category, (counts.get(i.category) ?? 0) + 1)
    return [['all', all.length], ...[...counts.entries()].sort((a, b) => b[1] - a[1])]
  }, [all])

  const filtered = useMemo(
    () => (category === 'all' ? all : all.filter((i) => i.category === category)),
    [all, category],
  )

  const featured = all.find((i) => i.is_featured)

  const move = useCallback(
    (delta) => setOpen((i) => (i === null ? null : (i + delta + filtered.length) % filtered.length)),
    [filtered.length],
  )

  return (
    <>
      <PageHero
        eyebrow="Zion in motion"
        title="Built. Installed. Experienced."
        lead="Every image here is of a lift Zion made. Cabins, doors, shafts, control panels, buildings — and the installations behind them."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Gallery' }]}
        image="/media/frames/chilkuru-atrium.jpg"
      />

      {featured && (
        <section className="section section--tight">
          <div className="shell">
            <Reveal variant="wipe" className="gfeature">
              <Img
                src={featured.src}
                alt={featured.title}
                ratio="21 / 9"
                sizes="100vw"
                parallax={30}
              />
              <div className="gfeature__cap">
                <p className="mono">{featured.meta}</p>
                <h2 className="gfeature__title">{featured.title}</h2>
                {featured.project_slug && (
                  <Link to={`/projects/${featured.project_slug}`} className="link">
                    View the project <Arrow size={14} />
                  </Link>
                )}
              </div>
            </Reveal>
          </div>
        </section>
      )}

      <section className="section">
        <div className="shell">
          <SectionHead eyebrow="The archive" title="Browse everything." split={false} />

          <div className="filters gfilters">
            {categories.map(([key, count]) => (
              <button
                key={key}
                type="button"
                className={`filters__btn ${category === key ? 'is-on' : ''}`}
                onClick={() => setCategory(key)}
              >
                {LABELS[key] ?? key}
                <sup>{count}</sup>
              </button>
            ))}
          </div>

          <div className="masonry">
            {filtered.map((item, i) => (
              <button
                type="button"
                className={`masonry__cell ${item.aspect < 0.85 ? 'is-tall' : ''}`}
                key={item.id}
                onClick={() => setOpen(i)}
              >
                <Img
                  src={item.src}
                  alt={item.title}
                  ratio={`${item.width} / ${item.height}`}
                  sizes="(min-width: 1200px) 24vw, (min-width: 800px) 32vw, (min-width: 500px) 48vw, 92vw"
                />
                <span className="masonry__hover">
                  <span className="masonry__title">{item.title}</span>
                  {item.meta && <span className="masonry__meta">{item.meta}</span>}
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {open !== null && (
        <Lightbox items={filtered} index={open} onClose={() => setOpen(null)} onMove={move} />
      )}

      <CtaBand
        eyebrow="Next step"
        title="Seen something you like?"
        lead="Any of these can be specified for your building. Tell us which one and what it has to fit into."
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{ to: '/projects', label: 'See the projects' }}
      />
    </>
  )
}
