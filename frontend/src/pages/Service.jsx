import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow, PILLAR_ICONS, Phone, Shield } from '@/components/icons'
import SERVICE_PILLARS from '@/data/servicePillars'
import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import ServiceForm from './contact/ServiceForm'
import { Rise, RiseIn, useLightHero, whenIntroDone } from './lift/shared'

import './contact.css'
import './contact-index.css'
import './service.css'

/* ==========================================================================
   /service — for a lift that already exists
   Kept apart from the project enquiry on purpose: somebody with a lift that is
   down should land on a phone number and a short form, not a sales page. The
   number comes first and stays in reach; the form is the quieter route.
   ========================================================================== */

/** Teal, the one ground on the site that is the brand's own colour: a call
    for help should look like it reaches Zion, not like another page. The
    number is set beside a lit call button, and the person who answers is on
    the right. */
function Opening({ phone }) {
  const ref = useRef(null)
  const [shown, setShown] = useState(false)
  useLightHero('flat')

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  return (
    <header ref={ref} className={`sv-hero ${shown ? 'is-in' : ''}`}>
      <div className="sv-hero__copy">
        <h1 className="sv-hero__title">
          <Rise text="Already have a Zion lift?" accent={false} />
        </h1>
        <p className="sv-hero__lead">
          This reaches the service desk directly. We also take on lifts we did not install, subject to a survey.
        </p>

        {/* the number, before anything else on the page */}
        <a className="sv-line" href={telHref(phone)}>
          <span className="sv-line__pulse" aria-hidden="true">
            <Phone size={26} />
          </span>
          <span className="sv-line__copy">
            <span className="sv-line__label">Call the service desk</span>
            <strong className="sv-line__num">{phone}</strong>
          </span>
        </a>
        <a href="#request" className="sv-hero__alt">
          Or send a request <Arrow size={14} />
        </a>
      </div>

      <figure className="sv-hero__who">
        <span className="sv-hero__photo">
          <Img
            src="/media/frames/workshop-assembly.jpg"
            alt="A Zion technician working on a lift car frame"
            priority
            sizes="(min-width: 900px) 40vw, 92vw"
            objectPosition="40% 50%"
          />
        </span>
        <figcaption className="sv-hero__note">
          <strong>Answered 24 hours, every day</strong>
          <span>Breakdowns and entrapments go to the front of the queue.</span>
        </figcaption>
      </figure>
    </header>
  )
}

export default function Service() {
  const site = useSite()
  const pillars = SERVICE_PILLARS
  const phone = site.phone_service || site.phone

  useEffect(() => {
    document.title = 'Service & support — Zion Lifts'
  }, [])

  return (
    <div className="ct sv-page">
      <Opening phone={phone} />

      <section className="ct-sec ct-sec--dark service" id="request">
        <div className="ct-head">
          <div>
            <p className="ld-label">Request service</p>
            <RiseIn as="h2" className="ct-h2" text="Tell the desk what is happening." />
          </div>
          <div className="ct-head__side">
            <p className="ct-lead">
              Two choices and how to reach you is enough. The more you can add, the better prepared the technician
              arrives.
            </p>
          </div>
        </div>

        <div className="ct-shell servicerow">
          <ServiceForm />
          <aside className="servicenote sv-note">
            <p className="servicenote__title">If someone is trapped</p>
            <p className="servicenote__body">
              Press the alarm in the lift — it connects to a battery-backed intercom that reaches us directly,
              independent of the building&rsquo;s power. Then call the number below. Entrapments are prioritised above
              every other call.
            </p>
            <a className="servicenote__phone" href={telHref(phone)}>
              {phone}
            </a>
            <p className="mono">Answered 24 hours, every day of the year</p>
          </aside>
        </div>
      </section>

      {(pillars ?? []).length > 0 && (
        <section className="ct-sec on-stone">
          <div className="ct-head">
            <div>
              <p className="ld-label">What the desk covers</p>
              <RiseIn as="h2" className="ct-h2" text="Five things we stay for." />
            </div>
            <div className="ct-head__side">
              <Link to="/contact" className="link">
                Planning a new lift instead? <Arrow size={14} />
              </Link>
            </div>
          </div>
          <ul className="ct-shell sv-cover">
            {pillars.map((p, i) => {
              const Icon = PILLAR_ICONS[p.icon] ?? Shield
              return (
                <li key={p.slug} className="sv-cover__item" style={{ '--i': i }}>
                  <Icon className="sv-cover__icon" />
                  <h3 className="sv-cover__name">{p.name}</h3>
                  <p className="sv-cover__desc">{p.description}</p>
                  {p.detail && <p className="sv-cover__detail">{p.detail}</p>}
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </div>
  )
}
