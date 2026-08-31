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

import { Alert, Arrow, Close } from '@/components/icons'
import { MAX_QUESTION, AssistantError, ask, resetSession } from '@/lib/assistant'
import { useEscape, useMediaQuery, useReducedMotion, useScrollLock } from '@/lib/hooks'

import Answer from './assistant/Answer'
import Mark from './assistant/Mark'
import Sources, { Confidence } from './assistant/Sources'
import './Assistant.css'

const STORE_KEY = 'zion.assistant.transcript'
/** Enough to keep the thread readable, short enough to stay under the quota. */
const KEEP = 30

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

export default function Assistant() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState(load)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [openSources, setOpenSources] = useState(null) // message id
  const [activeCite, setActiveCite] = useState(null)

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
    pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 64
  }, [])

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
        { id: answerId, role: 'assistant', content: '', citations: [], status: 'streaming' },
      ])
      setBusy(true)
      pinned.current = true

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const meta = await ask({
          question,
          history,
          signal: controller.signal,
          onDelta: (delta) => patch(answerId, (m) => ({ content: m.content + delta })),
          onCitations: (citations) => patch(answerId, { citations }),
        })
        patch(answerId, (m) => ({
          status: 'done',
          citations: meta.citations?.length ? meta.citations : m.citations,
          level: meta.level,
          score: meta.confidence,
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
    resetSession()
    inputRef.current?.focus()
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
        <Mark size={26} className="asst-launcher__mark" />
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
            <Mark size={30} className="asst__mark" />
            <div>
              <p className="asst__title">Ask Zion</p>
              <p className="asst__sub">Answers from our own product and service documents</p>
            </div>
          </div>
          <div className="asst__head-actions">
            {!empty && (
              <button type="button" className="asst__ghost" onClick={clear}>
                New
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

        <div className="asst__log" ref={logRef} onScroll={onLogScroll}>
          {empty ? (
            <div className="asst__empty">
              <p className="asst__empty-lead">
                Ask about lift types, capacities, shaft dimensions, installation or maintenance.
                Every answer cites the document it came from.
              </p>
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
                            onCite={(n) => {
                              setOpenSources(m.id)
                              setActiveCite(n)
                            }}
                          />
                        ) : (
                          <p className="asst-thinking" aria-hidden="true">
                            <span />
                            <span />
                            <span />
                          </p>
                        )}
                        {m.status !== 'streaming' && (
                          <>
                            <Confidence level={m.level} score={m.score} />
                            <Sources
                              citations={m.citations}
                              open={openSources === m.id}
                              active={openSources === m.id ? activeCite : null}
                              onToggle={() => {
                                setActiveCite(null)
                                setOpenSources((id) => (id === m.id ? null : m.id))
                              }}
                            />
                          </>
                        )}
                      </>
                    )}
                  </li>
                ),
              )}
            </ol>
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
          <textarea
            id="asst-input"
            ref={inputRef}
            className="asst__input"
            rows={1}
            value={draft}
            placeholder="Ask about a lift, a spec, or a service plan…"
            onChange={(e) => {
              setDraft(e.target.value)
              // Grow with the text, up to the cap set in CSS.
              e.target.style.height = 'auto'
              e.target.style.height = `${e.target.scrollHeight}px`
            }}
            onKeyDown={onKeyDown}
            aria-describedby={over ? 'asst-limit' : undefined}
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
        </form>

        {over && (
          <p className="asst__limit" id="asst-limit">
            That is longer than {MAX_QUESTION.toLocaleString()} characters — please trim it.
          </p>
        )}
      </div>
    </>
  )
}
