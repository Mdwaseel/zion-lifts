import { Link } from 'react-router-dom'

import { Arrow, Chat, Phone } from '@/components/icons'
import { telHref, whatsappHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import './Asks.css'

/* The asks a page offers where its reader decides: the quote in words, and
   the phone and WhatsApp beside it. Every quote lands on the enquiry form with
   the lift already chosen and, from a case study, the building named in the
   brief — so the visitor starts halfway through the form, and the engineer
   reading it knows what brought them. */

/** the enquiry form, opened on this lift and, when given, this building */
export function quoteHref({ lift, like } = {}) {
  const q = new URLSearchParams()
  if (lift) q.set('lift', lift)
  if (like) q.set('like', like)
  const qs = q.toString()
  return `/contact${qs ? `?${qs}` : ''}#enquiry`
}

/**
 * `label` is the quote button's words; `short` is what it shrinks to on a
 * phone in the compact row. `whatsapp` is the message the chat opens with.
 */
export function Asks({ to, label = 'Get a quote', short, whatsapp, tone = 'light', compact = false }) {
  const site = useSite()
  const wa = site?.whatsapp || site?.phone
  return (
    <div className={`asks asks--${tone} ${compact ? 'asks--compact' : ''}`}>
      <Link to={to} className="asks__go">
        {short && compact ? (
          <span>
            {short}
            <span className="asks__more">{label.slice(short.length)}</span>
          </span>
        ) : (
          label
        )}{' '}
        <Arrow size={14} />
      </Link>
      {site?.phone && (
        <a
          href={telHref(site.phone)}
          className="asks__alt"
          aria-label={compact ? `Call ${site.phone}` : undefined}
          title={compact ? `Call ${site.phone}` : undefined}
        >
          <Phone size={16} /> {!compact && site.phone}
        </a>
      )}
      {wa && (
        <a
          href={whatsappHref(wa, whatsapp)}
          className="asks__alt"
          target="_blank"
          rel="noreferrer noopener"
          aria-label={compact ? 'Message us on WhatsApp' : undefined}
          title={compact ? 'Message us on WhatsApp' : undefined}
        >
          <Chat size={16} /> {!compact && 'WhatsApp'}
        </a>
      )}
    </div>
  )
}

/** the brand's teal, a question the reader is already asking, and the asks */
export function AskBand({ id, title, lead, className = '', ...asks }) {
  return (
    <section className={`ask-band ${className}`} aria-labelledby={id}>
      <div className="ask-band__in">
        <div>
          <h2 id={id} className="ask-band__title">
            {title}
          </h2>
          {lead && <p className="ask-band__lead">{lead}</p>}
        </div>
        <Asks tone="dark" {...asks} />
      </div>
    </section>
  )
}
