/**
 * Where to go next, when there genuinely is a next place.
 *
 * These are client-side routes, so they are `<Link>`s and not anchors: an
 * assistant that reloads the whole application to move a visitor one page
 * across the site has undone the reason it is a widget rather than a page.
 *
 * Every URL here was verified against the site's own route table before it left
 * the service, so nothing in this component validates one — but it does close
 * the panel on the way out, because leaving a chat window open over the page
 * somebody just asked to see is the small rudeness that makes people close the
 * whole thing.
 *
 * Rendered only when the service sent pages, and the service sends at most
 * three. There is no "see all" and no empty state: a links section that is
 * sometimes empty is a links section people learn to skip.
 */

import { Link } from 'react-router-dom'

import { Arrow } from '@/components/icons'

export default function RelatedPages({ pages, onNavigate }) {
  if (!pages?.length) return null

  return (
    <nav className="asst-related" aria-label="Related pages">
      <p className="asst-related__lead">On the site</p>
      <ul className="asst-related__list">
        {pages.map((page) => (
          <li key={page.url}>
            <Link className="asst-related__card" to={page.url} onClick={onNavigate}>
              <span className="asst-related__title">
                {page.title}
                {page.section ? <span className="asst-related__section">{page.section}</span> : null}
              </span>
              {page.description ? (
                <span className="asst-related__desc">{page.description}</span>
              ) : null}
              <Arrow size={14} className="asst-related__arrow" />
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}
