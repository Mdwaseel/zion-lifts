import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoLoop } from '@/components/Media'
import Reveal, { RevealGroup, SplitLines } from '@/components/Reveal'
import { Arrow, Check } from '@/components/icons'
import { useScrollProgress } from '@/lib/hooks'

/* ==========================================================================
   08 · BLUEPRINT → REALITY
   Four stages of the same lift: drawing, structure, installed car, in use.
   ========================================================================== */

const STAGES = [
  {
    n: '01',
    label: 'Blueprint',
    line: 'A general arrangement drawing, dimensioned to a surveyed shaft.',
    src: '/media/sourced/blueprint-technical.jpg',
    treat: 'blueprint',
  },
  {
    n: '02',
    label: 'Structure',
    line: 'Rails, frame and machine set in place, plumb over the whole travel.',
    src: '/media/frames/kashi-structure.jpg',
  },
  {
    n: '03',
    label: 'The finished car',
    line: 'Finishes fitted, doors adjusted, levelling set, load tested.',
    src: '/media/frames/lekha-cabin.jpg',
  },
  {
    n: '04',
    label: 'In the building',
    line: 'The same lift, in daily use, at Lekha Nilayam.',
    src: '/media/frames/lekha-inuse.jpg',
  },
]

export function Blueprint() {
  return (
    <section className="section blueprint" aria-labelledby="blueprint-title">
      <div className="shell">
        <div className="section-head section-head--split">
          <div>
            <Reveal variant="fade">
              <p className="eyebrow">
                Blueprint to reality
              </p>
            </Reveal>
            <Reveal delay={60}>
              <h2 className="h2" id="blueprint-title" style={{ marginTop: '1.1rem' }}>
                We build what
                <br />
                we draw.
              </h2>
            </Reveal>
          </div>
          <Reveal delay={130}>
            <p className="body">
              Four stages of one installation. Nothing here is a render standing in for a
              photograph — the last frame is the lift the first frame described.
            </p>
          </Reveal>
        </div>

        <RevealGroup className="blueprint__row" step={110} variant="wipe">
          {STAGES.map((s) => (
            <figure className="blueprint__cell" key={s.n}>
              <div className={`blueprint__media ${s.treat === 'blueprint' ? 'is-blueprint' : ''}`}>
                <Img
                  src={s.src}
                  alt={s.label}
                  sizes="(min-width: 1000px) 24vw, (min-width: 640px) 46vw, 92vw"
                />
              </div>
              <figcaption className="blueprint__cap">
                <span className="index-num">{s.n}</span>
                <span className="blueprint__label">{s.label}</span>
                <span className="blueprint__line">{s.line}</span>
              </figcaption>
            </figure>
          ))}
        </RevealGroup>
      </div>
    </section>
  )
}

/* ==========================================================================
   09 · THE SAFETY LAB
   Five tests, each with what it proves and how it is proven.
   ========================================================================== */

