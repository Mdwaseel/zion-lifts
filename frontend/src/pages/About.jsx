import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup, SplitLines } from '@/components/Reveal'
import { CtaBand, SectionHead, StatRow } from '@/components/sections'
import { Arrow, PILLAR_ICONS, Shield } from '@/components/icons'
import CERTIFICATIONS from '@/data/certifications'
import MILESTONES from '@/data/milestones'
import SERVICE_PILLARS from '@/data/servicePillars'
import { statsFor } from '@/data/stats'
import { useApi, useCountUp, useScrollProgress } from '@/lib/hooks'
import { useSite } from '@/lib/site'

import './about.css'

/* --- 04 · THE ZION JOURNEY ------------------------------------------------ */

function Journey({ milestones }) {
  const [active, setActive] = useState(0)
  if (!milestones?.length) return null
  const m = milestones[active]

  return (
    <section className="section journey" id="journey">
      <div className="shell">
        <SectionHead
          index="04"
          eyebrow="The journey"
          title="Thirteen years, in the order they happened."
          lead="Only real milestones. We would rather show six honest ones than pad it out to twenty."
        />
      </div>

      <div className="journey__body">
        <div className="journey__stage">
          {milestones.map((item, i) => (
            <div key={item.year} className={`journey__plate ${i === active ? 'is-on' : ''}`}>
              <Img src={item.image_url} alt="" sizes="(min-width: 900px) 55vw, 100vw" />
            </div>
          ))}
          <div className="journey__veil" aria-hidden="true" />
          <p className="journey__bigyear" aria-hidden="true">
            {m.year}
          </p>
        </div>

        <div className="journey__panel">
          <ol className="journey__rail">
            {milestones.map((item, i) => (
              <li key={item.year}>
                <button
                  type="button"
                  className={`journey__dot ${i === active ? 'is-on' : ''}`}
                  onClick={() => setActive(i)}
                  aria-pressed={i === active}
                >
                  <span className="journey__dot-mark" aria-hidden="true" />
                  <span className="journey__dot-year">{item.year}</span>
                </button>
              </li>
            ))}
          </ol>
          <div className="journey__detail">
            <p className="mono">{m.year}</p>
            <h3 className="journey__title">{m.title}</h3>
            <p className="journey__desc">{m.description}</p>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- 10 · 1,750+ INSTALLATIONS -------------------------------------------- */

const MOSAIC = [
  '/media/frames/lekha-cabin.jpg',
  '/media/frames/owaisi-lobby.jpg',
  '/media/frames/chath-facade.jpg',
  '/media/frames/chilkuru-atrium.jpg',
  '/media/interiors/interior-03.jpg',
  '/media/frames/lacheta-lobby.jpg',
]

function Installations() {
  const site = useSite()
  const [ref, progress] = useScrollProgress()
  const [countRef, n] = useCountUp(site.installations ?? 1750, { duration: 2200 })
  const active = Math.min(MOSAIC.length - 1, Math.floor(progress * MOSAIC.length * 1.02))

  return (
    <section ref={ref} className="section section--flush installs">
      <div className="installs__pin">
        <div className="installs__stage">
          {MOSAIC.map((src, i) => (
            <div key={src} className={`installs__plate ${i === active ? 'is-on' : ''}`}>
              <Img src={src} alt="" sizes="100vw" />
            </div>
          ))}
          <div className="installs__veil" aria-hidden="true" />
          <div className="shell installs__content">
            <p className="eyebrow">Installed</p>
            <p className="installs__number" ref={countRef}>
              {new Intl.NumberFormat('en-IN').format(n)}
              <span>+</span>
            </p>
            <p className="installs__label">
              lifts installed across residential, commercial, hospitality, healthcare, institutional
              and industrial buildings since {site.founded_year}.
            </p>
            <Link to="/projects" className="btn btn--accent btn--sm">
              See the work <Arrow size={14} />
            </Link>
          </div>
        </div>
      </div>
      <div className="installs__runway" aria-hidden="true" />
    </section>
  )
}

/* --- page ----------------------------------------------------------------- */

const STAGES = [
  ['01', 'Engineering', 'Understanding the building before anything is drawn — survey, traffic, structure, the constraints nobody wrote down.'],
  ['02', 'Manufacturing', 'Car frames, cabins and structural shafts built in-house at Jeedimetla, then load-tested before dispatch.'],
  ['03', 'Installation', 'Rails aligned, machine set, doors adjusted, car commissioned — sequenced around a building that is often still in use.'],
  ['04', 'Support', 'Maintenance, safety testing and 24/7 breakdown cover, through the twenty-odd years that follow.'],
]

const FIT = [
  ['Residential', 'Villas, homes and apartment buildings.', '/media/frames/lacheta-lobby.jpg'],
  ['Commercial', 'Offices, retail and hospitality.', '/media/frames/chath-facade.jpg'],
  ['Institutional', 'Hospitals, government and education.', '/media/frames/owaisi-lobby.jpg'],
  ['Customised', 'Project-specific engineering where nothing standard fits.', '/media/frames/kashi-structure.jpg'],
]

const FACTORY = [
  ['01', 'Fabrication', 'Raw material into components.', '/media/sourced/factory-machining.jpg'],
  ['02', 'Assembly', 'Components into systems.', '/media/sourced/factory-welding.jpg'],
  ['03', 'Testing', 'Systems into a tested lift.', '/media/sourced/factory-assembly.jpg'],
  ['04', 'Dispatch', 'Factory to site.', '/media/frames/kashi-structure.jpg'],
]

export default function About() {
  const site = useSite()
  const { data: team } = useApi('team/')
  const { data: awards } = useApi('awards/')
  const { data: partners } = useApi('partners/')

  // Static — see src/data. None of it changes between deploys, so it renders
  // with the first paint instead of arriving a round trip later.
  const stats = statsFor('about')

  const [award, setAward] = useState(0)

  useEffect(() => {
    document.title = 'About — Zion Lifts'
  }, [])

  return (
    <>
      {/* --- 01 · HERO --- */}
      <header className="ahero">
        <div className="ahero__bg">
          <Img src="/media/frames/chilkuru-atrium.jpg" alt="" priority sizes="100vw" />
          <div className="ahero__veil" aria-hidden="true" />
        </div>
        <div className="shell ahero__inner">
          <Reveal variant="fade">
            <p className="eyebrow">About Zion</p>
          </Reveal>
          <SplitLines
            as="h1"
            className="display ahero__title"
            lines={['Helping people move', 'the right way.']}
          />
          <Reveal delay={340}>
            <p className="lead ahero__lead">
              Founded in {site.founded_year} with one workshop and a straightforward purpose: to help
              people move better, safer and more comfortably. Today, {site.team_size} people, a
              manufacturing unit of our own, and more than{' '}
              {new Intl.NumberFormat('en-IN').format(site.installations)} installations.
            </p>
          </Reveal>
        </div>
      </header>

      {/* --- 02 · BY THE NUMBERS --- */}
      <section className="section section--tight">
        <div className="shell">
          <StatRow stats={stats} />
        </div>
      </section>

      {/* --- 03 · WHERE IT BEGAN --- */}
      <section className="section on-paper">
        <div className="shell began">
          <Reveal variant="wipe" className="began__media">
            <Img
              src="/media/sourced/factory-floor.jpg"
              alt="Archival photograph of a manufacturing floor"
              ratio="4 / 3"
              sizes="(min-width: 900px) 52vw, 100vw"
            />
          </Reveal>
          <div className="began__copy">
            <Reveal variant="fade">
              <p className="eyebrow">The beginning</p>
            </Reveal>
            <Reveal delay={70}>
              <h2 className="h2">2012, and a workshop in Hyderabad.</h2>
            </Reveal>
            <Reveal delay={130}>
              <p className="body">
                Zion Lifts was founded on a simple observation: most of the lifts going into Indian
                buildings were being sold rather than engineered. The specification came from a
                price list, the survey happened after the order, and the maintenance contract was an
                afterthought.
              </p>
            </Reveal>
            <Reveal delay={190}>
              <p className="body">
                We started the other way round — survey first, specify second, quote third — and
                kept manufacturing close enough to fix what the survey found. Thirteen years later
                that is still the whole method.
              </p>
            </Reveal>
          </div>
        </div>
      </section>

      <Journey milestones={MILESTONES} />

      {/* --- 05 · BUILT TO FIT --- */}
      <section className="section">
        <div className="shell">
          <SectionHead
            index="05"
            eyebrow="Built to fit"
            title="Four kinds of building, one method."
            lead="The engineering underneath does not change. What changes is everything the building asks of it."
          />
          <RevealGroup className="fit" step={80} variant="wipe">
            {FIT.map(([title, line, src]) => (
              <figure className="fit__cell" key={title}>
                <Img
                  src={src}
                  alt={title}
                  ratio="3 / 4"
                  sizes="(min-width: 1000px) 24vw, (min-width: 640px) 46vw, 92vw"
                />
                <figcaption>
                  <h3 className="fit__title">{title}</h3>
                  <p className="fit__line">{line}</p>
                </figcaption>
              </figure>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 06 · IDEA TO INSTALLATION --- */}
      <section className="section on-stone">
        <div className="shell">
          <SectionHead index="06" eyebrow="What we do" title="From idea to installation." />
          <RevealGroup className="stages" step={80}>
            {STAGES.map(([n, title, body]) => (
              <div className="stages__cell" key={n}>
                <span className="index-num">{n}</span>
                <h3 className="stages__title">{title}</h3>
                <p className="stages__body">{body}</p>
              </div>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 07 · INSIDE ZION --- */}
      <section className="section factory" id="factory">
        <div className="shell">
          <SectionHead
            index="07"
            eyebrow="Inside Zion"
            title="Where elevators take shape."
            lead="Fabrication came in-house in 2014, so car frames, cabins and structural shafts are built to our own tolerances rather than bought in."
          />
        </div>
        <div className="factory__scroller">
          <ol className="factory__track">
            {FACTORY.map(([n, title, line, src]) => (
              <li className="factory__cell" key={n}>
                <div className="factory__media">
                  <Img src={src} alt={title} sizes="(min-width: 900px) 34vw, 78vw" parallax={18} />
                </div>
                <div className="factory__cap">
                  <span className="index-num">{n}</span>
                  <h3 className="factory__title">{title}</h3>
                  <p className="factory__line">{line}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* --- 08 · QUALITY & CERTIFICATION --- */}
      <section className="section on-paper">
        <div className="shell">
          <SectionHead
            index="08"
            eyebrow="Quality"
            title="Tested, then recorded."
            lead="Certification only means anything if the tests behind it actually happen. These are the ones that do."
          />
          <RevealGroup className="certs" step={80}>
            {CERTIFICATIONS.map((c) => (
              <div className="certs__cell" key={c.id}>
                <Shield className="certs__icon" />
                <h3 className="certs__name">{c.name}</h3>
                {c.issuer && <p className="certs__issuer mono">{c.issuer}</p>}
                <p className="certs__desc">{c.description}</p>
                {c.reference && <p className="certs__ref">{c.reference}</p>}
              </div>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 09 · RECOGNITION --- */}
      {awards?.length > 0 && (
        <section className="section awards">
          <div className="shell">
            <SectionHead index="09" eyebrow="Recognition" title="Awards and acknowledgements." />
            <div className="awards__body">
              <div className="awards__stage">
                {awards.map((a, i) => (
                  <div key={a.id} className={`awards__plate ${i === award ? 'is-on' : ''}`}>
                    <Img src={a.image_url} alt="" sizes="(min-width: 900px) 50vw, 100vw" />
                  </div>
                ))}
              </div>
              <div className="awards__panel">
                <div className="awards__detail">
                  <p className="mono">
                    {awards[award].year} · {awards[award].organisation}
                  </p>
                  <h3 className="awards__title">{awards[award].name}</h3>
                  <p className="awards__desc">{awards[award].description}</p>
                </div>
                <ol className="awards__years">
                  {awards.map((a, i) => (
                    <li key={a.id}>
                      <button
                        type="button"
                        className={`awards__year ${i === award ? 'is-on' : ''}`}
                        onClick={() => setAward(i)}
                        aria-pressed={i === award}
                      >
                        {a.year}
                      </button>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </section>
      )}

      <Installations />

      {/* --- 11 · THE PEOPLE --- */}
      {team?.length > 0 && (
        <section className="section">
          <div className="shell">
            <SectionHead
              index="11"
              eyebrow="The people behind Zion"
              title="Ninety-five to a hundred of us."
              lead="Engineers, fabricators, installers and a service crew who answer the phone at three in the morning."
            />
            <RevealGroup className="teamgrid" step={80} variant="wipe">
              {team.map((m) => (
                <figure className="teamcard" key={m.id}>
                  <Img
                    src={m.photo}
                    alt={m.name}
                    ratio="4 / 5"
                    sizes="(min-width: 1000px) 24vw, (min-width: 640px) 46vw, 92vw"
                  />
                  <figcaption>
                    <h3 className="teamcard__name">{m.name}</h3>
                    <p className="teamcard__role">{m.role}</p>
                    <p className="teamcard__bio">{m.bio}</p>
                  </figcaption>
                </figure>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {/* --- 12 · TECHNOLOGY PARTNERS --- */}
      {partners?.length > 0 && (
        <section className="section on-stone section--tight">
          <div className="shell">
            <SectionHead
              index="12"
              eyebrow="Our partners"
              title="What goes into a Zion lift."
              split={false}
            />
            <RevealGroup className="partners" step={60}>
              {partners.map((p) => (
                <div className="partners__cell" key={p.id}>
                  <p className="partners__role mono">{p.role_display}</p>
                  <h3 className="partners__name">{p.name}</h3>
                  <p className="partners__component">{p.component}</p>
                </div>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {/* --- 13 · BEYOND INSTALLATION --- */}
      <section className="section beyond">
        <div className="shell">
          <SectionHead
            index="13"
            eyebrow="After handover"
            title="The relationship doesn't end at installation."
            lead="A lift runs for twenty to twenty-five years. Most of that time is our responsibility too."
            action={
              <Link to="/contact#service" className="btn btn--accent btn--sm">
                Need service? <Arrow size={14} />
              </Link>
            }
          />
          <RevealGroup className="pillars" step={70}>
            {SERVICE_PILLARS.map((p) => {
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

      {/* --- 14 · LOOKING AHEAD --- */}
      <section className="section section--flush ahead">
        <div className="ahead__bg">
          <Img src="/media/frames/lekha-aerial.jpg" alt="" sizes="100vw" parallax={40} />
          <div className="ahead__veil" aria-hidden="true" />
        </div>
        <div className="shell ahead__inner">
          <Reveal variant="fade">
            <p className="eyebrow">Looking ahead</p>
          </Reveal>
          <Reveal delay={80}>
            <h2 className="display ahead__title">Helping people move the right way.</h2>
          </Reveal>
          <Reveal delay={160}>
            <p className="lead ahead__lead">
              The way people live and work keeps changing, and so does what a building asks of its
              lifts — quieter, more efficient, more accessible, and expected to be part of the
              architecture rather than hidden behind it. We are still investing in the same three
              things: the survey, the manufacturing, and the people who answer the phone afterwards.
            </p>
          </Reveal>
        </div>
      </section>

      <CtaBand
        eyebrow="15 · See it yourself"
        title="See Zion in motion."
        lead="Come to the factory and watch a car get loaded to 125% of its rating. It tells you more than any brochure."
        primary={{ to: '/contact#visit', label: 'Arrange a visit' }}
        secondary={{ to: '/contact', label: 'Get a quote' }}
      />
    </>
  )
}
