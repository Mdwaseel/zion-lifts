/**
 * Thin client over the Django REST API.
 *
 * Every GET is memoised for the life of the page: the site is content-heavy and
 * largely static, and several sections request the same collection (lift types
 * appear on Home, /lifts, every product page and the contact form).
 */

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

const cache = new Map()

function url(path, params) {
  const clean = `${BASE}/${String(path).replace(/^\/+/, '')}`
  if (!params) return clean
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  ).toString()
  return qs ? `${clean}?${qs}` : clean
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

  const promise = fetch(key, { signal, headers: { Accept: 'application/json' } })
    .then(async (res) => {
      if (!res.ok) {
        const err = new Error(`${res.status} ${res.statusText} — ${key}`)
        err.status = res.status
        throw err
      }
      return unwrap(await res.json())
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
  return Promise.allSettled([
    get('site/'),
    get('lifts/'),
    get('projects/'),
    get('service-pillars/'),
  ])
}