export function SafetyLab({ features = [] }) {
  const [active, setActive] = useState(0)
  const tests = features.slice(0, 5)
  if (!tests.length) return null
  const current = tests[active]

  return (
    <section className="section safety" aria-labelledby="safety-title">
      <div className="shell">
        <Reveal variant="fade">
          <p className="eyebrow">
            The safety lab
          </p>
        </Reveal>
        <SplitLines
          as="h2"
          className="h2 safety__title"
          lines={["Safety isn't", 'an option.']}
        />
        <Reveal delay={200}>
          <p className="lead safety__lead">
            Every car is load-tested to 125% of its rated capacity and has its governor and safety
            gear physically tripped before it leaves the works — then again after installation. The
            test is the point.
          </p>
        </Reveal>

        <div className="safety__body">
          <ol className="safety__tabs" role="tablist" aria-label="Safety tests">
            {tests.map((t, i) => (
              <li key={t.slug}>
                <button
                  type="button"
                  role="tab"
                  aria-selected={i === active}
                  className={`safety__tab ${i === active ? 'is-on' : ''}`}
                  onClick={() => setActive(i)}
                  onMouseEnter={() => setActive(i)}
                >
                  <span className="safety__tab-n">{String(i + 1).padStart(2, '0')}</span>
                  <span className="safety__tab-name">{t.name}</span>
                  <span className="safety__pass">
                    <Check size={12} /> Passed
                  </span>
                </button>
              </li>
            ))}
          </ol>

          <div className="safety__panel" role="tabpanel">
            <p className="safety__headline">{current.headline}</p>
            <p className="safety__desc">{current.description}</p>
            {current.test_procedure && (
              <div className="safety__test">
                <p className="mono">The test</p>
                <p>{current.test_procedure}</p>
              </div>
            )}
            {current.standard && (
              <p className="safety__standard">
                <span className="mono">Standard</span> {current.standard}
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   10 · THE MAKING OF ZION
   ========================================================================== */

const MAKING = [
  { label: 'Fabrication', line: 'Raw steel becomes car frames, shafts and cabin shells.', src: '/media/sourced/factory-machining.jpg' },
  { label: 'Welding', line: 'Frames assembled and squared before anything is finished.', src: '/media/sourced/factory-welding.jpg' },
  { label: 'Assembly', line: 'Machine, controller, doors and car brought together.', src: '/media/frames/kashi-machine.jpg' },
  { label: 'Testing', line: 'Loaded to 125%, governor tripped, levelling verified.', src: '/media/sourced/factory-assembly.jpg' },
  { label: 'Installation', line: 'Rails aligned on site, doors adjusted, car commissioned.', src: '/media/frames/kashi-structure.jpg' },
]

export function MakingOf() {
  return (
    <section className="section making" aria-labelledby="making-title">
      <div className="shell">
        <div className="section-head section-head--split">
          <div>
            <Reveal variant="fade">
              <p className="eyebrow">
                The making of Zion
              </p>
            </Reveal>
            <Reveal delay={60}>
              <h2 className="h2" id="making-title" style={{ marginTop: '1.1rem' }}>
                From raw material
                <br />
                to vertical movement.
              </h2>
            </Reveal>
          </div>
          <Reveal delay={130}>
            <div className="stack" style={{ '--flow': '1.5rem' }}>
              <p className="body">
                Fabrication was brought in-house in 2014 so car frames, cabins and structural shafts
                are built to Zion&rsquo;s own tolerances rather than bought in.
              </p>
              <Link to="/about#factory" className="link">
                Inside the factory <Arrow size={14} />
              </Link>
            </div>
          </Reveal>
        </div>
      </div>

      <div className="making__scroller">
        <ol className="making__track">
          {MAKING.map((m, i) => (
            <li className="making__cell" key={m.label}>
              <div className="making__media">
                <Img src={m.src} alt={m.label} sizes="(min-width: 900px) 34vw, 78vw" parallax={18} />
              </div>
              <div className="making__cap">
                <span className="index-num">{String(i + 1).padStart(2, '0')}</span>
                <h3 className="making__label">{m.label}</h3>
                <p className="making__line">{m.line}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

/* ==========================================================================
   11 · THE PROJECTS
   One project fills the frame at a time, driven by scroll.
   ========================================================================== */

export function ProjectsReel({ projects = [] }) {
  const [ref, progress] = useScrollProgress()
  const items = projects.filter((p) => p.is_featured).slice(0, 5)
  const list = items.length ? items : projects.slice(0, 5)
  const active = Math.min(list.length - 1, Math.floor(progress * list.length * 1.02))

  if (!list.length) return null
  const current = list[active]

  return (
    <section ref={ref} className="section section--flush reel" aria-labelledby="reel-title">
      <div className="reel__pin">
        <div className="reel__stage">
          {list.map((p, i) => (
            <div key={p.slug} className={`reel__layer ${i === active ? 'is-on' : ''}`}>
              {p.loop_video_url ? (
                <VideoLoop src={p.loop_video_url} poster={p.poster_url || p.hero_image_url} />
              ) : (
                <Img src={p.hero_image_url || p.poster_url} alt="" sizes="100vw" />
              )}
            </div>
          ))}
          <div className="reel__veil" aria-hidden="true" />

          <div className="shell reel__content">
            <div className="reel__head">
              <p className="eyebrow">
                The projects
              </p>
              <h2 className="h2 reel__title" id="reel-title">
                Real buildings.
                <br />
                Real installations.
              </h2>
            </div>

            <div className="reel__now" key={current.slug}>
              <p className="mono">
                {current.category?.name}
                {current.year ? ` · ${current.year}` : ''}
              </p>
              <h3 className="reel__name">{current.name}</h3>
              <p className="reel__statement">{current.statement}</p>
              <dl className="reel__meta">
                {[
                  ['Location', current.location],
                  ['System', current.system],
                  ['Capacity', current.capacity],
                  ['Stops', current.stops],
                ]
                  .filter(([, v]) => v)
                  .map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
              </dl>
              <Link to={`/projects/${current.slug}`} className="btn btn--accent btn--sm">
                View case study <Arrow size={14} />
              </Link>
            </div>

            <ol className="reel__rail">
              {list.map((p, i) => (
                <li key={p.slug} className={i === active ? 'is-on' : ''}>
                  <span className="reel__rail-bar" />
                  <span className="reel__rail-label">{p.name}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
      <div className="reel__runway" aria-hidden="true" />
    </section>
  )
}

/* ==========================================================================
   12 · THE DETAILS
   Eight macro plates. The photography carries it; almost no motion.
   ========================================================================== */

const DETAILS = [
  { label: 'The door', src: '/media/frames/lekha-hall.jpg' },
  { label: 'The button', src: '/media/frames/lacheta-indicator.jpg' },
  { label: 'Brass', src: '/media/frames/lacheta-lobby.jpg' },
  { label: 'Glass', src: '/media/frames/kashi-shaft.jpg' },
  { label: 'Light', src: '/media/frames/lekha-ceiling.jpg' },
  { label: 'The floor', src: '/media/frames/kashi-floor.jpg' },
  { label: 'The handrail', src: '/media/frames/chath-cabin.jpg' },
  { label: 'The ceiling', src: '/media/frames/lacheta-ceiling.jpg' },
]

export function Details() {
  return (
    <section className="section on-paper details" aria-labelledby="details-title">
      <div className="shell">
        <div className="section-head section-head--split">
          <div>
            <Reveal variant="fade">
              <p className="eyebrow">
                The details
              </p>
            </Reveal>
            <Reveal delay={60}>
              <h2 className="h2" id="details-title" style={{ marginTop: '1.1rem' }}>
                Details make
                <br />
                the difference.
              </h2>
            </Reveal>
          </div>
          <Reveal delay={130}>
            <p className="body">
              The parts of a lift people actually touch: the button, the handrail, the sill you step
              over without looking. Everything else is engineering nobody should have to notice.
            </p>
          </Reveal>
        </div>

        <RevealGroup className="details__grid" step={70} variant="wipe">
          {DETAILS.map((d) => (
            <figure className="details__cell" key={d.label}>
              <Img
                src={d.src}
                alt={d.label}
                ratio="1 / 1"
                sizes="(min-width: 1000px) 23vw, (min-width: 620px) 46vw, 92vw"
              />
              <figcaption className="details__cap">{d.label}</figcaption>
            </figure>
          ))}
        </RevealGroup>
      </div>
    </section>
  )
}
