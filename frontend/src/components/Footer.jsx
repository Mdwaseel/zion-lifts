import { Link } from 'react-router-dom'

import { useSite } from '@/lib/site'
import { telHref, whatsappHref } from '@/lib/media'

import { Arrow } from './icons'
import './Footer.css'

const COLUMNS = [
  {
    title: 'Lifts',
    links: [
      { to: '/lifts/home-elevator', label: 'Home elevators' },
      { to: '/lifts/capsule-elevator', label: 'Capsule elevators' },
      { to: '/lifts/mrl-traction', label: 'MRL traction' },
      { to: '/lifts/hydraulic-elevator', label: 'Hydraulic' },
      { to: '/lifts/passenger-elevator', label: 'Commercial passenger' },
      { to: '/lifts/hospital-elevator', label: 'Hospital' },
      { to: '/lifts/goods-elevator', label: 'Goods & freight' },
      { to: '/lifts/dumbwaiter', label: 'Dumbwaiters' },
      { to: '/lifts/car-stacker', label: 'Car stackers' },
    ],
  },
  {
    title: 'Explore',
    links: [
      { to: '/projects', label: 'Projects' },
      { to: '/gallery', label: 'Gallery' },
      { to: '/about', label: 'About Zion' },
      { to: '/journal', label: 'Journal' },
      { to: '/faq', label: 'FAQ' },
    ],
  },
]

export default function Footer() {
  const site = useSite()
  const head = site.offices?.find((o) => o.kind === 'head_office')
  const factory = site.offices?.find((o) => o.kind === 'factory')
  const year = new Date().getFullYear()

  return (
    <footer className="footer">
      {/* --- closing CTA ------------------------------------------------- */}
      <div className="footer__cta">
        <div className="shell footer__cta-inner">
          <p className="eyebrow">Where should we take you?</p>
          <h2 className="display footer__cta-title">
            Tell us what
            <br />
            you&rsquo;re building.
          </h2>
          <div className="footer__cta-actions">
            <Link to="/contact" className="btn btn--accent">
              Get a quote <Arrow />
            </Link>
            <Link to="/contact#visit" className="btn btn--ghost">
              Arrange a visit <Arrow />
            </Link>
          </div>
        </div>
      </div>

      {/* --- link grid --------------------------------------------------- */}
      <div className="shell footer__grid">
        <div className="footer__brand">
          <img src="/media/brand/lockup-light.png" alt="Zion Lifts" className="footer__logo" />
          <p className="footer__statement">{site.statement}</p>
          <p className="mono footer__since">
            {site.city}, {site.country} — since {site.founded_year}
          </p>
        </div>

        {COLUMNS.map((col) => (
          <nav className="footer__col" key={col.title} aria-label={col.title}>
            <p className="footer__col-title">{col.title}</p>
            <ul>
              {col.links.map((l) => (
                <li key={l.to}>
                  <Link to={l.to}>{l.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}

        <div className="footer__col">
          <p className="footer__col-title">Reach us</p>
          <ul>
            <li>
              <a href={telHref(site.phone)}>{site.phone}</a>
            </li>
            {site.whatsapp && (
              <li>
                <a href={whatsappHref(site.whatsapp)} target="_blank" rel="noreferrer noopener">
                  WhatsApp
                </a>
              </li>
            )}
            <li>
              <a href={`mailto:${site.email}`}>{site.email}</a>
            </li>
            {site.email_service && (
              <li>
                <a href={`mailto:${site.email_service}`}>{site.email_service}</a>
              </li>
            )}
          </ul>
          <p className="footer__note">24/7 after-sales support</p>
        </div>

        <div className="footer__col">
          <p className="footer__col-title">Visit</p>
          {head && (
            <address className="footer__address">
              <strong>Head office</strong>
              {head.address.split('\n').map((line) => (
                <span key={line}>{line}</span>
              ))}
              <span>
                {head.city} {head.postcode}
              </span>
              {head.hours && <span className="footer__hours">{head.hours}</span>}
            </address>
          )}
          {factory && (
            <address className="footer__address">
              <strong>Factory</strong>
              {factory.address.split('\n').map((line) => (
                <span key={line}>{line}</span>
              ))}
              <span>
                {factory.city} {factory.postcode}
              </span>
            </address>
          )}
        </div>
      </div>

      {/* --- baseline ---------------------------------------------------- */}
      <div className="shell footer__base">
        <p className="small">
          © {year} {site.company_name} Pvt. Ltd. All rights reserved.
        </p>
        <nav className="footer__legal" aria-label="Legal">
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
          <Link to="/cookies">Cookies</Link>
        </nav>
      </div>
    </footer>
  )
}
