/**
 * Thin client over the Django REST API.
 *
 * Every GET is memoised for the life of the page: the site is content-heavy and
 * largely static, and several sections request the same collection (lift types
 * appear on Home, /lifts, every product page and the contact form).
 */

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

/**
 * Static mode: the site is hosted as plain files (Vercel) with the API frozen
 * into public/api by scripts/snapshot-api.mjs. Reads resolve to those files and
 * writes are refused with a message the forms can show. Set by .env.static,
 * i.e. `npm run build:static`.
 */
export const STATIC = import.meta.env.VITE_STATIC_API === '1'

const cache = new Map()

function query(params) {
  if (!params) return ''
  return new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  ).toString()
}

/** Where a read lives in the frozen snapshot — the layout snapshot-api.mjs writes. */
function snapshotUrl(path, params) {
  const clean = `/api/${String(path).replace(/^\/+/, '')}`
  const dir = clean.endsWith('/') ? clean : `${clean}/`
  const qs = query(params)
  return qs ? `${dir}_q/${qs}.json` : `${dir}index.json`
}

function url(path, params) {
  if (STATIC) return snapshotUrl(path, params)
  const clean = `${BASE}/${String(path).replace(/^\/+/, '')}`
  const qs = query(params)
  return qs ? `${clean}?${qs}` : clean
}

/* In dev, a Django that is not running shows up as the proxy's 502 (or a
   refused connection). Rather than leave every page empty, reads fall back to
   the snapshot in public/api — the same files the static site serves — and
   say so once in the console. Real 4xx answers from the API are not masked. */
let warned = false
const unreachable = (err) => !err.status || err.status >= 500

async function fetchJson(key, signal) {
  const res = await fetch(key, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) {
    const err = new Error(`${res.status} ${res.statusText} — ${key}`)
    err.status = res.status
    throw err
  }
  return unwrap(await res.json())
}

/** Unwraps DRF pagination so callers always receive a plain array. */
function unwrap(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return data
}

export async function get(path, params, { signal } = {}) {
  const key = url(path, params)
  if (cache.has(key)) return cache.get(key)

  const promise = fetchJson(key, signal)
    .catch((err) => {
      if (STATIC || !import.meta.env.DEV || err.name === 'AbortError' || !unreachable(err)) throw err
      if (!warned) {
        warned = true
        console.warn('[api] The API is not answering — showing the snapshot in public/api. Start Django with dev.ps1.')
      }
      return fetchJson(snapshotUrl(path, params), signal)
    })
    .catch((err) => {
      cache.delete(key) // never memoise a failure
      throw err
    })

  cache.set(key, promise)
  return promise
}

function csrfToken() {
  return document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ?? ''
}

export async function post(path, body, { files } = {}) {
  if (STATIC) {
    const err = new Error(
      'This preview of the site cannot send enquiries yet. Please call +91 75690 08004 or email info@zionlifts.com and we will pick it up from there.',
    )
    err.static = true
    err.status = 0
    err.fields = {}
    throw err
  }
  const target = url(path)
  let init

  if (files?.length) {
    const form = new FormData()
    for (const [k, v] of Object.entries(body ?? {})) {
      if (v === undefined || v === null || v === '') continue
      form.append(k, typeof v === 'object' ? JSON.stringify(v) : v)
    }
    for (const file of files) form.append('uploads', file)
    init = { method: 'POST', body: form }
  } else {
    init = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    }
  }

  const token = csrfToken()
  if (token) init.headers = { ...init.headers, 'X-CSRFToken': token }

  const res = await fetch(target, init)
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error('Request failed')
    err.status = res.status
    err.fields = payload // DRF returns { field: [messages] }
    throw err
  }
  return payload
}

/** Warm the collections the first paint depends on, in parallel. */
export function prefetchCore() {
  return Promise.allSettled([get('site/'), get('lifts/'), get('projects/')])
}
