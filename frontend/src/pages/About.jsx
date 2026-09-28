import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Img, VideoLoop } from '@/components/Media'
import { AWARDS } from '@/data/awards'
import { ESTABLISHED, KNOWN_FOR, MODERNISATION, OFFICES, REVIEWS, SECTORS, VALUES, WHO_WE_ARE } from '@/data/about'
import Reveal from '@/components/Reveal'
import { ClientLogos } from '@/components/sections'
import { Arrow, ArrowDown } from '@/components/icons'
import { gsap } from '@/lib/gsap'
import { useReducedMotion } from '@/lib/hooks'
import { telHref } from '@/lib/media'

import { Rise, RiseIn, Scrub, clamp01, useLightHero, useScrollVar, whenIntroDone } from './lift/shared'
import './about.css'

/* ==========================================================================
   /about — who we are
   The company's own account (zionlifts.com/about), told in the site's frame
   language and the home page's colour: dark only where a film or a
   photograph fills the frame, ivory and paper everywhere else. The opening is
   a film rendered in /motion — the lift made, built in, ridden and handed
   over, with a drawn car riding the shaft beside it. Then who we are, the
   buildings the lifts go into, modernisation as a before-and-after drawing,
   the values as a stack of cards, the eight promises as a wall of photographs
   and drawings, the clients in their own words, and the way to reach us.
   ========================================================================== */

/* --- the opening: the work itself, in three moving columns ---------------- */

/* Zion's own installations and two of the lifts' films, stacked into three
   columns that drift past each other — one shows a finished lift, the next the
   workshop that made it. Each column is set twice so its loop has no seam. */
const WALL = [
  [
    { src: '/media/frames/lekha-hall.jpg' },
    { src: '/media/frames/chilkuru-capsule.jpg' },
    { src: '/media/frames/chath-inuse.jpg' },
    { src: '/media/frames/kashi-cabin.jpg' },
  ],
  [
    { film: '/media/lifts/home-elevator.mp4', src: '/media/lifts/home-elevator.jpg' },
    { src: '/media/frames/workshop-sparks.jpg' },
    { src: '/media/frames/lacheta-lobby.jpg' },
    { src: '/media/frames/owaisi-lobby.jpg' },
  ],
  [
    { src: '/media/frames/kashi-exterior.jpg' },
    { src: '/media/frames/lacheta-glass.jpg' },
    { film: '/media/lifts/capsule-elevator.mp4', src: '/media/lifts/capsule-elevator.jpg' },
    { src: '/media/frames/chath-facade.jpg' },
  ],
]

function Opening() {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(false)

  useEffect(() => whenIntroDone(() => setShown(true)), [])

  useLightHero()

  // scrolling away hurries the columns along, each at its own rate
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
    <header ref={ref} className={`ab-hero ${shown ? 'is-in' : ''} ${reduced ? 'is-still' : ''}`}>
      <div className="ab-hero__copy">
        <h1 className="ab-hero__title">
          <Rise text="Every kind of lift, made here." accent={false} />
        </h1>
        <p className="ab-hero__lead">
          Zion Lifts® designs, manufactures, supplies, erects and installs all types of lifts. An ISO certified
          company, in Hyderabad since {ESTABLISHED}, trusted by more than 1,000 clients.
        </p>
        <div className="ab-hero__actions">
          <Link to="/contact" className="ab-go">
            <span>Talk to us</span>
            <span className="ab-go__ring">
              <Arrow size={16} />
            </span>
          </Link>
          <a href="#who" className="ab-hero__more">
            Read our story <ArrowDown size={14} />
          </a>
        </div>
      </div>

      <div className="ab-hero__wall" aria-hidden="true">
        {WALL.map((col, c) => (
          <div className="ab-hero__col" key={c} style={{ '--c': c }}>
            <div className="ab-hero__track">
              {[0, 1].map((copy) =>
                col.map((it) => (
                  <div className="ab-hero__tile" key={`${copy}-${it.src}`}>
                    {it.film ? (
                      <VideoLoop src={it.film} poster={it.src} />
                    ) : (
                      <Img src={it.src} alt="" sizes="(min-width: 900px) 16vw, 32vw" priority={copy === 0} />
                    )}
                  </div>
                )),
              )}
            </div>
          </div>
        ))}
      </div>
    </header>
  )
}

