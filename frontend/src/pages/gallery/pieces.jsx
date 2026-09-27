import { useCallback, useEffect } from 'react'
import { Link } from 'react-router-dom'

import { Arrow, Close } from '@/components/icons'
import { useEscape, useScrollLock } from '@/lib/hooks'
import { srcSet } from '@/lib/media'

/* The lightbox a photograph opens in, shared by the gallery and the project
   pages. Its styles live in gallery.css (`lightbox`). */

/* --- the lightbox ----------------------------------------------------------- */

export function Lightbox({ items, index, onClose, onMove }) {
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

      <button type="button" className="lightbox__nav lightbox__nav--prev" onClick={() => onMove(-1)} aria-label="Previous image">
        <Arrow size={20} style={{ transform: 'rotate(180deg)' }} />
      </button>

      <figure className="lightbox__fig" key={item.id}>
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

      <button type="button" className="lightbox__nav lightbox__nav--next" onClick={() => onMove(1)} aria-label="Next image">
        <Arrow size={20} />
      </button>
    </div>
  )
}

/* --- the opening: the wall -------------------------------------------------
   The whole archive hung as one tilted wall behind the headline, its columns
   drifting past each other, leaning away as the page moves on. */
