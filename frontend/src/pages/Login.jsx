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

/** The drafted elevation on the left. Decorative, so it is hidden from readers. */
function Hoistway() {
  return (
    <svg
      className="login-art"
      viewBox="0 0 260 520"
      role="presentation"
      aria-hidden="true"
      preserveAspectRatio="xMidYMid meet"
    >
      <g className="login-art__rails">
        <path d="M70 20V500M190 20V500" />
        <path d="M52 20V500M208 20V500" strokeDasharray="2 8" />
      </g>

      <g className="login-art__levels">
        {[60, 148, 236, 324, 412].map((y, i) => (
          <g key={y}>
            <path d={`M52 ${y}H208`} />
            <text x="18" y={y + 4}>{`0${5 - i}`}</text>
          </g>
        ))}
        <path d="M52 490H208" />
        <text x="18" y="494">
          GF
        </text>
      </g>

      <g className="login-art__car">
        <rect x="84" y="270" width="92" height="128" rx="2" />
        <path d="M130 270v128" strokeDasharray="3 7" />
        <path d="M96 292h20M144 292h20" />
      </g>

      <g className="login-art__dims">
        <path d="M232 270v128M228 270h8M228 398h8" />
        <text x="238" y="338" transform="rotate(-90 238 338)">
          1600 KG
        </text>
      </g>
    </svg>
  )
}

/** Shown when someone signs in successfully but has no control-room clearance. */
function NoAccess({ user, onSignOut, busy }) {
  return (
    <div className="login-card__panel" role="status">
      <span className="login-card__mark" aria-hidden="true">
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
      <section className="login__visual" aria-hidden="true">
        <div className="login__grid" />
        <div className="login__visual-inner">
          <p className="login__eyebrow mono">Control room</p>
          <p className="login__wordmark">
            {/* The break is dropped below the split, so the space has to be
                explicit or the two words run together on a phone. */}
            Zion{' '}
            <br />
            Lifts
          </p>
          <p className="login__lead">Precision in vertical movement.</p>
          <Hoistway />
          <p className="login__meta mono">
            Hyderabad · Est. 2012 · Authorised personnel only
          </p>
        </div>
      </section>

      <section className="login__form-side on-paper">
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
              <p className="login-card__eyebrow mono">Zion Lifts</p>
              <h1 className="login-card__title">Welcome back</h1>
              <p className="login-card__lead">Sign in to the control room.</p>

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
      </section>
    </main>
  )
}
