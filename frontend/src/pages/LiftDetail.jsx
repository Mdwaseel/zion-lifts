import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { Accordion, CtaBand, LiftCard, SectionHead, TestimonialRow } from '@/components/sections'
import { Arrow, Check, Shield } from '@/components/icons'
import { useApi } from '@/lib/hooks'

import { Configurator } from './home/Machine'
import './lift-detail.css'

/* --- 04 · VARIANTS -------------------------------------------------------- */

function Variants({ variants, liftSlug }) {
  const [active, setActive] = useState(0)
  if (!variants?.length) return null
  const v = variants[active]

  return (
    <section className="section on-stone" id="variants">
      <div className="shell">
        <SectionHead index="04" eyebrow="Variants" title="Sized to the job." />
        <div className="variants">
          <ol className="variants__rail">
            {variants.map((item, i) => (
              <li key={item.code}>
                <button
                  type="button"
                  className={`variants__tab ${i === active ? 'is-on' : ''}`}
                  onClick={() => setActive(i)}
                  aria-pressed={i === active}
                >
                  <span className="variants__n">{String(i + 1).padStart(2, '0')}</span>
                  <span className="variants__code">{item.code}</span>
                  <span className="variants__name">{item.name}</span>
                </button>
              </li>
            ))}
          </ol>
          <div className="variants__panel">
            <h3 className="variants__title">{v.name}</h3>
            {v.description && <p className="body">{v.description}</p>}
            <dl className="variants__specs">
              {[
                ['Capacity', v.capacity],
                ['Passengers', v.persons],
                ['Speed', v.speed],
                ['Shaft', v.shaft],
              ]
                .filter(([, val]) => val && val !== '—')
                .map(([k, val]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{val}</dd>
                  </div>
                ))}
            </dl>
            <Link
              to={`/contact?lift=${liftSlug}&variant=${encodeURIComponent(v.code)}`}
              className="btn btn--accent btn--sm"
            >
              Enquire with this variant <Arrow size={14} />
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- 05 · DIMENSIONS ------------------------------------------------------ */

function ShaftDiagram() {
  return (
    <svg className="shaftdiagram" viewBox="0 0 320 420" role="img" aria-label="Shaft section showing pit, travel and headroom">
      <defs>
        <pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="7" stroke="currentColor" strokeWidth="1" opacity="0.28" />
        </pattern>
      </defs>
      {/* shaft walls */}
      <rect x="60" y="20" width="200" height="380" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.55" />
      {/* headroom */}
      <rect x="61" y="21" width="198" height="70" fill="url(#hatch)" />
      <line x1="60" y1="91" x2="260" y2="91" stroke="currentColor" strokeWidth="1" strokeDasharray="4 3" opacity="0.5" />
      {/* car */}
      <rect x="88" y="150" width="144" height="150" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
      <line x1="160" y1="150" x2="160" y2="300" stroke="var(--accent)" strokeWidth="1" opacity="0.35" />
      {/* pit */}
      <line x1="60" y1="345" x2="260" y2="345" stroke="currentColor" strokeWidth="1" strokeDasharray="4 3" opacity="0.5" />
      <rect x="61" y="346" width="198" height="53" fill="url(#hatch)" />
      {/* dimension arrows */}
      <g stroke="currentColor" strokeWidth="1" opacity="0.6" fill="none">
        <line x1="34" y1="21" x2="34" y2="90" />
        <line x1="30" y1="21" x2="38" y2="21" />
        <line x1="30" y1="90" x2="38" y2="90" />
        <line x1="34" y1="346" x2="34" y2="399" />
        <line x1="30" y1="346" x2="38" y2="346" />
        <line x1="30" y1="399" x2="38" y2="399" />
        <line x1="286" y1="92" x2="286" y2="344" />
        <line x1="282" y1="92" x2="290" y2="92" />
        <line x1="282" y1="344" x2="290" y2="344" />
      </g>
      <g className="shaftdiagram__label" fill="currentColor">
        <text x="14" y="60" transform="rotate(-90 14 60)" textAnchor="middle">HEADROOM</text>
        <text x="14" y="378" transform="rotate(-90 14 378)" textAnchor="middle">PIT</text>
        <text x="306" y="218" transform="rotate(-90 306 218)" textAnchor="middle">TRAVEL</text>
        <text x="160" y="228" textAnchor="middle" className="shaftdiagram__car">CAR</text>
      </g>
    </svg>
  )
}

function Dimensions({ lift }) {
  const groups = useMemo(() => {
    const out = new Map()
    for (const s of lift.specs ?? []) {
      if (!out.has(s.group)) out.set(s.group, [])
      out.get(s.group).push(s)
    }
    return [...out.entries()]
  }, [lift.specs])

  return (
    <section className="section" id="dimensions">
      <div className="shell">
        <SectionHead
          index="05"
          eyebrow="Dimensions & requirements"
          title="What the building has to give it."
          lead="Indicative figures for the standard configurations. The specification for your project is set by survey."
        />
        <div className="dims">
          <div className="dims__diagram">
            <ShaftDiagram />
            <ul className="dims__key">
              {[
                ['Shaft', lift.shaft_footprint],
                ['Pit depth', lift.pit_depth],
                ['Headroom', lift.headroom],
                ['Machine room', lift.machine_room],
              ]
                .filter(([, v]) => v)
                .map(([k, v]) => (
                  <li key={k}>
                    <span className="mono">{k}</span>
                    <strong>{v}</strong>
                  </li>
                ))}
            </ul>
          </div>
          <div className="dims__tables">
            {groups.map(([group, rows]) => (
              <table className="spectable" key={group}>
                <caption>{group}</caption>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <th scope="row">{r.label}</th>
                      <td>
                        {r.value}
                        {r.note && <small>{r.note}</small>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- page ----------------------------------------------------------------- */

const PROCESS = [
  ['01', 'Survey', 'We measure the shaft, the floor-to-floor heights and the power position. Drawings are rarely what the building actually is.'],
  ['02', 'Manufacture', 'Car frame, cabin and doors built and finished, then load-tested to 125% before dispatch.'],
  ['03', 'Install', 'Rails aligned, machine set, doors fitted and adjusted, car commissioned on site.'],
  ['04', 'Hand over', 'Safety testing repeated on site, statutory inspection prepared, walkthrough with whoever runs the building.'],
]

const AFTERCARE = [
  ['AMC', 'Scheduled preventive visits, safety testing recorded, comprehensive or non-comprehensive.'],
  ['Breakdown support', 'A staffed desk 24/7, with entrapments prioritised above every other call.'],
  ['Spare parts', 'Held and supported through the service life of the system.'],
]

export default function LiftDetail() {
  const { slug } = useParams()
  const { data: lift, loading, error } = useApi(slug ? `lifts/${slug}/` : null)
  const { data: finishes } = useApi('finishes/')
  const { data: projects } = useApi('projects/', { lift_type__slug: slug })
  const { data: testimonials } = useApi('testimonials/')
  const { data: faqCats } = useApi('faq-categories/')
  const { data: partners } = useApi('partners/')

  useEffect(() => {
    if (lift) document.title = `${lift.name} — Zion Lifts`
  }, [lift])

  if (loading) {
    return (
      <div className="section">
        <div className="shell">
          <div className="skeleton" style={{ height: '60vh' }} />
        </div>
      </div>
    )
  }

  if (error || !lift) {
    return (
      <section className="section">
        <div className="shell state">
          <p className="state__title">We could not find that lift.</p>
          <Link to="/lifts" className="btn btn--accent btn--sm">
            All lift systems <Arrow size={14} />
          </Link>
        </div>
      </section>
    )
  }

  const gallery = (lift.images ?? []).filter((i) => i.kind === 'gallery')
  const details = (lift.images ?? []).filter((i) => i.kind === 'detail' || i.kind === 'cabin')
  const productFaq =
    (faqCats ?? []).find((c) => c.slug === 'products-technology')?.questions?.slice(0, 5) ?? []

  return (
    <>
      {/* --- 01 · HERO --- */}
      <header className="pdhero">
        <div className="pdhero__media">
          <Img src={lift.hero_image_url} alt={lift.name} priority sizes="(min-width: 900px) 58vw, 100vw" />
        </div>
        <div className="pdhero__panel">
          <nav className="pagehero__crumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span aria-hidden="true">/</span>
            <Link to="/lifts">Lifts</Link>
            <span aria-hidden="true">/</span>
            <span>{lift.name}</span>
          </nav>
          <p className="eyebrow">{lift.eyebrow}</p>
          <h1 className="display pdhero__title">{lift.name}</h1>
          <p className="lead">{lift.tagline}</p>
          <dl className="pdhero__specs">
            {[
              ['Capacity', lift.capacity],
              ['Speed', lift.speed],
              ['Stops', lift.stops],
              ['Drive', lift.drive],
            ]
              .filter(([, v]) => v)
              .map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
          </dl>
          <div className="pdhero__actions">
            <a href="#configure" className="btn btn--accent btn--sm">
              Configure <Arrow size={14} />
            </a>
            <a href="#dimensions" className="btn btn--ghost btn--sm">
              Dimensions <Arrow size={14} />
            </a>
          </div>
        </div>
      </header>

      {/* --- 02 · OVERVIEW --- */}
      <section className="section on-paper">
        <div className="shell overview">
          <Reveal variant="fade">
            <p className="eyebrow">
              <span className="index-num">02</span> Overview
            </p>
          </Reveal>
          <div className="overview__body">
            {(lift.overview || lift.summary).split('\n\n').map((p, i) => (
              <Reveal key={i} delay={i * 80}>
                <p className={i === 0 ? 'overview__lead' : 'body'}>{p}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* --- 03 · APPLICATIONS --- */}
      {lift.applications?.length > 0 && (
        <section className="section section--tight">
          <div className="shell">
            <SectionHead index="03" eyebrow="Best for" title="Where it belongs." split={false} />
            <RevealGroup className="bestfor" step={60}>
              {lift.applications.map((a) => (
                <div className="bestfor__chip" key={a.slug}>
                  <Check size={14} />
                  <span>
                    <strong>{a.name}</strong>
                    {a.description && <em>{a.description}</em>}
                  </span>
                </div>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      <Variants variants={lift.variants} liftSlug={lift.slug} />
      <Dimensions lift={lift} />

      {/* --- 06 · CABIN CONFIGURATOR --- */}
      <Configurator finishes={finishes ?? []} compact liftSlug={lift.slug} />

      {/* --- 07/08 · GALLERY + DETAILS --- */}
      {gallery.length > 0 && (
        <section className="section">
          <div className="shell">
            <SectionHead
              index="07"
              eyebrow="In place"
              title={`${lift.short_name} installations.`}
            />
            <RevealGroup className="pdgallery" step={70} variant="wipe">
              {gallery.map((g) => (
                <figure className="pdgallery__cell" key={g.id}>
                  <Img
                    src={g.src}
                    alt={g.alt}
                    ratio="4 / 3"
                    sizes="(min-width: 1000px) 32vw, (min-width: 640px) 48vw, 92vw"
                  />
                  {g.caption && <figcaption>{g.caption}</figcaption>}
                </figure>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {details.length > 0 && (
        <section className="section on-stone section--tight">
          <div className="shell">
            <SectionHead index="08" eyebrow="Details" title="Up close." split={false} />
            <RevealGroup className="pddetails" step={60} variant="wipe">
              {details.map((d) => (
                <figure className="pddetails__cell" key={d.id}>
                  <Img src={d.src} alt={d.alt} ratio="1 / 1" sizes="(min-width: 900px) 24vw, 46vw" />
                  <figcaption className="mono">{d.caption}</figcaption>
                </figure>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {/* --- 09 · DRIVE SYSTEM --- */}
      <section className="section drive">
        <div className="shell drive__inner">
          <Reveal variant="wipe" className="drive__media">
            <Img
              src="/media/frames/kashi-machine.jpg"
              alt="Drive and sheave assembly"
              ratio="4 / 3"
              sizes="(min-width: 900px) 46vw, 100vw"
              parallax={22}
            />
          </Reveal>
          <div className="drive__copy">
            <Reveal variant="fade">
              <p className="eyebrow">
                <span className="index-num">09</span> Drive system
              </p>
            </Reveal>
            <Reveal delay={70}>
              <h2 className="h2">{lift.drive}</h2>
            </Reveal>
            <Reveal delay={130}>
              <p className="body">
                {lift.machine_room === 'Not required'
                  ? 'The machine mounts on the guide rails at the head of the shaft, so the building gives up no room above it. A closed-loop VVVF drive shapes acceleration into a curve and holds levelling within a few millimetres, loaded or empty.'
                  : 'A power unit sized to the duty, sited where the building has space for it, driving the car through a controlled ramp rather than a step. Levelling is held tight and re-levelled on load change.'}
              </p>
            </Reveal>
            {partners?.length > 0 && (
              <Reveal delay={190}>
                <ul className="drive__partners">
                  {partners.slice(0, 4).map((p) => (
                    <li key={p.id}>
                      <strong>{p.name}</strong>
                      <span>{p.component}</span>
                    </li>
                  ))}
                </ul>
              </Reveal>
            )}
          </div>
        </div>
      </section>

      {/* --- 10 · SAFETY SYSTEMS --- */}
      {lift.safety_features?.length > 0 && (
        <section className="section on-stone">
          <div className="shell">
            <SectionHead
              index="10"
              eyebrow="Safety systems"
              title="Fitted as standard."
              lead="Each of these is tested before dispatch and again after installation. The result is recorded."
            />
            <RevealGroup className="safetylist" step={60}>
              {lift.safety_features.map((s) => (
                <div className="safetylist__item" key={s.slug}>
                  <Shield className="safetylist__icon" />
                  <h3 className="safetylist__name">{s.name}</h3>
                  <p className="safetylist__line">{s.headline}</p>
                  {s.standard && <p className="safetylist__std mono">{s.standard}</p>}
                </div>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      {/* --- 12 · INSTALLATION PROCESS --- */}
      <section className="section">
        <div className="shell">
          <SectionHead index="12" eyebrow="Process" title="From survey to handover." />
          <RevealGroup className="process" step={80}>
            {PROCESS.map(([n, title, body]) => (
              <div className="process__step" key={n}>
                <span className="index-num">{n}</span>
                <h3 className="process__title">{title}</h3>
                <p className="process__body">{body}</p>
              </div>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 13 · AFTER-SALES --- */}
      <section className="section section--tight on-paper">
        <div className="shell">
          <SectionHead index="13" eyebrow="Aftercare" title="What happens next." split={false} />
          <RevealGroup className="aftercare" step={70}>
            {AFTERCARE.map(([title, body]) => (
              <div className="aftercare__item" key={title}>
                <h3 className="aftercare__title">{title}</h3>
                <p className="aftercare__body">{body}</p>
              </div>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 14 · FAQ --- */}
      {productFaq.length > 0 && (
        <section className="section">
          <div className="shell shell--text">
            <SectionHead
              index="14"
              eyebrow="Questions"
              title={`${lift.short_name}, in questions.`}
              action={
                <Link to="/faq" className="link">
                  Every question <Arrow size={14} />
                </Link>
              }
            />
            <Accordion items={productFaq} defaultOpen={0} />
          </div>
        </section>
      )}

      {/* --- 15 · PROJECTS WITH THIS SYSTEM --- */}
      {projects?.length > 0 && (
        <section className="section on-stone">
          <div className="shell">
            <SectionHead index="15" eyebrow="Installed" title={`${lift.short_name} in the field.`} />
            <RevealGroup className="liftgrid" step={80}>
              {projects.slice(0, 3).map((p) => (
                <article className="card" key={p.slug}>
                  <div className="card__media">
                    <Img src={p.hero_image_url} alt={p.name} sizes="(min-width: 1000px) 32vw, 92vw" />
                  </div>
                  <div className="card__body">
                    <p className="card__eyebrow">{p.category?.name}</p>
                    <h3 className="card__title">
                      <Link to={`/projects/${p.slug}`} className="card__link">
                        {p.name}
                      </Link>
                    </h3>
                    <p className="card__text">{p.statement}</p>
                    <div className="card__foot">
                      <span className="card__spec">{p.location}</span>
                    </div>
                  </div>
                </article>
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      <TestimonialRow
        testimonials={(testimonials ?? []).slice(0, 3)}
        title="What clients say"
      />

      {/* --- 17 · RELATED --- */}
      {lift.related?.length > 0 && (
        <section className="section">
          <div className="shell">
            <SectionHead
              index="17"
              eyebrow="The rest of the range"
              title="Other ways to move."
              action={
                <Link to="/lifts" className="link">
                  All systems <Arrow size={14} />
                </Link>
              }
            />
            <RevealGroup className="liftgrid" step={60}>
              {lift.related.slice(0, 3).map((r) => (
                <LiftCard key={r.slug} lift={r} />
              ))}
            </RevealGroup>
          </div>
        </section>
      )}

      <CtaBand
        eyebrow="18 · Next step"
        title={`Enquire about the ${lift.short_name}.`}
        lead="Send the number of levels, the building type and a plan if you have one. We will come back with a specification and a figure."
        primary={{ to: `/contact?lift=${lift.slug}`, label: 'Get a quote' }}
        secondary={{ to: '/contact#visit', label: 'Talk to an engineer' }}
      />
    </>
  )
}
