import { useEffect, useMemo, useRef, useState } from 'react'

import { gsap } from '@/lib/gsap'
import { useReducedMotion } from '@/lib/hooks'

import './shared.css'

/* The motion the lift pages share: one way of reading scroll into CSS, and one
   way of setting a headline. Used by a lift's own page and by the collection. */

export const clamp01 = (v) => Math.max(0, Math.min(1, v))

/** Writes how far an element has come up the screen into a CSS variable on it,
    eased a little behind the scroll. `from` and `to` are fractions of the
    viewport height the element's top travels between. The stylesheet does the
    rest — and because the variable is set on an element that is never itself
    transformed, the measurement cannot chase its own tail. */
export function useScrollVar(ref, { from = 1, to = 0.3, name = '--p', ease = 0.14 } = {}) {
  const reduced = useReducedMotion()
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    if (reduced) {
      el.style.setProperty(name, '1')
      return undefined
    }
    let cur = 0
    let last = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh || r.top > vh * 2) return
      const p = clamp01((vh * from - r.top) / (vh * (from - to)))
      cur += (p - cur) * ease
      if (Math.abs(cur - last) < 0.0005) return
      last = cur
      el.style.setProperty(name, cur.toFixed(4))
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [ref, reduced, from, to, name, ease])
}

/** Runs once the site's opening sequence has left the screen. */
export function whenIntroDone(cb) {
  if (!document.querySelector('.preloader')) {
    cb()
    return () => {}
  }
  const mo = new MutationObserver(() => {
    if (!document.querySelector('.preloader')) {
      mo.disconnect()
      cb()
    }
  })
  mo.observe(document.body, { childList: true, subtree: true })
  return () => mo.disconnect()
}

/** a line set word by word, each on its own rise; the last word in italic */
export function Rise({ text, accent = true }) {
  const words = text.split(' ')
  return words.map((w, i) => (
    <span key={i}>
      <span className="ld-word">
        <span className="ld-word__in" style={{ '--i': i }}>
          {accent && i === words.length - 1 ? <em>{w}</em> : w}
        </span>
      </span>
      {i < words.length - 1 ? ' ' : ''}
    </span>
  ))
}

/** the same line, rising when it comes on screen rather than on load */
export function RiseIn({ as: Tag = 'h2', text, className = '', accent = true, ...rest }) {
  const [el, setEl] = useState(null)
  const [seen, setSeen] = useState(false)

  useEffect(() => {
    if (!el) return undefined
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true)
          io.disconnect()
        }
      },
      { threshold: 0.4 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [el])

  return (
    <Tag ref={setEl} className={`ld-rise ${seen ? 'is-in' : ''} ${className}`} {...rest}>
      <Rise text={text} accent={accent} />
    </Tag>
  )
}

/** Text that is read into focus: every word starts dim and soft, and sharpens
    in turn as the block climbs the screen. */
export function Scrub({ as: Tag = 'p', text, className = '', span = 0.62 }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const words = useMemo(() => text.split(' '), [text])

  useEffect(() => {
    if (reduced) return undefined
    const el = ref.current
    const spans = [...el.querySelectorAll('.ld-w')]
    const n = spans.length
    const W = Math.max(5, Math.round(n * 0.16))
    let last = -1
    const tick = () => {
      const r = el.getBoundingClientRect()
      const vh = window.innerHeight
      if (r.bottom < -vh * 0.5 || r.top > vh * 1.5) return
      const p = clamp01((vh * 0.9 - r.top) / (r.height + vh * span))
      if (Math.abs(p - last) < 0.002) return
      last = p
      const head = p * (n + W) * 1.35
      for (let i = 0; i < n; i++) {
        const k = clamp01((head - i) / W)
        spans[i].style.opacity = (0.14 + 0.86 * k).toFixed(3)
        spans[i].style.filter = k < 0.98 ? `blur(${((1 - k) * 5).toFixed(2)}px)` : ''
      }
    }
    gsap.ticker.add(tick)
    return () => gsap.ticker.remove(tick)
  }, [reduced, words])

  return (
    <Tag ref={ref} className={className}>
      {words.map((w, i) => (
        <span key={i} className="ld-w">
          {w}{' '}
        </span>
      ))}
    </Tag>
  )
}
