/**
 * The control room's calls, over the shared authenticated client.
 *
 * Every path is derived from a resource key rather than written out, because
 * the panel has one list screen and one form screen serving all thirty
 * collections — there is nothing here that knows what a "lift" is.
 */

import { ApiError, api } from '@/api/client'

const BASE = 'admin'

const path = (...parts) => [BASE, ...parts.filter(Boolean)].join('/')

// --- the panel itself ------------------------------------------------------
export function fetchNavigation(options) {
  return api.get(`${path('navigation')}/`, options)
}

export function fetchDashboard(options) {
  return api.get(`${path('dashboard')}/`, options)
}

export function fetchActivity(options) {
  return api.get(`${path('activity')}/`, options)
}

// --- one collection --------------------------------------------------------
/** The field description the table and form render themselves from. */
export function fetchSchema(resource, options) {
  return api.get(`${path(resource, 'schema')}/`, options)
}

export function fetchList(resource, params = {}, options) {
  return api.get(`${path(resource)}/${query(params)}`, options)
}

export function fetchRecord(resource, id, options) {
  return api.get(`${path(resource, id)}/`, options)
}

export function createRecord(resource, body) {
  return api.post(`${path(resource)}/`, body)
}

export function updateRecord(resource, id, body) {
  return api.patch(`${path(resource, id)}/`, body)
}

export function deleteRecord(resource, id) {
  return api.remove(`${path(resource, id)}/`)
}

export function bulkAction(resource, action, ids) {
  return api.post(`${path(resource, 'bulk')}/`, { action, ids })
}

/** Choices for a relation field, optionally searched. */
export function fetchOptions(resource, field, q = '', options) {
  return api.get(`${path(resource, 'options')}/${query({ field, q })}`, options)
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

/**
 * Turn a failure into something a person can act on.
 *
 * Field-level errors are handled by the form, which shows them next to the
 * input they belong to; this is the message for everything else.
 */
export function messageFor(error, fallback = 'Something went wrong. Please try again.') {
  if (!(error instanceof ApiError)) return fallback

  switch (error.status) {
    case 0:
      return 'Could not reach the server. Check your connection.'
    case 400:
      return error.payload?.detail ?? 'Please check the highlighted fields.'
    case 401:
      return 'Your session expired. Please sign in again.'
    case 403:
      return error.payload?.detail ?? 'You do not have permission to do that.'
    case 404:
      return 'That record no longer exists.'
    case 409:
      // The server refused because of the record's state, not the request's
      // shape — a document already processing, or bytes already stored. Its
      // own message says which, and it is more useful than anything generic.
      return error.payload?.detail ?? 'That is not possible in the current state.'
    case 422:
      return error.payload?.detail ?? 'The server could not process that request.'
    case 429:
      return 'Too many requests. Please wait a moment.'
    case 503:
      return 'That service is temporarily unavailable. Please try again shortly.'
    default:
      return fallback
  }
}

export { ApiError }
