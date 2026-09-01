import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img } from '@/components/Media'
import Reveal, { RevealGroup } from '@/components/Reveal'
import { Accordion, CtaBand, LiftCard, PageHero, SectionHead } from '@/components/sections'
import { Arrow, Shield } from '@/components/icons'
import { faqCategory } from '@/data/faqs'
import { useApi } from '@/lib/hooks'

import { Configurator } from './home/Machine'
import './lifts.css'

/* --- 02 · LIFT FINDER ----------------------------------------------------- */

const PROPERTY = [
  { key: 'any', label: 'Any building' },
  { key: 'residential', label: 'Home or villa' },
  { key: 'commercial', label: 'Office, hotel or retail' },
  { key: 'institutional', label: 'Hospital or institution' },
  { key: 'industrial', label: 'Factory or parking' },
]

const FLOORS = [
  { key: 'any', label: 'Any' },
  { key: '2', label: '2–3', value: 3 },
  { key: '4', label: '4–6', value: 6 },
  { key: '7', label: '7–12', value: 12 },
  { key: '13', label: '13+', value: 18 },
]

const LOAD = [
  { key: 'any', label: 'Any' },
  { key: 'small', label: 'Up to 6 people', max: 6 },
  { key: 'mid', label: '8–15 people', max: 15 },
  { key: 'large', label: '15+ or goods', max: 99 },
]

