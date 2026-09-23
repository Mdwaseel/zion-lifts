import { Link } from 'react-router-dom'

import { Arrow, Mail, Phone, Pin } from '@/components/icons'
import { useSite } from '@/lib/site'
import { telHref, whatsappHref } from '@/lib/media'

import './Footer.css'

const COLUMNS = [
  {
    title: 'Company',
    links: [
      { to: '/about', label: 'About Zion' },
      { to: '/projects', label: 'Projects' },
      { to: '/gallery', label: 'Gallery' },
      { to: '/journal', label: 'Journal' },
      { to: '/contact', label: 'Contact' },
    ],
  },
  {
    title: 'Lifts',
    links: [
      { to: '/lifts/home-elevator', label: 'Home elevators' },
      { to: '/lifts/capsule-elevator', label: 'Capsule elevators' },
      { to: '/lifts/passenger-elevator', label: 'Commercial passenger' },
      { to: '/lifts/hospital-elevator', label: 'Hospital lifts' },
      { to: '/lifts', label: 'All nine systems' },
    ],
  },
]

/* the marks for the social row; only the ones the site has an address for
   are shown */
const SOCIAL = [
  {
    key: 'linkedin',
    label: 'LinkedIn',
    path: 'M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9h4v12H3zm7 0h3.8v1.7h.1c.5-1 1.8-2 3.7-2 4 0 4.7 2.6 4.7 6V21h-4v-5.3c0-1.3 0-2.9-1.8-2.9s-2 1.4-2 2.8V21h-4z',
  },
  {
    key: 'instagram',
    label: 'Instagram',
    path: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm0 8.2a3.2 3.2 0 1 1 0-6.4 3.2 3.2 0 0 1 0 6.4ZM17.4 5.4a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4ZM12 2c-2.7 0-3 0-4.1.1-2.9.1-4.7 1.9-4.8 4.8C3 8 3 8.3 3 11v2c0 2.7 0 3 .1 4.1.1 2.9 1.9 4.7 4.8 4.8C9 22 9.3 22 12 22s3 0 4.1-.1c2.9-.1 4.7-1.9 4.8-4.8.1-1.1.1-1.4.1-4.1v-2c0-2.7 0-3-.1-4.1-.1-2.9-1.9-4.7-4.8-4.8C15 2 14.7 2 12 2Zm0 1.8c2.7 0 3 0 4 .1 2 .1 3 1.1 3.1 3.1.1 1 .1 1.3.1 4v2c0 2.7 0 3-.1 4-.1 2-1.1 3-3.1 3.1-1 .1-1.3.1-4 .1s-3 0-4-.1c-2-.1-3-1.1-3.1-3.1-.1-1-.1-1.3-.1-4v-2c0-2.7 0-3 .1-4 .1-2 1.1-3 3.1-3.1 1-.1 1.3-.1 4-.1Z',
  },
  {
    key: 'youtube',
    label: 'YouTube',
    path: 'M22.5 7.2a2.7 2.7 0 0 0-1.9-1.9C18.9 4.8 12 4.8 12 4.8s-6.9 0-8.6.5A2.7 2.7 0 0 0 1.5 7.2 28 28 0 0 0 1 12a28 28 0 0 0 .5 4.8 2.7 2.7 0 0 0 1.9 1.9c1.7.5 8.6.5 8.6.5s6.9 0 8.6-.5a2.7 2.7 0 0 0 1.9-1.9A28 28 0 0 0 23 12a28 28 0 0 0-.5-4.8ZM9.8 15.1V8.9l5.7 3.1-5.7 3.1Z',
  },
  {
    key: 'whatsapp',
    label: 'WhatsApp',
    path: 'M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.8 12 12 0 0 0 4.6 4c1.7.7 2.1.6 2.8.5.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.6-.3Z',
  },
]

/* The foot of every page: a white card set in from the edges of the screen.
   The lockup and the statement across the top, then the directory, the ways
   to reach us and the social marks, then the small print. */
export default function Footer() {
  const site = useSite()
  const head = site.offices?.find((o) => o.kind === 'head_office')
  const year = new Date().getFullYear()

  const socials = SOCIAL.map((s) => {
    const href = s.key === 'whatsapp' ? (site.whatsapp ? whatsappHref(site.whatsapp) : '') : site[s.key]
    return href ? { ...s, href } : null
  }).filter(Boolean)

  return (
    <footer className="ft">
      <div className="ft__card">
        <div className="ft__top">
          <div className="ft__brand-wrap">
            <Link to="/" className="ft__brand" aria-label="Zion Lifts — home">
              <img src="/media/brand/lockup-light.png" alt="Zion Lifts" className="ft__logo" />
            </Link>
            <p className="ft__since">
              {site.city}, {site.country} · since {site.founded_year}
            </p>
          </div>
          <p className="ft__statement">{site.statement}</p>
        </div>

        <div className="ft__mid">
          {COLUMNS.map((col) => (
            <nav className="ft__col" key={col.title} aria-label={col.title}>
              <p className="ft__col-title">{col.title}</p>
              <ul>
                {col.links.map((l) => (
                  <li key={l.to}>
                    <Link to={l.to} className="ft__link">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}

          <div className="ft__col ft__col--contact">
            <p className="ft__col-title">Contact</p>
            <ul>
              <li>
                <a href={`mailto:${site.email}`} className="ft__reach">
                  <span className="ft__reach-icon">
                    <Mail size={15} aria-hidden="true" />
                  </span>
                  {site.email}
                </a>
              </li>
              <li>
                <a href={telHref(site.phone)} className="ft__reach">
                  <span className="ft__reach-icon">
                    <Phone size={15} aria-hidden="true" />
                  </span>
                  {site.phone}
                </a>
              </li>
              <li>
                <a
                  href={head?.directions_url || 'https://www.google.com/maps/search/?api=1&query=Zion+Lifts+Hyderabad'}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="ft__reach"
                >
                  <span className="ft__reach-icon">
                    <Pin size={15} aria-hidden="true" />
                  </span>
                  {head?.locality ? `${head.locality}, ` : ''}
                  {site.city}, {site.country}
                </a>
              </li>
            </ul>
            {head?.hours && <p className="ft__hours">{head.hours}</p>}
          </div>

          <div className="ft__aside">
            <Link to="/contact" className="ft__quote">
              <span>Get a quote</span>
              <span className="ft__quote-ring" aria-hidden="true">
                <Arrow size={14} />
              </span>
            </Link>
            {socials.length > 0 && (
              <ul className="ft__social" aria-label="Zion Lifts elsewhere">
                {socials.map((s) => (
                  <li key={s.key}>
                    <a href={s.href} target="_blank" rel="noreferrer noopener" aria-label={s.label} className="ft__social-link">
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d={s.path} />
                      </svg>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="ft__base">
          <p>
            © {year} {site.company_name} Pvt. Ltd. All rights reserved.
          </p>
          <nav className="ft__legal" aria-label="Legal">
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/cookies">Cookies</Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}
