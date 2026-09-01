import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { Accordion, SectionHead } from '@/components/sections'
import { Arrow, Chat, Mail, Phone, Pin, Wrench } from '@/components/icons'
import { faqCategories } from '@/data/faqs'
import { useApi } from '@/lib/hooks'
import { telHref, whatsappHref } from '@/lib/media'
import { useSite } from '@/lib/site'

import EnquiryForm, { ProjectSummary } from './contact/EnquiryForm'
import ServiceForm from './contact/ServiceForm'
import './contact.css'

const NEXT_STEPS = [
  ['01', 'We review', 'Your drawings and brief go to an engineer, not a mailbox.'],
  ['02', 'We discuss', 'A call to fill in what a form cannot — constraints, timing, what it has to fit into.'],
  ['03', 'We recommend', 'A system, with the reasons for it and the alternatives we ruled out.'],
  ['04', 'We quote', 'A written quotation against that recommendation, valid for 30 days.'],
]

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
    <>
      {/* --- 01 · HERO, splitting intent immediately --- */}
      <header className="chero">
        <div className="chero__bg">
          <Img src="/media/frames/lekha-hall.jpg" alt="" priority sizes="100vw" />
          <div className="chero__veil" aria-hidden="true" />
        </div>
        <div className="shell chero__inner">
          <Reveal variant="fade">
            <p className="eyebrow">Contact</p>
          </Reveal>
          <Reveal delay={70}>
            <h1 className="display chero__title">Discuss your project.</h1>
          </Reveal>
          <Reveal delay={140}>
            <p className="lead chero__lead">
              Two different conversations, and they should not share a form. Tell us which one this
              is.
            </p>
          </Reveal>
          <RevealGroup className="chero__split" step={90}>
            <a href="#enquiry" className="intent">
              <span className="intent__eyebrow mono">New lift</span>
              <span className="intent__title">I&rsquo;m planning an installation</span>
              <span className="intent__desc">
                New build, retrofit or replacement. Goes to our engineering team.
              </span>
              <span className="intent__go">
                Start a project enquiry <Arrow size={14} />
              </span>
            </a>
            <a href="#service" className="intent intent--service">
              <span className="intent__eyebrow mono">Existing lift</span>
              <span className="intent__title">I need service or support</span>
              <span className="intent__desc">
                Maintenance, a breakdown or modernisation. Goes to the 24/7 service desk.
              </span>
              <span className="intent__go">
                Get service support <Arrow size={14} />
              </span>
            </a>
          </RevealGroup>
        </div>
      </header>

      {/* --- 02 · DIRECT CONTACT --- */}
      <section className="section section--tight">
        <div className="shell">
          <RevealGroup className="direct" step={70}>
            <a className="direct__card" href={telHref(site.phone)}>
              <Phone className="direct__icon" />
              <span className="direct__label mono">Call</span>
              <strong className="direct__value">{site.phone}</strong>
              <span className="direct__note">Speak with our team</span>
            </a>
            {site.whatsapp && (
              <a
                className="direct__card"
                href={whatsappHref(site.whatsapp, "Hello Zion Lifts — I'd like to discuss a project.")}
                target="_blank"
                rel="noreferrer noopener"
              >
                <Chat className="direct__icon" />
                <span className="direct__label mono">WhatsApp</span>
                <strong className="direct__value">Start a chat</strong>
                <span className="direct__note">Fastest for a quick question</span>
              </a>
            )}
            <a className="direct__card" href={`mailto:${site.email}`}>
              <Mail className="direct__icon" />
              <span className="direct__label mono">Email</span>
              <strong className="direct__value">{site.email}</strong>
              <span className="direct__note">Send drawings and a brief</span>
            </a>
            <a className="direct__card direct__card--service" href="#service">
              <Wrench className="direct__icon" />
              <span className="direct__label mono">Service — 24/7</span>
              <strong className="direct__value">{site.phone_service || site.phone}</strong>
              <span className="direct__note">Breakdowns and entrapments first</span>
            </a>
          </RevealGroup>
        </div>
      </section>

      {/* --- 03/04 · PROJECT ENQUIRY + LIVE SUMMARY --- */}
      <section className="section on-stone" id="enquiry">
        <div className="shell">
          <SectionHead
            index="03"
            eyebrow="Project enquiry"
            title="Three steps, then an engineer reads it."
            lead="Nothing here is compulsory except how to reach you. The more you can tell us, the more useful the first call is."
          />
          <div className="enquiryrow">
            <div className="enquiryrow__form">
              <EnquiryForm lifts={lifts ?? []} onSnapshot={setSnapshot} />
            </div>
            <ProjectSummary form={snapshot.form} files={snapshot.files} lifts={lifts ?? []} />
          </div>
        </div>
      </section>

      {/* --- 05 · WHAT HAPPENS NEXT --- */}
      <section className="section section--tight">
        <div className="shell">
          <SectionHead index="05" eyebrow="After you send it" title="What happens next." split={false} />
          <RevealGroup className="nextsteps" step={80}>
            {NEXT_STEPS.map(([n, title, body]) => (
              <div className="nextsteps__step" key={n}>
                <span className="index-num">{n}</span>
                <h3 className="nextsteps__title">{title}</h3>
                <p className="nextsteps__body">{body}</p>
              </div>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 06/07 · VISIT + MAP --- */}
      <section className="section" id="visit">
        <div className="shell">
          <SectionHead
            index="06"
            eyebrow="Come see us"
            title="Two addresses."
            lead="The head office for design conversations; the factory if you want to watch a car being built and load-tested."
          />
          <div className="visit">
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
              <div className="visit__body">
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
                    <a
                      className="btn btn--accent btn--sm"
                      href={current.directions_url}
                      target="_blank"
                      rel="noreferrer noopener"
                    >
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
        </div>
      </section>

      {/* --- 08 · FACILITY --- */}
      <section className="section on-paper section--tight">
        <div className="shell facility">
          <Reveal variant="wipe" className="facility__media">
            <Img
              src="/media/sourced/factory-machining.jpg"
              alt="Machining on the factory floor"
              ratio="16 / 10"
              sizes="(min-width: 900px) 48vw, 100vw"
            />
          </Reveal>
          <div className="facility__copy">
            <Reveal variant="fade">
              <p className="eyebrow">
                <span className="index-num">08</span> The facility
              </p>
            </Reveal>
            <Reveal delay={70}>
              <h2 className="h2">See where Zion is built.</h2>
            </Reveal>
            <Reveal delay={130}>
              <p className="body">
                Fabrication, assembly and load testing all happen at our own unit in Jeedimetla.
                Watching a car get loaded to 125% of its rating tells you more about a lift company
                than any brochure. Visits are by appointment.
              </p>
            </Reveal>
            <Reveal delay={190}>
              <a href="#enquiry" className="link">
                Arrange a facility visit <Arrow size={14} />
              </a>
            </Reveal>
          </div>
        </div>
      </section>

      {/* --- 09 · SERVICE --- */}
      <section className="section service" id="service">
        <div className="shell">
          <SectionHead
            index="09"
            eyebrow="Existing lift · 24/7"
            title="Already have a Zion lift?"
            lead="This reaches the service desk directly. We also take on lifts we did not install, subject to a survey."
          />
          <div className="servicerow">
            <ServiceForm />
            <aside className="servicenote">
              <p className="servicenote__title">If someone is trapped</p>
              <p className="servicenote__body">
                Press the alarm in the car — it connects to a battery-backed intercom that reaches
                us directly, independent of the building&rsquo;s power. Then call the number below.
                Entrapments are prioritised above every other call.
              </p>
              <a className="servicenote__phone" href={telHref(site.phone_service || site.phone)}>
                {site.phone_service || site.phone}
              </a>
              <p className="mono">Answered 24 hours, every day of the year</p>
            </aside>
          </div>
        </div>
      </section>

      {/* --- 10 · CONTACT FAQ --- */}
      {contactFaqs.length > 0 && (
        <section className="section on-stone">
          <div className="shell shell--text">
            <SectionHead
              index="10"
              eyebrow="Before you ask"
              title="Contacting us, in questions."
              action={
                <Link to="/faq" className="link">
                  Every question <Arrow size={14} />
                </Link>
              }
            />
            <Accordion items={contactFaqs} defaultOpen={0} />
          </div>
        </section>
      )}
    </>
  )
}