function Finder({ lifts, filter, setFilter }) {
  const groups = [
    { id: 'property', label: 'Property type', options: PROPERTY },
    { id: 'floors', label: 'Number of floors', options: FLOORS },
    { id: 'load', label: 'Passengers or load', options: LOAD },
  ]

  return (
    <section className="section section--tight on-stone finder" id="finder">
      <div className="shell">
        <SectionHead
          index="02"
          eyebrow="Lift finder"
          title="Narrow it down."
          lead="Three questions. The grid below responds as you answer them — or ignore it and read all nine."
        />
        <div className="finder__grid">
          {groups.map((g) => (
            <fieldset className="finder__group" key={g.id}>
              <legend className="field__label">{g.label}</legend>
              <div className="chips">
                {g.options.map((o) => (
                  <button
                    key={o.key}
                    type="button"
                    className={`chip ${filter[g.id] === o.key ? 'is-on' : ''}`}
                    onClick={() => setFilter((f) => ({ ...f, [g.id]: o.key }))}
                    aria-pressed={filter[g.id] === o.key}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </fieldset>
          ))}
        </div>
        <p className="finder__result">
          <strong>{lifts.length}</strong> of 9 systems match
          {Object.values(filter).some((v) => v !== 'any') && (
            <button
              type="button"
              className="link finder__reset"
              onClick={() => setFilter({ property: 'any', floors: 'any', load: 'any' })}
            >
              Reset
            </button>
          )}
        </p>
      </div>
    </section>
  )
}

/* --- 04 · COMPARE --------------------------------------------------------- */

function Compare({ lifts }) {
  const rows = [
    ['Drive', (l) => l.drive],
    ['Speed', (l) => l.speed],
    ['Capacity', (l) => l.capacity],
    ['Stops', (l) => l.stops],
    ['Machine room', (l) => l.machine_room],
  ]
  return (
    <section className="section compare" id="compare">
      <div className="shell">
        <SectionHead
          index="04"
          eyebrow="Compare"
          title="Side by side."
          lead="The five figures that usually decide it. Everything else is detail we can work through together."
        />
        <div className="tablescroll">
          <table className="comparetable">
            <caption className="sr-only">Comparison of Zion lift systems</caption>
            <thead>
              <tr>
                <th scope="col">System</th>
                {rows.map(([label]) => (
                  <th scope="col" key={label}>
                    {label}
                  </th>
                ))}
                <th scope="col" className="sr-only">
                  Link
                </th>
              </tr>
            </thead>
            <tbody>
              {lifts.map((l) => (
                <tr key={l.slug}>
                  <th scope="row">
                    <Link to={`/lifts/${l.slug}`}>{l.name}</Link>
                  </th>
                  {rows.map(([label, fn]) => (
                    <td key={label}>{fn(l) || '—'}</td>
                  ))}
                  <td className="comparetable__go">
                    <Link to={`/lifts/${l.slug}`} aria-label={`View ${l.name}`}>
                      <Arrow size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

/* --- page ----------------------------------------------------------------- */

export default function Lifts() {
  const { data: lifts } = useApi('lifts/')
  const { data: applications } = useApi('applications/')
  const { data: safety } = useApi('safety-features/')
  const { data: projects } = useApi('projects/')
  const { data: finishes } = useApi('finishes/')

  const [filter, setFilter] = useState({ property: 'any', floors: 'any', load: 'any' })

  useEffect(() => {
    document.title = 'Lift systems — Zion Lifts'
  }, [])

  const all = lifts ?? []

  const filtered = useMemo(() => {
    return all.filter((l) => {
      if (filter.property !== 'any') {
        const groups = new Set((l.applications ?? []).map((a) => a.group))
        if (!groups.has(filter.property)) return false
      }
      if (filter.floors !== 'any') {
        const want = FLOORS.find((f) => f.key === filter.floors)?.value ?? 0
        if (l.max_floors < want && l.min_floors > want) return false
        if (l.max_floors < Number(filter.floors)) return false
      }
      if (filter.load !== 'any') {
        const max = LOAD.find((o) => o.key === filter.load)?.max ?? 99
        if (filter.load === 'small' && l.min_persons > 6) return false
        if (filter.load === 'mid' && (l.max_persons < 8 || l.min_persons > 15)) return false
        if (filter.load === 'large' && l.max_persons < 15 && l.max_persons > 0) return false
        void max
      }
      return true
    })
  }, [all, filter])

  const chooseFaq = faqCategory('choosing-a-lift')

  return (
    <>
      <PageHero
        eyebrow="The range"
        title="Nine ways to move vertically."
        lead="One engineering approach underneath — a gearless machine, rail-guided car and a controller that shapes every start and stop. Nine shells around it, for nine kinds of building."
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Lifts' },
        ]}
        image="/media/interiors/interior-05.jpg"
        meta={
          <>
            <span className="mono">01 · Index</span>
            <a className="link" href="#finder">
              Find the right one <Arrow size={14} />
            </a>
            <a className="link" href="#compare">
              Compare all nine <Arrow size={14} />
            </a>
          </>
        }
      />

      <Finder lifts={filtered} filter={filter} setFilter={setFilter} />

      {/* --- 03 · THE GRID --- */}
      <section className="section" id="range">
        <div className="shell">
          <SectionHead index="03" eyebrow="The systems" title="Every lift Zion builds." />
          {filtered.length ? (
            <RevealGroup className="liftgrid" step={70}>
              {filtered.map((l, i) => (
                <LiftCard key={l.slug} lift={l} index={i + 1} />
              ))}
            </RevealGroup>
          ) : (
            <div className="state">
              <p className="state__title">Nothing matches all three answers.</p>
              <p className="body">
                That usually means the requirement is a custom one, which is worth a conversation
                rather than a filter.
              </p>
              <Link to="/contact" className="btn btn--accent btn--sm">
                Tell us what you need <Arrow size={14} />
              </Link>
            </div>
          )}
        </div>
      </section>

      <Compare lifts={all} />

      {/* --- 05 · APPLICATIONS --- */}
      <section className="section on-paper">
        <div className="shell">
          <SectionHead
            index="05"
            eyebrow="Applications"
            title="Where these lifts go."
            lead="The building decides most of the specification before anyone opens a catalogue."
          />
          <RevealGroup className="applist" step={60}>
            {(applications ?? []).map((a) => (
              <div className="applist__item" key={a.slug}>
                <h3 className="applist__name">{a.name}</h3>
                <p className="applist__desc">{a.description}</p>
                <p className="applist__group mono">{a.group}</p>
              </div>
            ))}
          </RevealGroup>
        </div>
      </section>

      {/* --- 06 · ENGINEERING AT A GLANCE --- */}
      <section className="section glance">
        <div className="shell glance__inner">
          <Reveal variant="wipe" className="glance__media">
            <Img
              src="/media/frames/kashi-drive.jpg"
              alt="Gearless traction machine at the head of a shaft"
              ratio="4 / 3"
              sizes="(min-width: 900px) 48vw, 100vw"
              parallax={24}
            />
          </Reveal>
          <div className="glance__copy">
            <Reveal variant="fade">
              <p className="eyebrow">
                <span className="index-num">06</span> Engineering at a glance
              </p>
            </Reveal>
            <Reveal delay={70}>
              <h2 className="h2">The same machine under all of them.</h2>
            </Reveal>
            <Reveal delay={130}>
              <p className="body">
                A permanent-magnet gearless motor at the head of the shaft. Machined steel rails
                holding the car on one vertical plane. A closed-loop drive shaping every start and
                stop into a curve. Progressive safety gear that works without electricity.
              </p>
            </Reveal>
            <Reveal delay={190}>
              <Link to="/#machine" className="link">
                See the whole machine <Arrow size={14} />
              </Link>
            </Reveal>
          </div>
        </div>
      </section>

      {/* --- 07 · CUSTOMISATION --- */}
      <Configurator finishes={finishes ?? []} compact />

      {/* --- 08 · SAFETY --- */}
      <section className="section on-stone">
        <div className="shell">
          <SectionHead
            index="08"
            eyebrow="Safety"
            title="Fitted to every lift, without exception."
            lead="Not a premium tier. These are on the standard specification of every system on this page."
          />
          <RevealGroup className="safetylist" step={60}>
            {(safety ?? []).map((s) => (
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

      {/* --- 09 · PROJECTS --- */}
      <section className="section">
        <div className="shell">
          <SectionHead
            index="09"
            eyebrow="Installed"
            title="These systems, in buildings."
            action={
              <Link to="/projects" className="link">
                All projects <Arrow size={14} />
              </Link>
            }
          />
          <RevealGroup className="liftgrid" step={80}>
            {(projects ?? []).slice(0, 3).map((p) => (
              <article className="card" key={p.slug}>
                <div className="card__media">
                  <Img
                    src={p.hero_image_url || p.poster_url}
                    alt={p.name}
                    sizes="(min-width: 1000px) 32vw, 92vw"
                  />
                </div>
                <div className="card__body">
                  <p className="card__eyebrow">{p.lift_type_name || p.category?.name}</p>
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

      {/* --- 10 · CHOOSING FAQ --- */}
      {chooseFaq && (
        <section className="section on-paper">
          <div className="shell shell--text">
            <SectionHead
              index="10"
              eyebrow="Choosing"
              title="The questions people actually ask."
              action={
                <Link to="/faq" className="link">
                  Every question <Arrow size={14} />
                </Link>
              }
            />
            <Accordion items={chooseFaq.questions} defaultOpen={0} />
          </div>
        </section>
      )}

      <CtaBand
        eyebrow="11 · Next step"
        title="Tell us what you're building."
        lead="Send a floor plan and the number of levels and we will come back with a system, a specification and a real figure."
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{ to: '/projects', label: 'See the work' }}
      />
    </>
  )
}
