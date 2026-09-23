/**
 * Client for the RAG service that backs the site assistant.
 *
 * The service runs beside Django rather than inside it, so this talks to its
 * own origin-relative prefix (`/ai`), which Vite proxies in development and the
 * edge proxy rewrites in production. That indirection is not cosmetic: the
 * service is guarded by an `X-API-Key`, and a key the browser can read is a key
 * anyone can read. The proxy holds it, so nothing here ever sees it.
 *
 * Answers arrive as server-sent events. `ask()` surfaces the stream as it lands
 * and falls back to the unary endpoint when streaming does not survive the
 * network — a corporate proxy that buffers `text/event-stream` should cost the
 * visitor a slower answer, not no answer.
 *
 * The event protocol is additive and this reader is written to stay that way:
 * `metadata` arrives before the first token, `delta` carries the answer,
 * `citations`, `related_pages` and `suggestions` follow it, and `done` closes.
 * Any `type` this file does not recognise is skipped rather than treated as an
 * error, which is what lets the service add an event without shipping a new
 * bundle first.
 */

const BASE = import.meta.env?.VITE_AI_BASE ?? '/ai/api/v1'

/** Mirrors MAX_QUESTION_CHARS on the service; failing here saves a round trip. */
export const MAX_QUESTION = 4000

/** Mirrors MAX_HISTORY_TURNS. Older turns are dropped rather than rejected. */
const MAX_HISTORY_MESSAGES = 20

const SESSION_KEY = 'zion.assistant.session'

/** Every failure the widget can render, with one shape and a human message. */
export class AssistantError extends Error {
  constructor(message, { status = 0, code = 'error' } = {}) {
    super(message)
    this.name = 'AssistantError'
    this.status = status
    this.code = code
  }
}

const MESSAGES = {
  401: 'The assistant is not configured for this site yet.',
  429: 'That is a lot of questions at once — give it a moment and try again.',
  502: 'The assistant could not reach a language model.',
  503: 'The assistant is offline for a moment. Please try again shortly.',
}

function describe(status, payload) {
  return (
    payload?.error?.message ??
    payload?.detail ??
    MESSAGES[status] ??
    'The assistant could not answer that. Please try again.'
  )
}

/**
 * One id per browser tab. A session id is a server-side correlation handle
 * rather than a credential, and a tab is the natural lifetime for one.
 */
