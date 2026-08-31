/**
 * Fetch wrapper for the authenticated half of the API.
 *
 * Three things separate it from `lib/api.js`, which serves the public site:
 *
 *   1. `credentials: 'include'` — the browser attaches the auth cookies. The
 *      tokens themselves are HttpOnly, so nothing here can read them, and that
 *      is deliberate: a value JavaScript cannot reach is a value an injected
 *      script cannot steal.
 *   2. the CSRF header on every unsafe method, read from the one cookie Django
 *      does expose for exactly this purpose.
 *   3. a single-flight refresh on 401, so an expired access token renews itself
 *      once and the original request is retried rather than dumping the user
 *      back at the login page mid-task.
 */

// Optional-chained so the module also loads outside Vite, which is what lets
// auth-client.test.mjs exercise the refresh logic in plain Node.
const BASE = import.meta.env?.VITE_API_BASE ?? '/api'

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
const REFRESH_PATH = 'accounts/refresh/'

/** Requests that must never trigger a refresh — they *are* the auth handshake. */
const NO_REFRESH = new Set(['accounts/login/', 'accounts/refresh/', 'accounts/logout/'])

/** Thrown for every non-2xx response, so callers have one shape to handle. */
export class ApiError extends Error {
  constructor(status, payload) {
    super(payload?.detail ?? `Request failed (${status})`)
    this.name = 'ApiError'
    this.status = status
    this.code = payload?.code ?? null
    this.payload = payload ?? {}
  }

  /** DRF field errors, e.g. { email: ['Enter a valid email address.'] }. */
  get fields() {
    const { detail: _detail, code: _code, ...rest } = this.payload
    return rest
  }
}

function url(path) {
  return `${BASE}/${String(path).replace(/^\/+/, '')}`
}

/**
 * Django's CSRF token. Readable on purpose — it is a token, not a credential:
 * knowing it is useless to another site, which still cannot read it from *our*
 * origin and so cannot put it in a forged request's header.
 */
function csrfToken() {
  return document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ?? ''
}

// One refresh at a time. Without this, five requests failing together would
// fire five refreshes, and rotation would invalidate four of them.
let refreshing = null

function refreshSession() {
  refreshing ??= send(REFRESH_PATH, { method: 'POST', _retry: true }).finally(() => {
    refreshing = null
  })
  return refreshing
}

async function send(path, { method = 'GET', body, signal, _retry = false } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (!SAFE_METHODS.has(method)) {
    const token = csrfToken()
    if (token) headers['X-CSRFToken'] = token
  }

  const init = {
    method,
    headers,
    signal,
    credentials: 'include', // the whole point: cookies travel, JS never sees them
  }
  if (body !== undefined) init.body = JSON.stringify(body)

  let res
  try {
    res = await fetch(url(path), init)
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause
    throw new ApiError(0, { detail: 'Network error', code: 'network' })
  }

  const payload = res.status === 204 ? {} : await res.json().catch(() => ({}))
  if (res.ok) return payload

  // 401 once, and only once: refresh, then replay. `_retry` is what stops a
  // still-expired session from looping between here and /refresh/ forever.
  if (res.status === 401 && !_retry && !NO_REFRESH.has(path)) {
    try {
      await refreshSession()
    } catch {
      throw new ApiError(401, payload)
    }
    return send(path, { method, body, signal, _retry: true })
  }

  throw new ApiError(res.status, payload)
}

export const api = {
  get: (path, options) => send(path, { ...options, method: 'GET' }),
  post: (path, body, options) => send(path, { ...options, method: 'POST', body }),
}

export { refreshSession }
