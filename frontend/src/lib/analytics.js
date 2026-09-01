/**
 * The page-view beacon on the public site.
 *
 * Three rules shape this file, and everything in it follows from them.
 *
 * **It must never slow a page down.** The send is `navigator.sendBeacon`, which
 * hands the request to the browser and returns immediately — it is not awaited,
 * it does not block paint, and it survives the page being navigated away from.
 * `fetch(..., {keepalive: true})` is the fallback, which behaves the same way
 * where sendBeacon is missing. Nothing here ever holds up a render.
 *
 * **It must never break a page.** Every call is wrapped. A visitor with storage
 * disabled, an ad blocker eating the request, an offline device — all of them
 * produce a page that works and no analytics row, which is the correct trade in
 * that order.
 *
 * **It must not double-count.** A React route change and an effect re-running
 * are not two visits to a page. The last path sent is remembered, and each view
 * carries an `event_id` the server uses as an idempotency key, so even a
 * network-level retry lands once.
 *
 * What is stored in the browser: one random id in a first-party `visitor_id`
 * cookie, and nothing else. No name, no address, no profile. It is what lets
 * five pages from one person count as one visitor rather than five, and it means
 * nothing outside our own analytics tables. Clearing cookies is the intended way
 * to opt out, and the visitor simply becomes a new anonymous id.
 */

const BASE = import.meta.env?.VITE_API_BASE ?? '/api'
const ENDPOINT = `${BASE}/analytics/track/`

const VISITOR_COOKIE = 'visitor_id'

// Two years. Long enough that "returning visitor" means something over the life
// of a project enquiry, which is the timescale this business actually works on.
const VISITOR_TTL_DAYS = 730

// Route changes that land within this window on the same page are the same
// view — a remount, a replaceState, a double-invoked effect in StrictMode.
// Nobody navigates away and back inside a second and a half, so nothing real is
// lost by collapsing them.
const DEDUPE_MS = 1500

let lastPath = null
let lastSentAt = 0

/** Crypto-random where available; the fallback only has to be unique enough. */
function uuid() {
  try {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  } catch {
    /* fall through */
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const rand = (Math.random() * 16) | 0
    const value = char === 'x' ? rand : (rand & 0x3) | 0x8
    return value.toString(16)
  })
}

/** Reads our one cookie. Same shape as `csrfToken()` in `api/client.js`. */
function readVisitorCookie() {
  return document.cookie.match(/(?:^|;\s*)visitor_id=([^;]*)/)?.[1] ?? ''
}

function writeVisitorCookie(value) {
  const parts = [
    `${VISITOR_COOKIE}=${value}`,
    'path=/',
    `max-age=${VISITOR_TTL_DAYS * 86400}`,
    // Lax, not None: the id is only ever needed on our own pages, and Lax means
    // it is not attached to third-party requests at all.
    'SameSite=Lax',
  ]
  // Secure only over https — setting it on http silently makes the cookie
  // unstorable, which in development would mean a new "visitor" on every page.
  if (window.location.protocol === 'https:') parts.push('Secure')
  document.cookie = parts.join('; ')
}

/**
 * The browser's anonymous id, from a first-party cookie.
 *
 * Not HttpOnly, because this script is what reads and writes it; there is
 * nothing to protect from script access that script access is not already the
 * point of. It carries no personal data — it is a random uuid whose only
 * meaning is "the same browser as last time".
 *
 * Wrapped because `document.cookie` can be inert or throw where site data is
 * blocked. A visitor we cannot remember gets a fresh id per page and counts as
 * several people; undercounting uniques is the acceptable failure here, and it
 * is strictly better than an error on the first paint.
 */
function visitorId() {
  try {
    const existing = readVisitorCookie()
    if (existing) return existing

    const fresh = uuid()
    writeVisitorCookie(fresh)
    // Read it back: where site data is blocked the write is silently a no-op,
    // and returning `fresh` regardless would claim a persistence we do not have.
    return readVisitorCookie() || fresh
  } catch {
    return uuid()
  }
}

/** Fire and forget. Returns false only so callers can be tested, never awaited. */
function send(payload) {
  const body = JSON.stringify(payload)
  try {
    if (navigator.sendBeacon) {
      // The type matters: DRF parses JSON, and a Blob without it arrives as
      // text/plain and is rejected before it reaches the view.
      return navigator.sendBeacon(ENDPOINT, new Blob([body], { type: 'application/json' }))
    }
  } catch {
    /* fall through to fetch */
  }

  try {
    fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      // Survives the page being unloaded mid-flight, which is exactly when the
      // last page view of a visit is sent.
      keepalive: true,
      // The endpoint is anonymous and CSRF-exempt by virtue of having no
      // session; sending cookies would only add weight.
      credentials: 'omit',
    }).catch(() => {})
    return true
  } catch {
    return false
  }
}

/**
 * Record one page view.
 *
 * `referrer` is taken from `document.referrer` on the first view of a visit and
 * left empty afterwards: on a single-page app the browser's referrer still
 * points at whatever loaded the app shell, so sending it on every route change
 * would credit the same external source over and over.
 */
export function trackPageView(path, { force = false } = {}) {
  if (typeof window === 'undefined') return false

  // Dedupe on the *page*, not on the URL. The server stores a path with its
  // query string stripped, so `/` and `/?ref=x` are one row in Top Pages — and
  // anything that rewrites the query without changing the page (a modal putting
  // its state in the URL, a router dropping campaign parameters, an extension)
  // would otherwise fire a second view for a page nobody navigated to twice.
  const page = pageOf(path)
  const now = Date.now()
  if (!force && page === lastPath && now - lastSentAt < DEDUPE_MS) return false

  const isFirstOfPageLoad = lastPath === null
  lastPath = page
  lastSentAt = now

  try {
    return send({
      visitor_id: visitorId(),
      event_id: uuid(),
      path,
      referrer: isFirstOfPageLoad ? document.referrer || '' : '',
    })
  } catch {
    return false
  }
}

/** The stored form of a path: no query, no fragment. Mirrors the server's rule. */
function pageOf(path) {
  return String(path).split('?')[0].split('#')[0] || '/'
}

/** Test seam: forget what was last sent. Not used by the app. */
export function resetForTests() {
  lastPath = null
  lastSentAt = 0
}
