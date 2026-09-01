/**
 * The site assistant — a docked panel over the RAG service.
 *
 * It is a widget rather than a page on purpose: the questions it answers
 * ("what capacity do I need for six floors?", "how long is a machine-room-less
 * install?") arrive while someone is reading a product page, and sending them
 * somewhere else to ask loses the thing they were asking about.
 *
 * Three behaviours are worth knowing before reading the code:
 *
 *   - It is honest about grounding. Answers stream in with `[1]` markers, the
 *     passages behind them are one click away, and a weak retrieval says so
 *     instead of presenting a guess in the same voice as a fact.
 *   - It never traps the visitor. Escape closes it, a request in flight can be
 *     stopped, and every failure ends at the contact form rather than a dead end.
 *   - Below 640px it is a sheet, not a bubble: full height, modal, with the page
 *     behind it locked. A 380px panel floating over a phone is neither.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert, Arrow, ArrowDown, Check, Close } from '@/components/icons'
import { MAX_QUESTION, AssistantError, ask, resetSession } from '@/lib/assistant'
import { useEscape, useMediaQuery, useReducedMotion, useScrollLock } from '@/lib/hooks'

import Answer from './assistant/Answer'
import Mark from './assistant/Mark'
import RelatedPages from './assistant/RelatedPages'
import Sources, { Confidence } from './assistant/Sources'
import './Assistant.css'

const STORE_KEY = 'zion.assistant.transcript'
/** Enough to keep the thread readable, short enough to stay under the quota. */
const KEEP = 30

/** The counter stays out of the way until the limit is actually in sight. */
const COUNT_FROM = MAX_QUESTION - 300

const OPENERS = [
  'Which lift suits a four-storey home?',
  'What is the difference between MRL and hydraulic?',
  'How long does an installation take?',
  'What does an AMC cover?',
]

let seq = 0
const nextId = () => `m${Date.now().toString(36)}${(seq++).toString(36)}`

function load() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) ?? '[]')
    // A message left mid-stream by a reload is finished text, not a live one.
    return Array.isArray(saved)
      ? saved.map((m) => (m.status === 'streaming' ? { ...m, status: 'done' } : m))
      : []
  } catch {
    return []
  }
}

function save(messages) {
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(messages.slice(-KEEP)))
  } catch {
    /* private mode, or over quota — the transcript is a convenience */
  }
}

/**
 * The citation numbers an answer can legitimately point at.
 *
 * A marker with nothing behind it is drawn as plain text rather than as a
 * button that opens an empty drawer, so `Answer` needs the set rather than the
 * count: the service numbers its citations, and the numbering is not always
 * `1..n`.
 */
function markersOf(citations) {
  if (!citations?.length) return undefined
  return new Set(
    citations.map(
      (citation, i) => Number(String(citation.marker ?? '').replace(/\D/g, '')) || i + 1,
    ),
  )
}

