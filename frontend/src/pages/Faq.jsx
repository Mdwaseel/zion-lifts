import { useEffect, useMemo, useState } from 'react'

import Reveal from '@/components/Reveal'
import { Accordion, CtaBand, PageHero } from '@/components/sections'
import { faqCategories } from '@/data/faqs'

import './faq.css'

export default function Faq() {
  const [active, setActive] = useState('all')
  const [query, setQuery] = useState('')

  useEffect(() => {
    document.title = 'Questions, answered — Zion Lifts'
  }, [])

  // Static — see src/data/faqs.js. An empty section would render a chip
  // reading 0 above nothing, so sections with no questions are dropped.
  const cats = useMemo(() => faqCategories().filter((c) => c.questions.length > 0), [])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return cats
      .filter((c) => active === 'all' || c.slug === active)
      .map((c) => ({
        ...c,
        questions: q
          ? c.questions.filter(
              (item) =>
                item.question.toLowerCase().includes(q) || item.answer.toLowerCase().includes(q),
            )
          : c.questions,
      }))
      .filter((c) => c.questions.length > 0)
  }, [cats, active, query])

  const total = cats.reduce((n, c) => n + c.questions.length, 0)
  const shown = visible.reduce((n, c) => n + c.questions.length, 0)

  return (
    <>
      <PageHero
        eyebrow="Need to know"
        title="Questions, answered."
        lead={`${total} of the things people actually ask us, grouped by what you are trying to decide. If yours is not here, it is a good reason to call.`}
        crumbs={[{ label: 'Home', to: '/' }, { label: 'FAQ' }]}
      />

      <section className="section">
        <div className="shell faqlayout">
          {/* jump nav */}
          <aside className="faqnav">
            <label className="field faqnav__search">
              <span className="field__label">Search</span>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Shaft size, safety, AMC…"
              />
            </label>
            <nav aria-label="Question categories">
              <ul className="faqnav__list">
                <li>
                  <button
                    type="button"
                    className={`faqnav__btn ${active === 'all' ? 'is-on' : ''}`}
                    onClick={() => setActive('all')}
                  >
                    Everything <sup>{total}</sup>
                  </button>
                </li>
                {cats.map((c) => (
                  <li key={c.slug}>
                    <button
                      type="button"
                      className={`faqnav__btn ${active === c.slug ? 'is-on' : ''}`}
                      onClick={() => setActive(c.slug)}
                    >
                      {c.name} <sup>{c.questions.length}</sup>
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>

          <div className="faqbody">
            {query && (
              <p className="faqbody__count mono">
                {shown} result{shown === 1 ? '' : 's'} for &ldquo;{query}&rdquo;
              </p>
            )}
            {visible.length === 0 ? (
              <div className="state">
                <p className="state__title">Nothing matches that.</p>
                <p className="body">
                  Try a broader word, or ask us directly — an unanswered question usually means we
                  should add it here.
                </p>
              </div>
            ) : (
              visible.map((c) => (
                <section className="faqgroup" key={c.slug} id={c.slug}>
                  <Reveal variant="fade">
                    <header className="faqgroup__head">
                      <h2 className="faqgroup__title">{c.name}</h2>
                      {c.description && <p className="faqgroup__desc">{c.description}</p>}
                    </header>
                  </Reveal>
                  <Accordion items={c.questions} />
                </section>
              ))
            )}
          </div>
        </div>
      </section>

      <CtaBand
        eyebrow="Still deciding?"
        title="Ask an engineer instead."
        lead="Most of these answers get more useful once we know your building. Send a plan and we will answer against it."
        primary={{ to: '/contact', label: 'Get a quote' }}
        secondary={{ to: '/lifts', label: 'Compare the range' }}
      />
    </>
  )
}
