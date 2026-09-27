import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import { Accordion } from '@/components/sections'
import { Arrow, Chat, Mail, Phone, Pin, Wrench } from '@/components/icons'
import { faqCategories } from '@/data/faqs'
import { useApi } from '@/lib/hooks'
import { telHref, whatsappHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import EnquiryForm, { ProjectSummary } from './contact/EnquiryForm'
import { Rise, RiseIn, useLightHero, useScrollVar, whenIntroDone } from './lift/shared'

import './contact.css'
import './projects-index.css'
import './contact-index.css'

const NEXT_STEPS = [
  ['01', 'We review', 'Your drawings and brief go to an engineer, not a mailbox.'],
  ['02', 'We discuss', 'A call to fill in what a form cannot — constraints, timing, what it has to fit into.'],
  ['03', 'We recommend', 'A system, with the reasons for it and the alternatives we ruled out.'],
  ['04', 'We quote', 'A written quotation against that recommendation, valid for 30 days.'],
]

/* --- a section's head: label, a line that rises, and what it is for -------- */

function Head({ label, title, lead, action }) {
  return (
    <div className="ct-head">
      <div>
        <p className="ld-label">{label}</p>
        <RiseIn as="h2" className="ct-h2" text={title} />
      </div>
      {(lead || action) && (
        <div className="ct-head__side">
          {lead && <p className="ct-lead">{lead}</p>}
          {action}
        </div>
      )}
    </div>
  )
}

/* --- the opening: two doors -------------------------------------------------
   There are two reasons to write to a lift company, and a landing already has
   a control for exactly that: an up button and a down button. Up is a new
   lift; down is one that needs attention. Each is a large photograph with its
   call button on it, and pointing at one lights the button. */

const CALLS = [
  {
    key: 'up',
    href: '/contact#enquiry',
    label: 'New lift',
    title: 'I’m planning an installation',
    desc: 'New build, retrofit or replacement. Goes to our engineering team.',
    go: 'Start a project enquiry',
    src: '/media/frames/lekha-hall.jpg',
  },
  {
    key: 'down',
    href: '/service',
    label: 'Existing lift',
    title: 'I need service or support',
    desc: 'Maintenance, a breakdown or modernisation. Goes to the 24/7 service desk.',
    go: 'Get service support',
    src: '/media/frames/kashi-machine.jpg',
  },
]

function Opening({ site }) {
  const ref = useRef(null)
  const [shown, setShown] = useState(false)
  useLightHero()

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  const direct = [
    { Icon: Phone, label: 'Call', value: site.phone, href: telHref(site.phone) },
    site.whatsapp && {
      Icon: Chat,
      label: 'WhatsApp',
      value: 'Start a chat',
      href: whatsappHref(site.whatsapp, "Hello Zion Lifts — I'd like to discuss a project."),
      external: true,
    },
    { Icon: Mail, label: 'Email', value: site.email, href: `mailto:${site.email}` },
    { Icon: Wrench, label: 'Service · 24/7', value: site.phone_service || site.phone, href: telHref(site.phone_service || site.phone) },
  ].filter(Boolean)

  return (
    <header ref={ref} className={`ct-hero ${shown ? 'is-in' : ''}`}>
      <div className="ct-hero__copy">
        <h1 className="ct-hero__title">
          <Rise text="Discuss your project." accent={false} />
        </h1>
        <p className="ct-hero__lead">
          Two different conversations, and they should not share a form. Press the one this is.
        </p>
      </div>

      <nav className="ct-doors" aria-label="What this is about">
        {CALLS.map((c, i) => (
          <Link key={c.key} to={c.href} className={`ct-door ct-door--${c.key}`} style={{ '--i': i }}>
            <span className="ct-door__media" aria-hidden="true">
              <Img src={c.src} alt="" priority sizes="(min-width: 900px) 46vw, 92vw" />
            </span>
            <span className="ct-door__btn" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d={c.key === 'up' ? 'M12 6.5 19 17H5Z' : 'M12 17.5 5 7h14Z'} />
              </svg>
            </span>
            <span className="ct-door__copy">
              <span className="ct-door__label">{c.label}</span>
              <strong className="ct-door__title">{c.title}</strong>
              <span className="ct-door__desc">{c.desc}</span>
              <span className="ct-door__go">
                {c.go} <Arrow size={13} />
              </span>
            </span>
          </Link>
        ))}
      </nav>

      <div className="ct-hero__foot">
        {direct.map((d, i) => (
          <a
            key={d.label}
            href={d.href}
            className="ct-direct"
            style={{ '--i': i }}
            {...(d.external ? { target: '_blank', rel: 'noreferrer noopener' } : {})}
          >
            <d.Icon className="ct-direct__icon" />
            <span className="ct-direct__label">{d.label}</span>
            <strong className="ct-direct__value">{d.value}</strong>
          </a>
        ))}
      </div>
    </header>
  )
}

/* --- what happens next: a line that is drawn as you read along it ----------- */

function NextSteps() {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.85, to: 0.3 })

  return (
    <section className="ct-next">
      <Head label="After you send it" title="What happens next." />
      <ol ref={ref} className="ct-next__row">
        {NEXT_STEPS.map(([n, title, body], i) => (
          <li className="ct-next__step" key={n} style={{ '--i': i }}>
            <span className="ct-next__dot" aria-hidden="true" />
            <p className="ct-next__n">{n}</p>
            <h3 className="ct-next__title">{title}</h3>
            <p className="ct-next__body">{body}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

/* --- the facility: a frame that opens --------------------------------------- */

function Facility() {
  const wrap = useRef(null)
  useScrollVar(wrap, { from: 1, to: 0.15 })

  return (
    <div ref={wrap} className="pr-invite-wrap">
      <section className="pr-invite">
        <div className="pr-invite__scene">
          <Img src="/media/frames/workshop-sparks.jpg" alt="" sizes="100vw" objectPosition="60% 50%" />
        </div>
        <div className="pr-invite__copy">
          <p className="ld-label">The facility</p>
          <h2 className="pr-invite__title ld-rise">
            <Rise text="See where Zion is built." />
          </h2>
          <p className="pr-invite__lead">
            Fabrication, assembly and load testing all happen at our own unit in Jeedimetla. Watching a lift get
            loaded to 125% of its rating tells you more about a manufacturer than any brochure. Visits are by
            appointment.
          </p>
          <div className="pr-invite__actions">
            <a href="#enquiry" className="pr-go">
              <span>Arrange a facility visit</span>
              <span className="pr-go__ring">
                <Arrow size={16} />
              </span>
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}

export default function Contact() {
  const site = useSite()
  const { data: lifts } = useApi('lifts/')
  const [office, setOffice] = useState('head_office')
  // mirrored out of the enquiry form so the live summary can read it
  const [snapshot, setSnapshot] = useState({ form: {}, files: [] })

  useEffect(() => {
    document.title = 'Contact — Zion Lifts'
  }, [])

  const offices = site.offices ?? []
  const current = offices.find((o) => o.kind === office) ?? offices[0]
  const contactFaqs = faqCategories('contact').flatMap((c) => c.questions)

  return (
    <div className="ct">
      <Opening site={site} />

      {/* --- project enquiry + live summary --- */}
      <section className="ct-sec on-paper ct-readable ct-sec--white" id="enquiry">
        <Head
          label="Project enquiry"
          title="Three steps, then an engineer reads it."
          lead="Nothing here is compulsory except how to reach you. The more you can tell us, the more useful the first call is."
        />
        <div className="ct-shell enquiryrow">
          <div className="enquiryrow__form">
            <EnquiryForm lifts={lifts ?? []} onSnapshot={setSnapshot} />
          </div>
          <ProjectSummary form={snapshot.form} files={snapshot.files} lifts={lifts ?? []} />
        </div>
      </section>

      <NextSteps />

      {/* --- visit + map --- */}
      <section className="ct-sec on-paper ct-readable" id="visit">
        <Head
          label="Come see us"
          title="Two addresses."
          lead="The head office for design conversations; the factory if you want to watch a lift being built and load-tested."
        />
        <div className="ct-shell visit">
          <div className="visit__toggle" role="tablist" aria-label="Locations">
            {offices.map((o) => (
              <button
                key={o.kind}
                type="button"
                role="tab"
                aria-selected={office === o.kind}
                className={`visit__tab ${office === o.kind ? 'is-on' : ''}`}
                onClick={() => setOffice(o.kind)}
              >
                {o.kind_display}
              </button>
            ))}
          </div>

          {current && (
            <div className="visit__body ct-visit" key={current.kind}>
              <div className="visit__panel">
                <Pin className="visit__icon" />
                <h3 className="visit__name">{current.name}</h3>
                <address className="visit__address">
                  {current.address.split('\n').map((l) => (
                    <span key={l}>{l}</span>
                  ))}
                  <span>
                    {current.city}, {current.state} {current.postcode}
                  </span>
                </address>
                <dl className="visit__meta">
                  {current.phone && (
                    <div>
                      <dt>Phone</dt>
                      <dd>
                        <a href={telHref(current.phone)}>{current.phone}</a>
                      </dd>
                    </div>
                  )}
                  {current.email && (
                    <div>
                      <dt>Email</dt>
                      <dd>
                        <a href={`mailto:${current.email}`}>{current.email}</a>
                      </dd>
                    </div>
                  )}
                  {current.hours && (
                    <div>
                      <dt>Hours</dt>
                      <dd>{current.hours}</dd>
                    </div>
                  )}
                </dl>
                {current.note && <p className="visit__note">{current.note}</p>}
                {current.directions_url && (
                  <a className="btn btn--accent btn--sm" href={current.directions_url} target="_blank" rel="noreferrer noopener">
                    Get directions <Arrow size={14} />
                  </a>
                )}
              </div>
              <div className="visit__map">
                {current.map_embed_url ? (
                  <iframe
                    title={`Map of ${current.name}`}
                    src={current.map_embed_url}
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                  />
                ) : (
                  <div className="visit__map-fallback">
                    <p className="mono">Map unavailable</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </section>

      <Facility />

      {/* --- contact FAQ --- */}
      {contactFaqs.length > 0 && (
        <section className="ct-sec on-stone ct-readable">
          <Head
            label="Before you ask"
            title="Contacting us, in questions."
            action={
              <Link to="/faq" className="link">
                Every question <Arrow size={14} />
              </Link>
            }
          />
          <div className="ct-shell ct-shell--text">
            <Accordion items={contactFaqs} defaultOpen={0} />
          </div>
        </section>
      )}
    </div>
  )
}
