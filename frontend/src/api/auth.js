/**
 * The five authentication calls, and the one place error text is decided.
 *
 * Nothing here returns or stores a token: the server writes them to HttpOnly
 * cookies and the browser sends them back. There is no `localStorage`, no
 * `sessionStorage`, and no token in React state anywhere in this app.
 */

import { ApiError, api } from './client'

/** GET a challenge. Also seeds Django's CSRF cookie, so call it before login. */
export function fetchCaptcha({ signal } = {}) {
  return api.get('accounts/captcha/', { signal })
}

export function login({ email, password, captchaId, captchaAnswer }) {
  return api.post('accounts/login/', {
    email: email.trim(),
    password,
    captcha_id: captchaId,
    captcha_answer: captchaAnswer.trim(),
  })
}

export function logout() {
  return api.post('accounts/logout/')
}

export function currentUser({ signal } = {}) {
  return api.get('accounts/me/', { signal })
}

/**
 * Turn a failure into something worth reading.
 *
 * The server is deliberately vague about credentials — it will not say whether
 * an address exists — and this keeps that contract rather than guessing at a
 * more specific message.
 */
export function messageFor(error) {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.'

  switch (error.status) {
    case 0:
      return 'Could not reach the server. Check your connection and try again.'
    case 400:
      if (error.code === 'captcha_invalid') return 'Invalid or expired CAPTCHA.'
      return firstFieldError(error) ?? 'Please check the form and try again.'
    case 401:
      return 'Invalid email or password.'
    case 403:
      // A stale CSRF token, almost always. A fresh CAPTCHA fetches a new one.
      return 'Your session expired. Please try again.'
    case 429:
      return 'Too many attempts. Please wait a minute and try again.'
    default:
      return 'Something went wrong. Please try again.'
  }
}

function firstFieldError(error) {
  const [message] = Object.values(error.fields).flat()
  return typeof message === 'string' ? message : null
}

/** Which field a 400 belongs to, so the form can mark it. */
export function fieldErrors(error) {
  if (!(error instanceof ApiError)) return {}
  if (error.code === 'captcha_invalid') return { captcha_answer: 'Invalid or expired CAPTCHA.' }
  if (error.status !== 400) return {}

  return Object.fromEntries(
    Object.entries(error.fields).map(([key, value]) => [key, [].concat(value)[0]]),
  )
}