export default function Assistant() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState(load)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [openSources, setOpenSources] = useState(null) // message id
  const [activeCite, setActiveCite] = useState(null)
  const [copiedId, setCopiedId] = useState(null)
  const [atBottom, setAtBottom] = useState(true)

  const isSheet = useMediaQuery('(max-width: 640px)')
  const reduced = useReducedMotion()

  const panelRef = useRef(null)
  const launcherRef = useRef(null)
  const inputRef = useRef(null)
  const logRef = useRef(null)
  const abortRef = useRef(null)
  const pinned = useRef(true) // is the log scrolled to the bottom?

  useScrollLock(open && isSheet)
  useEscape(() => setOpen(false), open)

  useEffect(() => save(messages), [messages])

  // Abandon a request in flight if the component goes away mid-answer.
  useEffect(() => () => abortRef.current?.abort(), [])

  useEffect(() => {
    if (copiedId == null) return
    const t = setTimeout(() => setCopiedId(null), 1600)
    return () => clearTimeout(t)
  }, [copiedId])

  /* --- scrolling -------------------------------------------------------- */

  // Follow the stream, but only while the visitor is already at the bottom:
  // yanking the view down while they are re-reading an earlier answer is worse
  // than letting new text arrive off-screen.
  useEffect(() => {
    if (!open || !pinned.current) return
    const log = logRef.current
    if (log) log.scrollTop = log.scrollHeight
  }, [messages, open])

  const onLogScroll = useCallback((e) => {
    const el = e.currentTarget
    const bottom = el.scrollHeight - el.scrollTop - el.clientHeight < 64
    pinned.current = bottom
    // Mirrored into state only for the jump button, so a scroll that does not
    // cross the threshold costs nothing.
    setAtBottom((was) => (was === bottom ? was : bottom))
  }, [])

  const toBottom = useCallback(() => {
    pinned.current = true
    setAtBottom(true)
    const log = logRef.current
    log?.scrollTo({ top: log.scrollHeight, behavior: reduced ? 'auto' : 'smooth' })
  }, [reduced])

  /* --- focus ------------------------------------------------------------ */

  useEffect(() => {
    if (open) {
      // Wait for the panel's entry transition so focus does not scroll the
      // page to a control that is still translating into place.
      const t = setTimeout(() => inputRef.current?.focus(), reduced ? 0 : 220)
      return () => clearTimeout(t)
    }
    launcherRef.current?.focus()
  }, [open, reduced])

  // As a sheet the panel is modal, so Tab must not walk out into the page
  // behind it. As a docked bubble it is not, and trapping would be wrong.
  useEffect(() => {
    if (!open || !isSheet) return
    const onKey = (e) => {
      if (e.key !== 'Tab') return
      const focusable = panelRef.current?.querySelectorAll(
        'button:not([disabled]), a[href], textarea, input, [tabindex]:not([tabindex="-1"])',
      )
      if (!focusable?.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    const node = panelRef.current
    node?.addEventListener('keydown', onKey)
    return () => node?.removeEventListener('keydown', onKey)
  }, [open, isSheet])

  /* --- asking ----------------------------------------------------------- */

  const patch = useCallback((id, changes) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, ...(typeof changes === 'function' ? changes(m) : changes) } : m,
      ),
    )
  }, [])

  const send = useCallback(
    async (question, { history }) => {
      const answerId = nextId()
      setMessages((prev) => [
        ...prev,
        {
          id: answerId,
          role: 'assistant',
          content: '',
          citations: [],
          pages: [],
          suggestions: [],
          status: 'streaming',
        },
      ])
      setBusy(true)
      pinned.current = true
      setAtBottom(true)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const meta = await ask({
          question,
          history,
          signal: controller.signal,
          onDelta: (delta) => patch(answerId, (m) => ({ content: m.content + delta })),
          onCitations: (citations) => patch(answerId, { citations }),
          // Intent and confidence land before the first token, so the answer
          // can be framed while it is still being written.
          onMeta: ({ intent, confidence, level }) =>
            patch(answerId, { intent, score: confidence, level }),
          onPages: (pages) => patch(answerId, { pages }),
        })
        patch(answerId, (m) => ({
          status: 'done',
          citations: meta.citations?.length ? meta.citations : m.citations,
          pages: meta.relatedPages?.length ? meta.relatedPages : m.pages,
          suggestions: meta.suggestions ?? [],
          intent: meta.intent ?? m.intent,
          level: meta.level ?? m.level,
          score: meta.confidence ?? m.score,
          // An empty answer is a failure the service did not report as one.
          content: m.content || 'I could not find anything about that in our documents.',
        }))
      } catch (error) {
        if (error?.name === 'AbortError') {
          // Stopped by the visitor: keep whatever arrived, drop the empty shell.
          setMessages((prev) =>
            prev
              .map((m) => (m.id === answerId ? { ...m, status: 'stopped' } : m))
              .filter((m) => m.id !== answerId || m.content.trim()),
          )
        } else {
          patch(answerId, {
            status: 'error',
            error:
              error instanceof AssistantError
                ? error.message
                : 'Something went wrong. Please try again.',
          })
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null
        setBusy(false)
      }
    },
    [patch],
  )

  const submit = useCallback(
    (raw) => {
      const question = raw.trim().slice(0, MAX_QUESTION)
      if (!question || busy) return

      const turn = { id: nextId(), role: 'user', content: question, status: 'done' }
      const history = messages
      setMessages((prev) => [...prev, turn])
      setDraft('')
      // The box grows with what you type, so it also has to shrink back — React
      // clearing the value does not undo an inline height set from scrollHeight.
      if (inputRef.current) inputRef.current.style.height = ''
      send(question, { history })
    },
    [busy, messages, send],
  )

  /** Re-asks the question that produced a failed answer, in place. */
  const retry = useCallback(
    (failedId) => {
      const index = messages.findIndex((m) => m.id === failedId)
      const question = messages[index - 1]?.content
      if (!question) return
      const history = messages.slice(0, index - 1)
      setMessages((prev) => prev.filter((m) => m.id !== failedId))
      send(question, { history })
    },
    [messages, send],
  )

  const clear = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setOpenSources(null)
    setActiveCite(null)
    resetSession()
    inputRef.current?.focus()
  }, [])

  const copyAnswer = useCallback((message) => {
    navigator.clipboard?.writeText(message.content).then(
      () => setCopiedId(message.id),
      () => {},
    )
  }, [])

  const onKeyDown = (e) => {
    // Enter sends; the panel is a conversation, and a newline is the rarer
    // intent. Shift+Enter still gets you one.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit(draft)
    }
  }

  const empty = messages.length === 0
  const over = draft.length > MAX_QUESTION
  const status = useMemo(() => {
    if (busy) return 'Looking through our documents…'
    return ''
  }, [busy])

  return (
    <>
      <button
        ref={launcherRef}
        type="button"
        className={`asst-launcher${open ? ' is-open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="assistant-panel"
      >
        <Mark size={28} className="asst-launcher__mark" />
        <span className="asst-launcher__label">Ask Zion</span>
      </button>

      <div
        id="assistant-panel"
        ref={panelRef}
        className={`asst${open ? ' is-open' : ''}${isSheet ? ' is-sheet' : ''}`}
        role="dialog"
        aria-label="Ask Zion — product assistant"
        aria-modal={isSheet ? 'true' : undefined}
        hidden={!open}
      >
        <header className="asst__head">
          <div className="asst__id">
            <Mark size={32} className="asst__mark" />
            <div>
              <p className="asst__title">Ask Zion</p>
              {/* The status line carries the one fact that changes — whether it
                  is working — rather than a description that never does. */}
              <p className={`asst__status${busy ? ' is-busy' : ''}`}>
                <span className="asst__dot" aria-hidden="true" />
                {busy ? 'Searching our documents…' : 'Product assistant · online'}
              </p>
            </div>
          </div>
          <div className="asst__head-actions">
            {!empty && (
              <button type="button" className="asst__ghost" onClick={clear}>
                New chat
              </button>
            )}
            <button
              type="button"
              className="asst__icon"
              onClick={() => setOpen(false)}
              aria-label="Close the assistant"
            >
              <Close size={16} />
            </button>
          </div>
        </header>

        <div className="asst__stage">
          <div
            className={`asst__log${empty ? ' asst__log--empty' : ''}`}
            ref={logRef}
            onScroll={onLogScroll}
          >
            {empty ? (
              <div className="asst__empty">
                {/* The mascot at full size, centred: with nothing said yet, the
                    thing that says what this is should be the thing you see. */}
                <span className="asst__avatar">
                  <Mark size={64} />
                </span>
                <p className="asst__empty-title">Ask Zion</p>
                <p className="asst__empty-lead">
                  Answers on lift types, capacities, shafts, installation and service — each
                  cites its source.
                </p>
                <p className="asst__openers-lead">Try one of these</p>
                <ul className="asst__openers">
                  {OPENERS.map((q) => (
                    <li key={q}>
                      <button type="button" onClick={() => submit(q)}>
                        {q}
                        <Arrow size={14} />
                      </button>
                    </li>
                  ))}
                </ul>
                <p className="asst__disclaimer">
                  For a binding specification or a quotation, please{' '}
                  <Link to="/contact" onClick={() => setOpen(false)}>
                    speak to our engineers
                  </Link>
                  .
                </p>
              </div>
            ) : (
              <ol className="asst__thread">
                {messages.map((m) =>
                  m.role === 'user' ? (
                    <li key={m.id} className="asst-msg asst-msg--you">
                      <p>{m.content}</p>
                    </li>
                  ) : (
                    <li key={m.id} className="asst-msg asst-msg--zion">
                      {/* A fixed gutter with the mascot in it: you can tell who
                          is speaking without reading a word of the turn. */}
                      <Mark size={30} className="asst-msg__avatar" />
                      <div className="asst-msg__body">
                        {m.status === 'error' ? (
                          <div className="asst-fail">
                            <p>
                              <Alert size={14} /> {m.error}
                            </p>
                            <div className="asst-fail__actions">
                              <button type="button" onClick={() => retry(m.id)}>
                                Try again
                              </button>
                              <Link to="/contact" onClick={() => setOpen(false)}>
                                Contact us instead
                              </Link>
                            </div>
                          </div>
                        ) : (
                          <>
                            {m.content ? (
                              <Answer
                                text={m.content}
                                streaming={m.status === 'streaming'}
                                markers={markersOf(m.citations)}
                                onCite={(n) => {
                                  setOpenSources(m.id)
                                  setActiveCite(n)
                                }}
                              />
                            ) : (
                              <p className="asst-thinking">
                                <span className="asst-thinking__dots" aria-hidden="true">
                                  <span />
                                  <span />
                                  <span />
                                </span>
                                Searching our documents…
                              </p>
                            )}
                            {m.status !== 'streaming' && (
                              <>
                                <Confidence
                                  level={m.level}
                                  score={m.score}
                                  intent={m.intent}
                                  hasCitations={Boolean(m.citations?.length)}
                                />
                                {/* Sources and copy share one row: they are the
                                    two things anyone does with an answer. */}
                                {m.content && (
                                  <div className="asst-msg__tools">
                                    <Sources
                                      citations={m.citations}
                                      open={openSources === m.id}
                                      active={openSources === m.id ? activeCite : null}
                                      inline
                                      onNavigate={() => setOpen(false)}
                                      onToggle={() => {
                                        setActiveCite(null)
                                        setOpenSources((id) => (id === m.id ? null : m.id))
                                      }}
                                    />
                                    <button
                                      type="button"
                                      className="asst-tool"
                                      onClick={() => copyAnswer(m)}
                                    >
                                      {copiedId === m.id ? <Check size={13} /> : null}
                                      {copiedId === m.id ? 'Copied' : 'Copy answer'}
                                    </button>
                                  </div>
                                )}
                                <RelatedPages
                                  pages={m.pages}
                                  onNavigate={() => setOpen(false)}
                                />
                                {m.suggestions?.length ? (
                                  <ul className="asst-followups">
                                    {m.suggestions.slice(0, 3).map((q) => (
                                      <li key={q}>
                                        <button
                                          type="button"
                                          disabled={busy}
                                          onClick={() => submit(q)}
                                        >
                                          {q}
                                        </button>
                                      </li>
                                    ))}
                                  </ul>
                                ) : null}
                              </>
                            )}
                          </>
                        )}
                      </div>
                    </li>
                  ),
                )}
              </ol>
            )}
          </div>

          {!empty && !atBottom && (
            <button type="button" className="asst__jump" onClick={toBottom}>
              <ArrowDown size={13} />
              Latest
            </button>
          )}
        </div>

        {/* Politeness matters here: assertive would interrupt a screen reader
            on every streamed token. The log itself is read on request. */}
        <p className="sr-only" role="status" aria-live="polite">
          {status}
        </p>

        <form
          className="asst__composer"
          onSubmit={(e) => {
            e.preventDefault()
            submit(draft)
          }}
        >
          <label className="sr-only" htmlFor="asst-input">
            Your question
          </label>
          {/* The field and its send control are one surface, so the focus ring
              belongs to the dock rather than to the textarea inside it. */}
          <div className={`asst__dock${over ? ' is-over' : ''}`}>
            <textarea
              id="asst-input"
              ref={inputRef}
              className="asst__input"
              rows={1}
              value={draft}
              placeholder="Ask about a lift or a service plan…"
              onChange={(e) => {
                setDraft(e.target.value)
                // Grow with the text, up to the cap set in CSS.
                e.target.style.height = 'auto'
                e.target.style.height = `${e.target.scrollHeight}px`
              }}
              onKeyDown={onKeyDown}
              aria-describedby={draft.length > COUNT_FROM ? 'asst-count' : undefined}
              aria-invalid={over || undefined}
            />

            {busy ? (
              <button
                type="button"
                className="asst__stop"
                onClick={() => abortRef.current?.abort()}
                aria-label="Stop the answer"
              >
                <span aria-hidden="true" />
              </button>
            ) : (
              <button
                type="submit"
                className="asst__send"
                disabled={!draft.trim() || over}
                aria-label="Send question"
              >
                <Arrow size={16} />
              </button>
            )}
          </div>

          <p className="asst__foot">
            {/* Short on purpose: the empty state already makes the longer
                promise, and this one has to hold one line under the field. */}
            <span>AI answers — verify critical specifications with us.</span>
            {draft.length > COUNT_FROM && (
              <span className={`asst__count${over ? ' is-over' : ''}`} id="asst-count">
                {over
                  ? `${(draft.length - MAX_QUESTION).toLocaleString()} over the limit`
                  : `${draft.length.toLocaleString()} / ${MAX_QUESTION.toLocaleString()}`}
              </span>
            )}
          </p>
        </form>
      </div>
    </>
  )
}
