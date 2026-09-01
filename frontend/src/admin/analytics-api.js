/**
 * The analytics reports, over the panel's existing authenticated client.
 *
 * One function per endpoint rather than a generic `fetchReport(name)`: each of
 * these takes different parameters, and a single call taking a bag of options
 * would push the question of which ones apply into every call site.
 *
 * Every request carries the current range, so a component asking for a panel
 * cannot accidentally render one window's chart above another window's table.
 */

import { api, apiBase } from '@/api/client'

const BASE = 'admin/analytics'

/** Range state -> query parameters. Custom ranges carry their two dates. */
export function rangeParams(range) {
  if (!range) return {}
  if (range.key === 'custom') {
    return { range: 'custom', start: range.start, end: range.end }
  }
  return { range: range.key }
}

export function fetchOverview(range, options) {
  return api.get(`${BASE}/overview/${query(rangeParams(range))}`, options)
}

export function fetchVisitors(range, options) {
  return api.get(`${BASE}/visitors/${query(rangeParams(range))}`, options)
}

export function fetchPages(range, { page = 1, pageSize = 10 } = {}, options) {
  return api.get(
    `${BASE}/pages/${query({ ...rangeParams(range), page, page_size: pageSize })}`,
    options,
  )
}

export function fetchPageDetail(range, path, options) {
  return api.get(`${BASE}/pages/${query({ ...rangeParams(range), path })}`, options)
}

export function fetchSources(range, options) {
  return api.get(`${BASE}/sources/${query(rangeParams(range))}`, options)
}

export function fetchDevices(range, options) {
  return api.get(`${BASE}/devices/${query(rangeParams(range))}`, options)
}

export function fetchGeography(range, level = 'country', options) {
  return api.get(`${BASE}/geography/${query({ ...rangeParams(range), level })}`, options)
}

/** Live visitors and the activity feed. Range-independent — "now" is not a window. */
export function fetchRealtime({ page = 1, pageSize = 12 } = {}, options) {
  return api.get(`${BASE}/realtime/${query({ page, page_size: pageSize })}`, options)
}

/**
 * The export URL.
 *
 * A plain link rather than a fetch: the response is a file download, and letting
 * the browser navigate to it gets the Content-Disposition handling, the progress
 * indicator and the cancel button for free. The cookies travel with it because
 * it is a same-origin request, so the staff gate still applies.
 */
export function exportUrl(range) {
  return `${apiBase}/${BASE}/export/${query(rangeParams(range))}`
}

function query(params) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.set(key, value)
  }
  const string = search.toString()
  return string ? `?${string}` : ''
}