export function sessionId() {
  try {
    let id = sessionStorage.getItem(SESSION_KEY)
    if (!id) {
      id = (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`).replace(/-/g, '')
      sessionStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    return undefined // private mode: let the service mint one for us
  }
}

export function resetSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    /* nothing to clear */
  }
}

/** The trailing turns, oldest first, in the shape the service expects. */
function toHistory(messages) {
  return messages
    .filter((m) => (m.role === 'user' || m.role === 'assistant') && m.content.trim())
    .slice(-MAX_HISTORY_MESSAGES)
    .map(({ role, content }) => ({ role, content }))
}

async function readError(res) {
  const payload = await res.json().catch(() => null)
  return new AssistantError(describe(res.status, payload), {
    status: res.status,
    code: payload?.error?.code ?? 'http_error',
  })
}

function payloadFor(question, history) {
  return JSON.stringify({
    question,
    history: toHistory(history),
    session_id: sessionId(),
    stream: true,
  })
}

/**
 * Splits an SSE byte stream into its `data:` payloads.
 *
 * Written by hand rather than with EventSource because EventSource can only
 * issue a GET, and the question does not belong in a query string.
 */
async function* events(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // Frames are separated by a blank line. Whatever follows the last one is
      // a partial frame, and has to wait for the next chunk.
      let split
      while ((split = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, split)
        buffer = buffer.slice(split + 2)

        const data = frame
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim())
          .join('')

        if (!data) continue
        if (data === '[DONE]') return
        try {
          yield JSON.parse(data)
        } catch {
          // A malformed frame is not worth abandoning the answer over.
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {})
  }
}

/** Every field an answer can carry, before any of it has arrived. */
function emptyMeta() {
  return {
    citations: [],
    relatedPages: [],
    suggestions: [],
    confidence: null,
    level: null,
    intent: null,
  }
}

/**
 * Asks a question, reporting progress through the callbacks.
 *
 * @param {object} opts
 * @param {string} opts.question
 * @param {Array}  opts.history            prior turns, oldest first
 * @param {AbortSignal} [opts.signal]
 * @param {(delta: string) => void} [opts.onDelta]
 * @param {(citations: Array) => void} [opts.onCitations]
 * @param {(meta: object) => void} [opts.onMeta]   intent and confidence, early
 * @param {(pages: Array) => void} [opts.onPages]
 * @returns {Promise<{citations: Array, relatedPages: Array, suggestions: Array,
 *   confidence: number|null, level: string|null, intent: string|null}>}
 */
export async function ask({
  question,
  history = [],
  signal,
  onDelta,
  onCitations,
  onMeta,
  onPages,
}) {
  const payload = payloadFor(question, history)
  const callbacks = { signal, onDelta, onCitations, onMeta, onPages }
  let res

  try {
    res = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: payload,
      signal,
    })
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause
    throw new AssistantError('No connection to the assistant.', { code: 'network' })
  }

  if (!res.ok) throw await readError(res)
  // No readable body means something between here and the service swallowed the
  // stream. Ask again without it rather than rendering an empty answer.
  if (!res.body) return unary(payload, callbacks)

  const meta = emptyMeta()
  let received = false

  for await (const chunk of events(res)) {
    switch (chunk.type) {
      case 'delta':
        if (chunk.content) {
          received = true
          onDelta?.(chunk.content)
        }
        break
      case 'metadata':
        // Arrives before the first token: how the question was understood and
        // how well it is supported, so the panel can frame the answer while it
        // is still being written.
        meta.intent = chunk.intent ?? null
        meta.confidence = typeof chunk.confidence === 'number' ? chunk.confidence : null
        meta.level = chunk.confidence_level ?? null
        onMeta?.({ intent: meta.intent, confidence: meta.confidence, level: meta.level })
        break
      case 'citations':
        meta.citations = chunk.citations ?? []
        onCitations?.(meta.citations)
        break
      case 'related_pages':
        meta.relatedPages = chunk.related_pages ?? []
        onPages?.(meta.relatedPages)
        break
      case 'suggestions':
        meta.suggestions = chunk.suggested_questions ?? []
        break
      case 'error':
        throw new AssistantError(chunk.error || describe(500), { code: 'stream_error' })
      default:
        // An event type this bundle predates. Ignored on purpose.
        break
    }
  }

  // A stream that closed without a single delta is indistinguishable from a
  // buffering proxy, and the unary endpoint is not vulnerable to that.
  if (!received) return unary(payload, callbacks)

  return meta
}

/** The non-streamed endpoint. Same answer, delivered in one piece. */
async function unary(payload, { signal, onDelta, onCitations, onMeta, onPages }) {
  let res
  try {
    res = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: payload,
      signal,
    })
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause
    throw new AssistantError('No connection to the assistant.', { code: 'network' })
  }

  if (!res.ok) throw await readError(res)

  const data = await res.json()
  const meta = {
    citations: data.citations ?? [],
    relatedPages: data.related_pages ?? [],
    suggestions: data.suggested_questions ?? [],
    confidence: typeof data.confidence === 'number' ? data.confidence : null,
    level: data.confidence_level ?? null,
    intent: data.intent ?? null,
  }

  onMeta?.({ intent: meta.intent, confidence: meta.confidence, level: meta.level })
  if (data.answer) onDelta?.(data.answer)
  if (meta.citations.length) onCitations?.(meta.citations)
  if (meta.relatedPages.length) onPages?.(meta.relatedPages)

  return meta
}

/** Whether the service is reachable. Keeps the launcher from promising an
 *  answer it cannot deliver. */
export async function ping({ signal } = {}) {
  try {
    const res = await fetch(`${BASE}/health`, {
      signal,
      headers: { Accept: 'application/json' },
    })
    return res.ok
  } catch {
    return false
  }
}
