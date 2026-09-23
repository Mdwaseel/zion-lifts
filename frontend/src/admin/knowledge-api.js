/**
 * The knowledge base's calls.
 *
 * Kept apart from `api.js` because those endpoints are derived from a resource
 * key — one list screen and one form screen serving thirty collections — and
 * these are not. Uploading a document, retrying an ingestion and reindexing a
 * version are *operations*, not row writes, and they have names rather than
 * verbs on a table.
 *
 * Every one of them is enforced server-side. What the panel does with the
 * results is presentation; what a person is allowed to do is Django's answer.
 */

import { ApiError, apiBase, api, csrfToken } from '@/api/client'

const BASE = 'admin/knowledge'

const path = (...parts) => [BASE, ...parts.filter(Boolean)].join('/')

// --- knowledge bases -------------------------------------------------------

export function fetchKnowledgeBases(options) {
  return api.get(`${path('bases')}/`, options)
}

export function fetchKnowledgeBase(id, options) {
  return api.get(`${path('bases', id)}/`, options)
}

export function createKnowledgeBase(body) {
  return api.post(`${path('bases')}/`, body)
}

export function updateKnowledgeBase(id, body) {
  return api.patch(`${path('bases', id)}/`, body)
}

// --- documents -------------------------------------------------------------

export function fetchDocuments(params = {}, options) {
  return api.get(`${path('documents')}/${query(params)}`, options)
}

export function fetchDocument(id, options) {
  return api.get(`${path('documents', id)}/`, options)
}

/** Just enough to poll while something is processing. */
export function fetchDocumentStatus(id, options) {
  return api.get(`${path('documents', id, 'status')}/`, options)
}

export function fetchVersions(id, options) {
  return api.get(`${path('documents', id, 'versions')}/`, options)
}

export function fetchJobs(id, options) {
  return api.get(`${path('documents', id, 'jobs')}/`, options)
}

export function renameDocument(id, body) {
  return api.patch(`${path('documents', id)}/`, body)
}

// --- operations ------------------------------------------------------------
// Each of these queues work rather than changing a row. The panel never talks
// to Redis or Celery: it asks Django, and Django decides whether to enqueue.

export function reindexDocument(id) {
  return api.post(`${path('documents', id, 'reindex')}/`, {})
}

export function retryDocument(id) {
  return api.post(`${path('documents', id, 'retry')}/`, {})
}

export function deleteDocument(id) {
  return api.post(`${path('documents', id, 'delete')}/`, {})
}

// --- upload ----------------------------------------------------------------

/**
 * Upload a PDF, reporting progress as the bytes go up.
 *
 * XHR rather than fetch, and only here: fetch cannot report upload progress at
 * all, so a fetch-based uploader has to either show nothing or invent a
 * timer-driven bar that is unrelated to what is actually happening. A 20 MB
 * scan on a slow connection is exactly when someone needs to know whether it is
 * moving.
 *
 * @returns {{promise: Promise<object>, abort: () => void}}
 */
export function uploadDocument({ knowledgeBase, file, name, onProgress }) {
  const form = new FormData()
  form.append('knowledge_base', knowledgeBase)
  form.append('file', file)
  if (name) form.append('name', name)

  const request = new XMLHttpRequest()
  const url = `${apiBase}/${path('documents', 'upload')}/`

  const promise = new Promise((resolve, reject) => {
    request.open('POST', url)
    // The cookies are HttpOnly, so the browser attaches them and nothing here
    // can read them. The CSRF token is the one value that must be echoed back.
    request.withCredentials = true
    const token = csrfToken()
    if (token) request.setRequestHeader('X-CSRFToken', token)
    request.setRequestHeader('Accept', 'application/json')

    request.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) return
      onProgress?.(Math.round((event.loaded / event.total) * 100))
    })

    request.addEventListener('load', () => {
      const payload = parse(request.responseText)
      if (request.status >= 200 && request.status < 300) {
        // The bytes have arrived; everything after this is the worker's.
        onProgress?.(100)
        resolve(payload)
      } else {
        reject(new ApiError(request.status, payload))
      }
    })

    request.addEventListener('error', () =>
      reject(new ApiError(0, { detail: 'Network error', code: 'network' })),
    )
    request.addEventListener('abort', () => {
      const error = new Error('Upload cancelled')
      error.name = 'AbortError'
      reject(error)
    })

    request.send(form)
  })

  return { promise, abort: () => request.abort() }
}

function parse(text) {
  try {
    return JSON.parse(text)
  } catch {
    return {}
  }
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
