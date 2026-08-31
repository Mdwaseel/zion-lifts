import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from 'react'

import { useReducedMotion } from '@/lib/hooks'
import { gsap } from '@/lib/gsap'

/* ==========================================================================
   The trajectory field under the contexts section.

   Read it as an architectural drawing of movement, not as water: a set of
   thin, layered lines that leave the lower left, lift through the middle of
   the frame, cross one another and settle toward the lower right.

   Every path is generated from the same model —

       y = base + amp · sin(2π·freq·t + phase) − lift · sin(π·t)

   — where the last term is what raises the middle of the run and makes the
   lines cross rather than travel in parallel. Sampled points are converted to
   a smooth cubic Bézier chain (Catmull-Rom), so the geometry is built once.

   Nothing regenerates per frame. Flow is a horizontal translate; the response
   to scroll is a vertical scale about each line's own baseline. Both are
   written straight onto the group's transform attribute, so no React state
   changes while the animation runs.
   ========================================================================== */

const VB_W = 1600
const VB_H = 320

// Drawn well past both edges so a translating line never reveals its ends.
const X_FROM = -900
const X_TO = 2500
const SAMPLES = 64

/**
 * base/amp/lift are fractions of the viewBox height, freq is whole cycles
 * across the viewBox width (whole so the horizontal loop is seamless), speed
 * is user units per second.
 */
const PATHS = [
  { base: 0.72, amp: 0.085, lift: 0.2, freq: 2, phase: 0.0, w: 1.4, o: 0.6, dash: null, speed: 16 },
  { base: 0.78, amp: 0.1, lift: 0.26, freq: 2, phase: 1.1, w: 1, o: 0.42, dash: '1 7', speed: 22 },
  { base: 0.66, amp: 0.07, lift: 0.15, freq: 3, phase: 2.4, w: 1, o: 0.3, dash: '2 9', speed: 12 },
  { base: 0.84, amp: 0.11, lift: 0.3, freq: 2, phase: 3.4, w: 1.6, o: 0.75, dash: null, speed: 26 },
  { base: 0.6, amp: 0.055, lift: 0.12, freq: 4, phase: 0.7, w: 1, o: 0.22, dash: '1 11', speed: 9 },
  { base: 0.9, amp: 0.075, lift: 0.22, freq: 3, phase: 4.6, w: 1, o: 0.34, dash: '3 6', speed: 30 },
  { base: 0.75, amp: 0.13, lift: 0.34, freq: 2, phase: 5.5, w: 1, o: 0.18, dash: null, speed: 19 },
]

/** Catmull-Rom through the sampled points, emitted as cubic Béziers. */
function toBezier(pts) {
  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] ?? p2
    const c1x = p1[0] + (p2[0] - p0[0]) / 6
    const c1y = p1[1] + (p2[1] - p0[1]) / 6
    const c2x = p2[0] - (p3[0] - p1[0]) / 6
    const c2y = p2[1] - (p3[1] - p1[1]) / 6
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`
  }
  return d
}

function buildPath({ base, amp, lift, freq, phase }) {
  const baseY = base * VB_H
  const ampY = amp * VB_H
  const liftY = lift * VB_H
  const pts = []
  for (let i = 0; i <= SAMPLES; i++) {
    const x = X_FROM + ((X_TO - X_FROM) * i) / SAMPLES
    const t = x / VB_W
    const y = baseY + ampY * Math.sin(2 * Math.PI * freq * t + phase) - liftY * Math.sin(Math.PI * t)
    pts.push([x, y])
  }
  return { d: toBezier(pts), baseY }
}

/**
 * Imperative handle: `setProgress(p, amplitude)` where p is 0-1 through the
 * pinned section and amplitude scales the field for the active context.
 */
const ContextWave = forwardRef(function ContextWave(_props, ref) {
  const groupsRef = useRef([])
  const stateRef = useRef({ progress: 0, amp: 1, ampCurrent: 1 })
  const reduced = useReducedMotion()

  const paths = useMemo(() => PATHS.map((p) => ({ ...p, ...buildPath(p) })), [])

  useImperativeHandle(ref, () => ({
    setProgress(progress, amp) {
      stateRef.current.progress = progress
      stateRef.current.amp = amp
    },
  }))

  useEffect(() => {
    const groups = groupsRef.current.filter(Boolean)
    if (!groups.length) return

    // Static, centred state — no drift, no dash travel.
    if (reduced) {
      groups.forEach((g, i) => {
        g.setAttribute('transform', `translate(0 0) translate(0 ${paths[i].baseY}) scale(1 1) translate(0 ${-paths[i].baseY})`)
      })
      return
    }

    const start = performance.now()
    const tick = () => {
      const elapsed = (performance.now() - start) / 1000
      const s = stateRef.current
      // ease the amplitude toward its target so a context change reads as a
      // settle rather than a jump
      s.ampCurrent += (s.amp - s.ampCurrent) * 0.06

      for (let i = 0; i < groups.length; i++) {
        const p = paths[i]
        const wavelength = VB_W / p.freq
        // travel one whole wavelength then wrap: the geometry repeats, so the
        // reset is invisible
        const tx = -(((elapsed * p.speed) % wavelength) + s.progress * wavelength * 0.35)
        const sy = s.ampCurrent
        groups[i].setAttribute(
          'transform',
          `translate(${tx.toFixed(1)} 0) translate(0 ${p.baseY.toFixed(1)}) scale(1 ${sy.toFixed(3)}) translate(0 ${(-p.baseY).toFixed(1)})`,
        )
      }
    }

    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [paths, reduced])

  return (
    <svg
      className="world__wave"
      viewBox={`0 0 ${VB_W} ${VB_H}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      {paths.map((p, i) => (
        <g key={i} ref={(el) => (groupsRef.current[i] = el)}>
          <path
            d={p.d}
            fill="none"
            stroke="currentColor"
            strokeWidth={p.w}
            strokeLinecap="round"
            strokeDasharray={p.dash ?? undefined}
            opacity={p.o}
            vectorEffect="non-scaling-stroke"
          />
        </g>
      ))}
    </svg>
  )
})

export default ContextWave
