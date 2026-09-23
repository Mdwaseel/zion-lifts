import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Arrow, PILLAR_ICONS, Phone, Shield } from '@/components/icons'
import { gsap } from '@/lib/gsap'
import SERVICE_PILLARS from '@/data/servicePillars'
import { useReducedMotion } from '@/lib/hooks'
import { telHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import ServiceForm from './contact/ServiceForm'
import { Rise, RiseIn, clamp01, whenIntroDone } from './lift/shared'

import './contact.css'
import './contact-index.css'
import './service.css'

/* ==========================================================================
   /service — for a lift that already exists
   Kept apart from the project enquiry on purpose: somebody with a lift that is
   down should land on a phone number and a short form, not a sales page. The
   number comes first and stays in reach; the form is the quieter route.
   ========================================================================== */

function Opening({ phone }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(false)

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  useEffect(() => {
    if (reduced) return undefined
    const el = ref.current
    let last = -1
    const tick = () => {
      const p = clamp01(window.scrollY / window.innerHeight)
      if (Math.abs(p - last) < 0.001) return
      last = p
      el.style.setProperty('--x', p.toFixed(4))
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced])

  return (
    <header ref={ref} className={`sv-hero ${shown ? 'is-in' : ''}`}>
      <div className="sv-hero__scene" aria-hidden="true">
        <Img src="/media/frames/kashi-machine.jpg" alt="" priority sizes="100vw" />
      </div>
      <div className="sv-hero__grade" aria-hidden="true" />

      <div className="sv-hero__copy">
        <p className="ld-label sv-hero__label">Existing lift · 24/7</p>
        <h1 className="sv-hero__title">
          <Rise text="Already have a Zion lift?" />
        </h1>
        <p className="sv-hero__lead">
          This reaches the service desk directly. We also take on lifts we did not install, subject to a survey.
        </p>
      </div>

      {/* the number, before anything else on the page */}
      <div className="sv-hero__foot">
        <a className="sv-line" href={telHref(phone)}>
          <span className="sv-line__pulse" aria-hidden="true">
            <Phone size={20} />
          </span>
          <span className="sv-line__copy">
            <span className="sv-line__label">Service desk · answered 24 hours, every day</span>
            <strong className="sv-line__num">{phone}</strong>
          </span>
        </a>
        <a href="#request" className="sv-hero__alt">
          Or send a request <Arrow size={14} />
        </a>
      </div>
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
