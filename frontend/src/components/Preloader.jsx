import { useEffect, useRef, useState } from 'react'

import { useReducedMotion } from '@/lib/hooks'

import './Preloader.css'

/**
 * Section 00 — a floor indicator ticking up rather than a spinner. Shown once
 * per session so returning to the home page is instant.
 */
const SEEN_KEY = 'zion:intro-seen'

export function hasSeenIntro() {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

export default function Preloader({ onDone }) {
  const reduced = useReducedMotion()
  const [floor, setFloor] = useState(1)
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
      setTimeout(() => onDone?.(), reduced ? 0 : 900)
    }

    if (reduced) {
      setFloor(24)
      finish()
      return
    }

    // accelerate: the gaps between floors shorten as it climbs
    let n = 1
    let timer
    const step = () => {
      n += 1
      setFloor(n)
      if (n >= 24) {
        timer = setTimeout(finish, 380)
        return
      }
      timer = setTimeout(step, Math.max(28, 132 - n * 4.6))
    }
    timer = setTimeout(step, 260)
    return () => clearTimeout(timer)
  }, [onDone, reduced])

  return (
    <div className={`preloader ${leaving ? 'is-leaving' : ''}`} role="status" aria-live="polite">
      <div className="preloader__line" aria-hidden="true" />

      <div className="preloader__lockup">
        <span className="preloader__word">Zion Lifts</span>
        <span className="preloader__sub">Vertical transportation</span>
        <span className="preloader__sub">Hyderabad, India</span>
      </div>

      <div className="preloader__floor" aria-label={`Loading, floor ${floor}`}>
        <span className="preloader__num">{String(floor).padStart(2, '0')}</span>
        <span className="preloader__arrow" aria-hidden="true">
          &uarr;
        </span>
      </div>
    </div>
  )
}
