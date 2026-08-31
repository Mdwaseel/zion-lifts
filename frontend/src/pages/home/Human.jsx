import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup, SplitLines } from '@/components/Reveal'
import { Arrow, PILLAR_ICONS, Shield } from '@/components/icons'
import { useScrollProgress } from '@/lib/hooks'
import { useSite } from '@/lib/site'

/* ==========================================================================
   13 · AFTER THE INSTALLATION
   The deliberate tonal shift: technical to human.
   ========================================================================== */

export function AfterInstall({ pillars = [] }) {
  return (
    <section className="section on-stone after" aria-labelledby="after-title">
      <div className="shell">
        <div className="after__top">
          <Reveal variant="wipe" className="after__media">
            <Img
              src="/media/frames/lekha-inuse.jpg"
              alt="A Zion lift in daily use"
              ratio="16 / 10"
              sizes="(min-width: 900px) 58vw, 100vw"
              parallax={30}
            />
          </Reveal>
          <div className="after__intro">
            <Reveal variant="fade">
              <p className="eyebrow">
                After the installation
              </p>
            </Reveal>
            <Reveal delay={70}>
              <h2 className="h2 after__title" id="after-title">
                Our work doesn&rsquo;t end
                <br />
                when the doors open.
              </h2>
            </Reveal>
            <Reveal delay={140}>
              <p className="body">
                A lift runs for twenty to twenty-five years before it needs modernising. Most of its
                life happens after the handover, which is the part a maintenance contract is
                actually for.
              </p>
            </Reveal>
            <Reveal delay={200}>
              <Link to="/contact#service" className="btn btn--accent btn--sm">
                Request service <Arrow size={14} />
              </Link>
            </Reveal>
          </div>
        </div>

        <RevealGroup className="pillars" step={80}>
          {pillars.map((p) => {
            const Icon = PILLAR_ICONS[p.icon] ?? Shield
            return (
              <div className="pillar" key={p.slug}>
                <Icon className="pillar__icon" />
                <h3 className="pillar__name">{p.name}</h3>
                <p className="pillar__desc">{p.description}</p>
                {p.detail && <p className="pillar__detail">{p.detail}</p>}
              </div>
            )
          })}
        </RevealGroup>
      </div>
    </section>
  )
}

/* ==========================================================================
   14 · THE PEOPLE
   ========================================================================== */

export function People({ team = [] }) {
  if (!team.length) return null
  return (
    <section className="section people" aria-labelledby="people-title">
      <div className="shell">
        <Reveal variant="fade">
          <p className="eyebrow">
            The people
          </p>
        </Reveal>
        <SplitLines
          as="h2"
          className="h2 people__title"
          lines={['Engineered by people.', 'Built for people.']}
        />

        <RevealGroup className="people__grid" step={90} variant="wipe">
          {team.map((m) => (
            <figure className="person" key={m.id}>
              <Img
                src={m.photo}
                alt={m.name}
                ratio="4 / 5"
                sizes="(min-width: 1000px) 24vw, (min-width: 640px) 46vw, 92vw"
              />
              <figcaption className="person__cap">
                <h3 className="person__name">{m.name}</h3>
                <p className="person__role">{m.role}</p>
                {m.bio && <p className="person__bio">{m.bio}</p>}
              </figcaption>
            </figure>
          ))}
        </RevealGroup>
      </div>
    </section>
  )
}

/* ==========================================================================
   15 · TRUST
   Certification and standards woven into one architectural frame, not a
   badge wall.
   ========================================================================== */

export function Trust({ certifications = [], partners = [] }) {
  const site = useSite()
  return (
    <section className="section section--flush trust" aria-labelledby="trust-title">
      <div className="trust__bg">
        <Img src="/media/frames/chilkuru-atrium.jpg" alt="" sizes="100vw" parallax={40} />
        <div className="trust__veil" aria-hidden="true" />
      </div>

      <div className="shell trust__inner">
        <Reveal variant="fade">
          <p className="eyebrow">
            Trust
          </p>
        </Reveal>
        <Reveal delay={70}>
          <h2 className="h2 trust__title" id="trust-title">
            Trusted by buildings
            <br />
            that move people.
          </h2>
        </Reveal>

        <div className="trust__grid">
          <RevealGroup className="trust__certs" step={90}>
            {certifications.map((c) => (
              <div className="trust__cert" key={c.id}>
                <Shield className="trust__cert-icon" />
                <h3 className="trust__cert-name">{c.name}</h3>
                {c.issuer && <p className="trust__cert-issuer">{c.issuer}</p>}
                {c.description && <p className="trust__cert-desc">{c.description}</p>}
              </div>
            ))}
          </RevealGroup>

          {partners.length > 0 && (
            <Reveal delay={200} className="trust__partners">
              <p className="mono">Systems we build with</p>
              <ul className="trust__partner-list">
                {partners.map((p) => (
                  <li key={p.id}>
                    <strong>{p.name}</strong>
                    {p.component && <span>{p.component}</span>}
                  </li>
                ))}
              </ul>
            </Reveal>
          )}
        </div>

        <Reveal delay={260}>
          <p className="trust__foot">
            {new Intl.NumberFormat('en-IN').format(site.installations)}+ installations across
            residential, commercial, hospitality, healthcare and industrial buildings since{' '}
            {site.founded_year}.
          </p>
        </Reveal>
      </div>
    </section>
  )
}

/* ==========================================================================
   16 · FINAL ASCENT
   Loops back to the hero cabin: doors close, the floors climb, the doors open
   onto a skyline.
   ========================================================================== */

const CLIMB = ['12', '17', '23', '28', '31', '34', '36']

export function FinalAscent() {
  const [ref, progress] = useScrollProgress()
  // doors close over the first 40%, then open onto the skyline after 70%
  const close = Math.min(1, progress / 0.4)
  const reveal = Math.max(0, Math.min(1, (progress - 0.68) / 0.3))
  const shut = Math.max(0, close - reveal * 1.6)
  const floor = CLIMB[Math.min(CLIMB.length - 1, Math.floor(progress * CLIMB.length))]

  return (
    <section ref={ref} className="section section--flush ascent" aria-labelledby="ascent-title">
      <div className="ascent__pin">
        <div className="ascent__stage">
          <div className="ascent__sky" style={{ opacity: 0.35 + reveal * 0.65 }}>
            <Img src="/media/sourced/skyline-hyderabad.jpg" alt="" sizes="100vw" />
          </div>

          <div className="ascent__doors" aria-hidden="true" style={{ '--shut': shut }}>
            <div className="ascent__door ascent__door--l" />
            <div className="ascent__door ascent__door--r" />
          </div>

          <div className="ascent__ticker" aria-hidden="true">
            <span>&uarr;</span>
            <span className="ascent__floor">{floor}</span>
          </div>

          <div className="shell ascent__content" style={{ opacity: reveal }}>
            <p className="eyebrow">
              Final ascent
            </p>
            <h2 className="display ascent__title" id="ascent-title">
              Where should
              <br />
              we take you?
            </h2>
            <div className="ascent__actions">
              <Link to="/contact" className="btn btn--accent">
                Get a quote <Arrow />
              </Link>
              <Link to="/contact#visit" className="btn btn--ghost">
                Arrange a visit <Arrow />
              </Link>
            </div>
          </div>
        </div>
      </div>
      <div className="ascent__runway" aria-hidden="true" />
    </section>
  )
}
