import { useEffect, useRef } from 'react'

import { useReducedMotion } from '@/lib/hooks'

/* ==========================================================================
   The faint schematic behind the engineering headline.

   A shaft section drawn the way a general-arrangement drawing would show it:
   a centre line with a lift travelling it, the levelling circles it is measured
   against, datum ticks down each side, and a few coordinate points. It is
   deliberately near-invisible — it exists to make the negative space beside
   the headline read as intentional, not to be looked at.

   Everything loops in CSS. The only script here is a pointer offset written to
   two custom properties, rAF-throttled, and skipped entirely when motion is
   reduced.
   ========================================================================== */

export default function EngSchematic() {
  const ref = useRef(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    const el = ref.current
    if (!el || reduced) return
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return

    let raf = 0
    let x = 0
    let y = 0
    const onMove = (e) => {
      x = (e.clientX / window.innerWidth - 0.5) * 2
      y = (e.clientY / window.innerHeight - 0.5) * 2
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        el.style.setProperty('--px', (x * 5).toFixed(2) + 'px')
        el.style.setProperty('--py', (y * 3).toFixed(2) + 'px')
      })
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => {
      window.removeEventListener('pointermove', onMove)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [reduced])

  return (
    <div className="eng__schematic" ref={ref} aria-hidden="true">
      <svg viewBox="0 0 420 320" preserveAspectRatio="xMidYMid meet" focusable="false">
        {/* levelling circles the lift is measured against */}
        <g className="eng__rings">
          <circle cx="210" cy="150" r="52" />
          <circle cx="210" cy="150" r="88" />
          <circle cx="210" cy="150" r="124" />
        </g>

        {/* shaft centre line, and the guide rails either side of it */}
        <g className="eng__shaft">
          <line x1="210" y1="6" x2="210" y2="314" />
          <line className="eng__rail" x1="178" y1="24" x2="178" y2="296" />
          <line className="eng__rail" x1="242" y1="24" x2="242" y2="296" />
        </g>

        {/* the lift, travelling */}
        <g className="eng__car">
          <rect x="196" y="120" width="28" height="60" rx="1" />
          <line x1="196" y1="150" x2="224" y2="150" />
        </g>

        {/* datum ticks down each side */}
        <g className="eng__ticks">
          {Array.from({ length: 9 }, (_, i) => (
            <g key={i}>
              <line x1="150" y1={40 + i * 30} x2="162" y2={40 + i * 30} />
              <line x1="258" y1={40 + i * 30} x2="270" y2={40 + i * 30} />
            </g>
          ))}
        </g>

        {/* coordinate points */}
        <g className="eng__nodes">
          {[
            [122, 92],
            [298, 118],
            [104, 206],
            [316, 214],
            [140, 262],
            [286, 66],
          ].map(([cx, cy], i) => (
            <circle key={i} cx={cx} cy={cy} r="1.8" style={{ animationDelay: `${i * 1.3}s` }} />
          ))}
        </g>
      </svg>
    </div>
  )
}
