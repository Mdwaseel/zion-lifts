/**
 * Sending a file from the operator's computer to the control room.
 *
 * XHR rather than `fetch`, and only here, for the same reason the knowledge
 * base's uploader uses it: `fetch` cannot report upload progress at all, so a
 * fetch-based uploader either shows nothing or invents a timer-driven bar that
 * is unrelated to what is happening. A 40 MB project film on a site office's
 * connection is exactly when somebody needs to know whether it is moving.
 *
 * Returns `{ promise, abort }` so a component can cancel a large upload the
 * moment the operator changes their mind, rather than leaving it running
 * against a form they have already left.
 */

import { ApiError, apiBase, csrfToken } from '@/api/client'

const ENDPOINT = 'admin/uploads'

/**
 * @returns {{promise: Promise<{url, name, size, kind}>, abort: () => void}}
 */
export function uploadMedia({ file, folder = 'content', onProgress }) {
  const form = new FormData()
  form.append('file', file)
  form.append('folder', folder)

  const request = new XMLHttpRequest()

  const promise = new Promise((resolve, reject) => {
    request.open('POST', `${apiBase}/${ENDPOINT}/`)
    // The auth cookies are HttpOnly, so the browser attaches them and nothing
    // here can read them. The CSRF token is the one value that must be echoed.
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

/** What the file picker offers, matching what the server will accept. */
export const ACCEPT = {
  image: 'image/jpeg,image/png,image/gif,image/webp,image/avif',
  video: 'video/mp4,video/webm,video/quicktime',
}

export const SIZE_LIMIT_MB = { image: 8, video: 64 }

function parse(text) {
  try {
    return JSON.parse(text)
  } catch {
    return {}
  }
}
