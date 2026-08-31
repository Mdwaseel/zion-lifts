import { useCallback, useEffect, useRef, useState } from 'react'

import { get } from './api'

/** Fetches a collection or record, with loading/error state. */
export function useApi(path, params, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false, error: null })
      return
    }
    let live = true
    setState((s) => ({ ...s, loading: true, error: null }))
    get(path, params)
      .then((data) => live && setState({ data, loading: false, error: null }))
      .catch((error) => live && setState({ data: null, loading: false, error }))
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, JSON.stringify(params), ...deps])

  return state
}

/** True once the element has entered the viewport; stays true afterwards. */
export function useInView({ threshold = 0.2, rootMargin = '0px 0px -12% 0px' } = {}) {
  const ref = useRef(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || inView) return
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          io.disconnect()
        }
      },
      { threshold, rootMargin },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [inView, threshold, rootMargin])

  return [ref, inView]
}

export function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (e) => setReduced(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return reduced
}

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && window.matchMedia?.(query).matches,
  )
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = (e) => setMatches(e.matches)
    setMatches(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])
  return matches
}

/** Counts from 0 to `value` once visible. Respects reduced motion. */
export function useCountUp(value, { duration = 1600, start = 0 } = {}) {
  // low threshold and no bottom trim: a stat row parked at the edge of the
  // viewport should still count, rather than sitting on its start value
  const [ref, inView] = useInView({ threshold: 0.25, rootMargin: '0px' })
  const reduced = useReducedMotion()
  const [n, setN] = useState(start)

  useEffect(() => {
    if (!inView) return
    if (reduced) {
      setN(value)
      return
    }
    let raf
    const t0 = performance.now()
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / duration)
      const eased = 1 - Math.pow(1 - p, 4)
      setN(Math.round(start + (value - start) * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, value, duration, start, reduced])

  return [ref, n]
}

/** Locks body scroll while `locked` is true (menu, lightbox). */
export function useScrollLock(locked) {
  useEffect(() => {
    if (!locked) return
    const { body } = document
    const y = window.scrollY
    body.classList.add('is-locked')
    body.style.top = `-${y}px`
    body.style.position = 'fixed'
    body.style.width = '100%'
    return () => {
      body.classList.remove('is-locked')
      body.style.top = ''
      body.style.position = ''
      body.style.width = ''
      window.scrollTo(0, y)
    }
  }, [locked])
}

/** Calls `handler` on Escape. */
export function useEscape(handler, active = true) {
  const saved = useRef(handler)
  saved.current = handler
  useEffect(() => {
    if (!active) return
    const onKey = (e) => e.key === 'Escape' && saved.current?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active])
}

/**
 * 0 → 1 progress of an element travelling through the viewport.
 *
 * `mode: 'pin'` measures a sticky section instead: 0 the moment its top meets
 * the viewport top, 1 when its last screenful has been scrolled through. That
 * is what a pinned stage needs — 'travel' would already be part-way through
 * before the section had even reached the top of the screen.
 */
export function useScrollProgress({ mode = 'pin' } = {}) {
  const ref = useRef(null)
  const [progress, setProgress] = useState(0)

  const measure = useCallback(() => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const vh = window.innerHeight
    let p
    if (mode === 'pin') {
      const runway = Math.max(1, rect.height - vh)
      p = -rect.top / runway
    } else {
      p = (vh - rect.top) / (rect.height + vh)
    }
    setProgress(Math.max(0, Math.min(1, p)))
  }, [mode])

  useEffect(() => {
    measure()
    window.addEventListener('scroll', measure, { passive: true })
    window.addEventListener('resize', measure)
    return () => {
      window.removeEventListener('scroll', measure)
      window.removeEventListener('resize', measure)
    }
  }, [measure])

  return [ref, progress]
}
