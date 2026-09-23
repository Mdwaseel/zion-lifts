import { useEffect, useRef, useState } from 'react'

import { useReducedMotion } from '@/lib/hooks'

import './Preloader.css'

/**
 * Section 00 — the lockup holds on a black ground while the page loads, then
 * launches: the mark is a triangle, so it leaves the way a rocket does, up and
 * out of frame, accelerating, with the ground falling away behind it.
 *
 * Shown once per session, so coming back to the home page is instant.
 */
const SEEN_KEY = 'zion:intro-seen'

/** how long the hold lasts before the launch, in ms */
const HOLD = 1500

/** the launch itself — must match the transition on .preloader__lockup */
const LAUNCH = 1150

export function hasSeenIntro() {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

/**
 * `?intro` on the URL runs the intro again even though this session has already
 * seen it. The intro is deliberately once a session, which makes it invisible
 * while you are reloading the same tab working on it — and makes it impossible
 * to show someone on demand without opening a fresh window.
 */
export function introForced() {
  try {
    return new URLSearchParams(window.location.search).has('intro')
  } catch {
    return false
  }
}

export default function Preloader({ onDone }) {
  const reduced = useReducedMotion()
  const [leaving, setLeaving] = useState(false)
  const done = useRef(false)

  useEffect(() => {
    const finish = () => {
      if (done.current) return
      done.current = true
      try {
        sessionStorage.setItem(SEEN_KEY, '1')
      } catch {
        /* private mode — show the intro again next time, which is fine */
      }
      setLeaving(true)
      setTimeout(() => onDone?.(), reduced ? 0 : LAUNCH)
    }

    if (reduced) {
      finish()
      return undefined
    }

    const timer = setTimeout(finish, HOLD)
    return () => clearTimeout(timer)
  }, [onDone, reduced])

  return (
    <div className={`preloader ${leaving ? 'is-leaving' : ''}`} role="status" aria-live="polite">
      {/* two elements, not one: the inner one arrives, the outer one launches.
          Sharing a single element means the launch transform replaces a running
          animation in the same frame, and the browser skips the transition. */}
      <div className="preloader__lockup">
        <div className="preloader__rise">
          {/* the trail belongs to the mark, not to the frame: the lockup is a
              row, so the mark does not sit at the centre of the screen */}
          <span className="preloader__ship">
            <img
              className="preloader__mark"
              src="/media/brand/mark.webp"
              alt=""
              width="120"
              height="128"
              aria-hidden="true"
            />
            <span className="preloader__trail" aria-hidden="true" />
          </span>
          <span className="preloader__word">
            Zion <em>Lifts</em>
          </span>
        </div>
      </div>

      <span className="sr-only">Loading</span>
    </div>
  )
}
