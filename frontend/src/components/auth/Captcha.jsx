import { useCallback, useEffect, useState } from 'react'

import { Refresh } from '@/components/icons'
import { fetchCaptcha } from '@/api/auth'

/**
 * The CAPTCHA challenge and its input.
 *
 * The component holds only the public half — an opaque id and a PNG data URI.
 * The answer is checked on the server against a digest it never sends here, so
 * there is nothing on this page for a script to read.
 *
 * `onChallenge` hands the current id up to the form, which sends it with the
 * password. `refreshToken` lets the parent force a new challenge after a failed
 * attempt, because a spent challenge cannot be used twice.
 */
export default function Captcha({
  value,
  onChange,
  onChallenge,
  refreshToken = 0,
  error,
  disabled,
}) {
  const [challenge, setChallenge] = useState(null)
  const [state, setState] = useState('loading') // loading | ready | failed

  const load = useCallback(
    async (signal) => {
      setState('loading')
      try {
        const next = await fetchCaptcha({ signal })
        if (signal?.aborted) return
        setChallenge(next)
        setState('ready')
        onChallenge?.(next.captcha_id)
      } catch {
        if (signal?.aborted) return
        setState('failed')
        onChallenge?.(null)
      }
    },
    [onChallenge],
  )

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load, refreshToken])

  const errorId = error ? 'captcha-error' : undefined

  return (
    <div className={`field auth-captcha${error ? ' field--error' : ''}`}>
      <label className="field__label" htmlFor="captcha_answer">
        Security check
      </label>

      <div className="auth-captcha__frame">
        <div className="auth-captcha__image" aria-live="polite">
          {state === 'ready' && (
            <img
              src={challenge.image}
              alt="Five letters and digits, distorted. Type them into the field below."
              width="240"
              height="78"
            />
          )}
          {state === 'loading' && (
            <span className="auth-captcha__placeholder">Loading challenge…</span>
          )}
          {state === 'failed' && (
            <span className="auth-captcha__placeholder">
              Could not load. Use refresh.
            </span>
          )}
        </div>

        <button
          type="button"
          className="auth-captcha__refresh"
          onClick={() => load()}
          disabled={disabled || state === 'loading'}
          // The visible label reads "New image", which says nothing on its own
          // once the surrounding layout is gone.
          aria-label="Show a different security check image"
        >
          <Refresh size={16} aria-hidden="true" />
          <span>New image</span>
        </button>
      </div>

      <input
        id="captcha_answer"
        name="captcha_answer"
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Enter the characters shown above"
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck="false"
        inputMode="text"
        maxLength={12}
        disabled={disabled}
        required
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={errorId}
      />

      {error && (
        <p className="field__error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  )
}