/* --- who we are ----------------------------------------------------------- */

function WhoWeAre() {
  const sec = useRef(null)
  useScrollVar(sec, { from: 1, to: -0.9, name: '--s', ease: 0.1 })

  return (
    <section ref={sec} className="section on-stone ab-begin" id="who">
      <p className="ab-begin__ghost" aria-hidden="true">
        Zion · {ESTABLISHED} · Zion
      </p>
      <div className="shell">
        <p className="ld-label ab-begin__label">Who we are</p>
        <Scrub className="ab-begin__line" text={WHO_WE_ARE.opening} />
        <div className="ab-begin__grid">
          <figure className="ab-begin__frame">
            <div className="ab-begin__tilt">
              <Img
                src="/media/frames/workshop-sparks.jpg"
                alt="A Zion technician grinding a steel section in the workshop"
                ratio="4 / 5"
                sizes="(min-width: 900px) 34vw, 92vw"
                objectPosition="72% 50%"
                parallax={20}
              />
            </div>
          </figure>
          <div className="ab-begin__body">
            {WHO_WE_ARE.body.map((line) => (
              <Scrub key={line} span={0.3} text={line} />
            ))}
            <Reveal className="ab-founder">
              <span className="ab-founder__mark" aria-hidden="true">
                {WHO_WE_ARE.founder.name[0]}
              </span>
              <span>
                <strong>{WHO_WE_ARE.founder.name}</strong>
                <em>{WHO_WE_ARE.founder.role}</em>
              </span>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  )
}

/* --- where our lifts work: five buildings, read at a glance ----------------
   One row of five cards on the paper: a photograph of the kind of building,
   its name, one line, and the lifts it usually takes as plain links. Nothing
   to open or scroll through — everything is on the card. On a phone the row
   becomes a strip that swipes sideways, so the section stays short. */
