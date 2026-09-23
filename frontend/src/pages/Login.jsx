import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { fieldErrors, messageFor } from '@/api/auth'
import Captcha from '@/components/auth/Captcha'
import { Alert, Arrow, Eye, EyeOff, Lock } from '@/components/icons'
import { useAuth } from '@/lib/auth'

import './login.css'

/**
 * Where a signed-in staff user lands. The custom control room is a route in
 * this same app, so navigate() is enough — the full page load that Django's
 * server-rendered /admin/ needed is not.
 */
const CONTROL_URL = import.meta.env.VITE_CONTROL_URL ?? '/control'

const EMPTY = { email: '', password: '', captcha_answer: '' }

function isEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)
}

/**
 * The brand tile at the head of the card: the up/down pair between two guide
 * rails — the same thing every lift landing button says. A drawn car was the
 * first attempt and read as a padlock at 26px; the arrows do not.
 */
function LiftMark() {
  return (
    <svg
      className="login-mark"
      viewBox="0 0 32 32"
      width="26"
      height="26"
      role="presentation"
      aria-hidden="true"
    >
      <g className="login-mark__rails">
        <path d="M6 5V27M26 5V27" />
      </g>
      <g className="login-mark__travel">
        <path d="M11.5 14L16 8.5L20.5 14" />
        <path d="M11.5 18L16 23.5L20.5 18" />
      </g>
    </svg>
  )
}

/** Shown when someone signs in successfully but has no control-room clearance. */
function NoAccess({ user, onSignOut, busy }) {
  return (
    <div className="login-card__panel" role="status">
      <span className="login-card__mark login-card__mark--warn" aria-hidden="true">
        <Lock size={20} />
      </span>
      <h1 className="login-card__title">Not authorised</h1>
      <p className="login-card__lead">
        You are signed in as <strong>{user?.email}</strong>, but this account does not have
        access to the control room. Ask an administrator to grant staff access.
      </p>
      <button type="button" className="btn btn--solid login-card__wide" onClick={onSignOut} disabled={busy}>
        {busy ? 'Signing out…' : 'Sign out'}
      </button>
      <p className="login-card__foot">
        <Link className="link login-card__back" to="/">
          Return to zionlifts.com
        </Link>
      </p>
    </div>
  )
}

