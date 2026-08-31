/**
 * Provenance for one answer: where it came from, and how sure the service is.
 *
 * Both are collapsed by default. A retrieval-grounded answer is only worth
 * trusting if the sources are checkable, but a panel that opens with five
 * passages of raw chunk text buries the answer itself — so the sources sit one
 * click away and the `[1]` markers in the prose open them at the right entry.
 */

import { useEffect, useRef, useState } from 'react'

import { Alert, Check } from '@/components/icons'

/** A citation's `source` is a URL, a filename, or nothing. Label it either way. */
function label(citation) {
  const { title, source } = citation
  if (title) return title
  if (!source) return 'Reference'
  try {
    const url = new URL(source)
    return `${url.hostname.replace(/^www\./, '')}${url.pathname === '/' ? '' : url.pathname}`
  } catch {
    return source.split(/[\\/]/).pop() || source
  }
}

function href(citation) {
  return /^https?:\/\//i.test(citation.source ?? '') ? citation.source : null
}

/**
 * The service's own confidence in the retrieval behind an answer.
 *
 * Shown only when it is low. A green tick on every high-confidence answer
 * trains people to ignore it, and then the one warning that matters is ignored
 * with the rest.
 */
export function Confidence({ level, score }) {
  if (level !== 'low') return null
  const percent = typeof score === 'number' ? ` (${Math.round(score * 100)}% match)` : ''

  return (
    <p className="asst-confidence">
      <Alert size={14} />
      <span>
        Weak match in our documents{percent} — please confirm this with our engineering team.
      </span>
    </p>
  )
}

export default function Sources({ citations, open, onToggle, active }) {
  const listRef = useRef(null)
  const [copied, setCopied] = useState(null)

  // A marker click opens the panel and scrolls to its entry; without this the
  // source you asked for can land below the fold of a short list.
  useEffect(() => {
    if (!open || active == null) return
    const el = listRef.current?.querySelector(`[data-marker="${active}"]`)
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [open, active])

  useEffect(() => {
    if (copied == null) return
    const t = setTimeout(() => setCopied(null), 1600)
    return () => clearTimeout(t)
  }, [copied])

  if (!citations?.length) return null

  return (
    <div className="asst-sources">
      <button
        type="button"
        className="asst-sources__toggle"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span className="asst-sources__count">{citations.length}</span>
        {citations.length === 1 ? 'source' : 'sources'}
        <span className="asst-sources__chev" aria-hidden="true" />
      </button>

      {open && (
        <ol className="asst-sources__list" ref={listRef}>
          {citations.map((citation, i) => {
            const n = Number(String(citation.marker ?? '').replace(/\D/g, '')) || i + 1
            const link = href(citation)

            return (
              <li
                key={citation.chunk_id ?? i}
                data-marker={n}
                className={`asst-source${active === n ? ' is-active' : ''}`}
              >
                <span className="asst-source__n" aria-hidden="true">
                  {n}
                </span>
                <div className="asst-source__body">
                  {link ? (
                    <a
                      className="asst-source__title"
                      href={link}
                      target="_blank"
                      rel="noreferrer noopener"
                    >
                      {label(citation)}
                    </a>
                  ) : (
                    <p className="asst-source__title">{label(citation)}</p>
                  )}
                  <p className="asst-source__snippet">{citation.snippet}</p>
                  {!link && citation.snippet && (
                    <button
                      type="button"
                      className="asst-source__copy"
                      onClick={() => {
                        navigator.clipboard?.writeText(citation.snippet).then(
                          () => setCopied(n),
                          () => {},
                        )
                      }}
                    >
                      {copied === n ? <Check size={13} /> : null}
                      {copied === n ? 'Copied' : 'Copy passage'}
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}