function Sectors() {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.4 })

  return (
    <section className="section on-paper ab-sectors" aria-labelledby="sectors-title">
      <div className="shell">
        <header className="ab-head">
          <div>
            <p className="ld-label ab-sectors__label">Where our lifts work</p>
            <RiseIn
              as="h2"
              className="ab-h2"
              id="sectors-title"
              text="World-class lifts for every building."
              accent={false}
            />
          </div>
          <Reveal delay={100}>
            <p className="ab-lead">
              A wide range of current-generation elevator solutions — for residential buildings, commercial and
              corporate towers, industries, malls and hotels, to name a few.
            </p>
          </Reveal>
        </header>

        <ul ref={ref} className="ab-bldgs">
          {SECTORS.map((sec, i) => (
            <li key={sec.name} className="ab-bldg" style={{ '--i': i }}>
              <span className="ab-bldg__media" aria-hidden="true">
                <Img src={sec.src} alt="" sizes="(min-width: 1100px) 19vw, (min-width: 700px) 30vw, 72vw" objectPosition={sec.pos} />
              </span>
              <div className="ab-bldg__copy">
                <h3>{sec.name}</h3>
                <p>{sec.line}</p>
                <ul className="ab-bldg__lifts" aria-label={`Lifts for ${sec.name.toLowerCase()}`}>
                  {sec.lifts.map(([slug, label]) => (
                    <li key={slug}>
                      <Link to={`/lifts/${slug}`}>
                        {label} <Arrow size={12} />
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ul>

        <div className="ab-sectors__ask">
          <p>
            <strong>Not sure which lift your building needs?</strong>
            <span>Tell us the floors and what it has to carry — an engineer will recommend one.</span>
          </p>
          <Link to="/contact#enquiry" className="ab-sectors__go">
            Ask an engineer <Arrow size={14} />
          </Link>
        </div>
      </div>
    </section>
  )
}

/* --- modernisation and service -------------------------------------------- */

function Modernisation() {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.35 })

  return (
    <section className="section on-stone ab-modern">
      <div ref={ref} className="shell ab-modern__grid">
        <figure className="ab-modern__film">
          <VideoLoop src="/media/motion/about-modernise-light.mp4" poster="/media/motion/about-modernise-light.jpg" ratio="1 / 1" />
        </figure>

        <div className="ab-modern__copy">
          <p className="ld-label">Modernisation &amp; service network</p>
          <RiseIn as="h2" className="ab-h2" text="Old lifts, made new again." />
          {MODERNISATION.body.map((p) => (
            <Reveal key={p} as="p" className="ab-lead">
              {p}
            </Reveal>
          ))}
          <Link to="/service" className="ab-go">
            <span>Service &amp; modernisation</span>
            <span className="ab-go__ring">
              <Arrow size={16} />
            </span>
          </Link>
        </div>
      </div>

      <div className="shell">
        <Scrub className="ab-modern__closing" text={MODERNISATION.closing} />
      </div>
    </section>
  )
}

/* --- the values: a stack of cards ------------------------------------------ */

function Values() {
  const ref = useRef(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    if (reduced || !ref.current) return undefined
    const slots = [...ref.current.querySelectorAll('.ab-stack__slot')]
    const last = slots.map(() => -1)
    const tick = () => {
      const vh = window.innerHeight
      const box = ref.current.getBoundingClientRect()
      if (box.bottom < -vh * 0.5 || box.top > vh * 1.5) return
      slots.forEach((slot, i) => {
        const r = slot.getBoundingClientRect()
        const arrive = clamp01((vh - r.top) / (vh * 0.75))
        const next = slots[i + 1]?.getBoundingClientRect()
        const cover = next ? clamp01(1 - (next.top - r.top) / r.height) : 0
        const key = arrive + cover * 10
        if (Math.abs(key - last[i]) < 0.002) return
        last[i] = key
        slot.style.setProperty('--in', arrive.toFixed(4))
        slot.style.setProperty('--q', cover.toFixed(4))
      })
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced])

  return (
    <section className="section on-paper ab-method">
      <div className="shell">
        <header className="ab-head">
          <RiseIn as="h2" className="ab-h2" text="Our core value system." />
          <Reveal delay={100}>
            <p className="ab-lead">Six things every person at Zion signs up to — from the workshop floor to the site.</p>
          </Reveal>
        </header>

        <div ref={ref} className={`ab-stack ${reduced ? 'is-still' : ''}`}>
          {VALUES.map((v, i) => (
            <div className="ab-stack__slot" key={v.name} style={{ '--i': i }}>
              <article className="ab-card">
                <div className="ab-card__media">
                  <Img src={v.src} alt="" sizes="(min-width: 900px) 46vw, 92vw" />
                </div>
                <div className="ab-card__copy">
                  <h3>{v.name}</h3>
                  <p className="ab-card__text">{v.body}</p>
                </div>
              </article>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* --- awards & recognition: the organisers' own marks ----------------------
   Built like the home page's certification cards — white cards on the ivory,
   the mark as the picture and the facts as its caption — and brought up in
   reading order the way the promises wall below is. The four Times Business
   Awards take the first row, the listings and the certificate the second. */
function Awards() {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.3 })

  return (
    <section className="section on-stone ab-awards" id="awards" aria-labelledby="awards-title">
      <div className="shell">
        <header className="ab-head">
          <div>
            <p className="ld-label">Awards &amp; recognition</p>
            <RiseIn as="h2" className="ab-h2" id="awards-title" text="Recognised, year after year." />
          </div>
          <Reveal delay={100}>
            <p className="ab-lead">
              Four Times Business Awards in a row, two Industry Outlook Top 10 listings, and a quality system
              certified to ISO 9001:2015.
            </p>
          </Reveal>
        </header>

        <ul ref={ref} className="ab-awards__grid">
          {AWARDS.map((a, i) => (
            <li key={a.id} className="ab-award" style={{ '--i': i }}>
              <span className="ab-award__mark">
                <img src={a.logo} alt={`${a.body} ${a.year}`} loading="lazy" decoding="async" />
              </span>
              <p className="ab-award__meta">
                <span>{a.body}</span>
                <span>{a.year}</span>
              </p>
              <h3 className="ab-award__title">{a.title}</h3>
              <p className="ab-award__note">{a.note}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

/* --- what we are known for: a wall of photographs and drawings ------------ */

function KnownFor() {
  const ref = useRef(null)
  useScrollVar(ref, { from: 0.95, to: 0.05 })

  return (
    <section className="section on-paper ab-known">
      <div className="shell">
        <header className="ab-head">
          <RiseIn as="h2" className="ab-h2" text="What we are known for." />
          <Reveal delay={100}>
            <p className="ab-lead">
              Eight things our clients count on — the people, the lifts they build, and the way they are looked
              after.
            </p>
          </Reveal>
        </header>

        <ol ref={ref} className="ab-known__grid">
          {KNOWN_FOR.map((k, i) => (
            <li
              className={`ab-known__tile ${k.wide ? 'is-wide' : ''} ${k.src ? 'is-photo' : 'is-film'}`}
              key={k.id}
              style={{ '--i': i }}
            >
              <div className="ab-known__media">
                {k.src ? (
                  <Img src={k.src} alt="" sizes="(min-width: 1000px) 46vw, 92vw" />
                ) : (
                  <VideoLoop src={k.film} poster={k.poster} />
                )}
              </div>
              <div className="ab-known__copy">
                <p className="ab-known__text">{k.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

/* --- in their words -------------------------------------------------------- */

function Reviews() {
  const half = Math.ceil(REVIEWS.length / 2)
  const rows = [REVIEWS.slice(0, half), REVIEWS.slice(half)]

  return (
    <section className="section on-stone ab-reviews" aria-labelledby="reviews-title">
      <div className="shell ab-head">
        <div>
          <p className="ld-label">Client reviews</p>
          <RiseIn as="h2" className="ab-h2" id="reviews-title" text="In their own words." />
        </div>
        <Reveal delay={100}>
          <p className="ab-lead">
            From homeowners who were told a lift would not fit, to buildings that cannot close for a repair.
          </p>
        </Reveal>
      </div>

      <div className="ab-reviews__rows">
        {rows.map((row, r) => (
          <div key={r} className={`ab-reviews__row ${r ? 'is-back' : ''}`} style={{ '--n': row.length }}>
            <ul className="ab-reviews__track">
              {[0, 1].map((copy) =>
                row.map((rv) => (
                  <li key={`${copy}-${rv.name}`} className="ab-review" aria-hidden={copy === 1 || undefined}>
                    <blockquote>
                      <p>{rv.quote}</p>
                    </blockquote>
                    <p className="ab-review__who">
                      <span className="ab-review__mark" aria-hidden="true">
                        {rv.name[0]}
                      </span>
                      {rv.name}
                    </p>
                  </li>
                )),
              )}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}

/* --- get in touch ----------------------------------------------------------- */

function Invitation() {
  const wrap = useRef(null)
  useScrollVar(wrap, { from: 1, to: 0.15 })

  return (
    <div ref={wrap} className="ab-invite-wrap">
      <section className="ab-invite">
        <div className="ab-invite__scene">
          <Img src="/media/frames/lekha-aerial.jpg" alt="" sizes="100vw" />
        </div>
        <div className="ab-invite__copy">
          <p className="ld-label">Get in touch</p>
          <h2 className="ab-invite__title ld-rise">
            <Rise text="Get in touch with us today." />
          </h2>
          <address className="ab-invite__lead">{OFFICES.works}</address>
          <div className="ab-invite__actions">
            <Link to="/contact" className="ab-go">
              <span>Contact us</span>
              <span className="ab-go__ring">
                <Arrow size={16} />
              </span>
            </Link>
            {OFFICES.phones.map((p) => (
              <a key={p} href={telHref(p)} className="ab-invite__alt">
                {p}
              </a>
            ))}
            <a href={`mailto:${OFFICES.email}`} className="ab-invite__alt">
              {OFFICES.email}
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}

/* --- page ----------------------------------------------------------------- */

export default function About() {
  useEffect(() => {
    document.title = 'About — Zion Lifts'
  }, [])

  return (
    <div className="ab">
      <Opening />
      <WhoWeAre />
      <Sectors />
      <Modernisation />
      <Values />
      <Awards />
      <KnownFor />
      <Reviews />
      <ClientLogos
        eyebrow="Our clients"
        title="1000+ satisfied clients."
        lead="Residential buildings, corporate towers, industries, malls and hotels — a few of the names we look after."
      />
      <Invitation />
    </div>
  )
}