export default function Login() {
  const { user, isLoading, isAuthenticated, isStaff, signIn, signOut } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [captchaId, setCaptchaId] = useState(null)
  const [captchaNonce, setCaptchaNonce] = useState(0)
  const [status, setStatus] = useState('idle') // idle | submitting | leaving
  const [revealPassword, setRevealPassword] = useState(false)
  const [signingOut, setSigningOut] = useState(false)

  const errorRef = useRef(null)

  const busy = status !== 'idle'

  // Already cleared and coming back to /login: go straight through rather than
  // making someone sign in twice. A document navigation, so no redirect loop.
  useEffect(() => {
    if (!isLoading && isAuthenticated && isStaff) {
      setStatus('leaving')
      navigate(CONTROL_URL, { replace: true })
    }
  }, [isLoading, isAuthenticated, isStaff, navigate])

  // Move the reader to the message rather than leaving it announced but unfound.
  useEffect(() => {
    if (formError) errorRef.current?.focus()
  }, [formError])

  const set = (key) => (value) => {
    setForm((current) => ({ ...current, [key]: value }))
    setErrors((current) => (current[key] ? { ...current, [key]: undefined } : current))
  }

  const validate = useMemo(
    () => () => {
      const next = {}
      if (!form.email.trim()) next.email = 'Enter your email address.'
      else if (!isEmail(form.email.trim())) next.email = 'Enter a valid email address.'
      if (!form.password) next.password = 'Enter your password.'
      if (!form.captcha_answer.trim()) next.captcha_answer = 'Enter the characters shown.'
      else if (!captchaId) next.captcha_answer = 'Get a new image and try again.'
      return next
    },
    [form, captchaId],
  )

  async function onSubmit(event) {
    event.preventDefault()
    if (busy) return // a second Enter must not send a second request

    const found = validate()
    setErrors(found)
    if (Object.keys(found).length) return

    setStatus('submitting')
    setFormError(null)

    try {
      const account = await signIn({
        email: form.email,
        password: form.password,
        captchaId,
        captchaAnswer: form.captcha_answer,
      })

      if (account.is_staff) {
        setStatus('leaving')
        navigate(CONTROL_URL, { replace: true })
        return
      }
      setStatus('idle') // the NoAccess panel takes over from here
    } catch (error) {
      setFormError(messageFor(error))
      setErrors(fieldErrors(error))
      // The challenge is spent whether it was right or wrong, so always ask
      // for a new one and clear what was typed into it.
      setForm((current) => ({ ...current, captcha_answer: '' }))
      setCaptchaNonce((n) => n + 1)
      setStatus('idle')
    }
  }

  async function onSignOut() {
    setSigningOut(true)
    await signOut()
    setSigningOut(false)
    setForm(EMPTY)
    setCaptchaNonce((n) => n + 1)
  }

  const showNoAccess = !isLoading && isAuthenticated && !isStaff

  return (
    <main className="login" id="main">
      {/* One ground, three layers: the glow sets the light, the rails and the
          floor lines carry the hoistway. All decorative, all behind the card. */}
      <div className="login__field" aria-hidden="true">
        <div className="login__glow" />
        <div className="login__rails" />
        <div className="login__floors" />
      </div>

      <div className="login__stage">
        <div className="login-card">
          {isLoading || status === 'leaving' ? (
            <div className="login-card__panel login-card__panel--waiting" role="status">
              <span className="login-card__spinner" aria-hidden="true" />
              <p className="login-card__lead">
                {status === 'leaving' ? 'Opening the control room…' : 'Checking your session…'}
              </p>
            </div>
          ) : showNoAccess ? (
            <NoAccess user={user} onSignOut={onSignOut} busy={signingOut} />
          ) : (
            <div className="login-card__panel">
              <span className="login-card__mark" aria-hidden="true">
                <LiftMark />
              </span>
              <p className="login-card__eyebrow mono">Zion Lifts · Control room</p>
              <h1 className="login-card__title">Welcome back</h1>
              <p className="login-card__lead">Sign in to continue.</p>

              <form className="login-form" onSubmit={onSubmit} noValidate>
                {formError && (
                  <div
                    className="login-form__alert"
                    role="alert"
                    tabIndex={-1}
                    ref={errorRef}
                  >
                    <Alert size={16} aria-hidden="true" />
                    <span>{formError}</span>
                  </div>
                )}

                <div className={`field${errors.email ? ' field--error' : ''}`}>
                  <label className="field__label" htmlFor="email">
                    Email address
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    value={form.email}
                    onChange={(e) => set('email')(e.target.value)}
                    autoComplete="username"
                    autoFocus
                    required
                    disabled={busy}
                    placeholder="you@zionlifts.com"
                    aria-invalid={errors.email ? 'true' : undefined}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                  />
                  {errors.email && (
                    <p className="field__error" id="email-error">
                      {errors.email}
                    </p>
                  )}
                </div>

                <div className={`field${errors.password ? ' field--error' : ''}`}>
                  <label className="field__label" htmlFor="password">
                    Password
                  </label>
                  <div className="login-form__password">
                    <input
                      id="password"
                      name="password"
                      type={revealPassword ? 'text' : 'password'}
                      value={form.password}
                      onChange={(e) => set('password')(e.target.value)}
                      autoComplete="current-password"
                      required
                      disabled={busy}
                      aria-invalid={errors.password ? 'true' : undefined}
                      aria-describedby={errors.password ? 'password-error' : undefined}
                    />
                    <button
                      type="button"
                      className="login-form__reveal"
                      onClick={() => setRevealPassword((v) => !v)}
                      aria-pressed={revealPassword}
                      aria-label={revealPassword ? 'Hide password' : 'Show password'}
                      disabled={busy}
                    >
                      {revealPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="field__error" id="password-error">
                      {errors.password}
                    </p>
                  )}
                </div>

                <Captcha
                  value={form.captcha_answer}
                  onChange={set('captcha_answer')}
                  onChallenge={setCaptchaId}
                  refreshToken={captchaNonce}
                  error={errors.captcha_answer}
                  disabled={busy}
                />

                <button
                  type="submit"
                  className="btn btn--accent login-card__wide"
                  disabled={busy}
                >
                  {status === 'submitting' ? (
                    <>
                      <span className="login-card__spinner login-card__spinner--sm" aria-hidden="true" />
                      Signing in…
                    </>
                  ) : (
                    <>
                      Sign in
                      <Arrow size={16} className="btn__arrow" />
                    </>
                  )}
                </button>
              </form>

              <p className="login-card__foot">
                Trouble signing in? Contact your system administrator.
                <Link className="link login-card__back" to="/">
                  Return to zionlifts.com
                </Link>
              </p>
            </div>
          )}
        </div>

        <p className="login__meta mono">Hyderabad · Est. 2012 · Authorised personnel only</p>
      </div>
    </main>
  )
}
