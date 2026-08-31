/**
 * GSAP + ScrollTrigger, registered once.
 *
 * ScrollTrigger is used here to *measure* scroll, not to pin. Every pinned
 * section on the home page holds itself with `position: sticky` over a scroll
 * runway; introducing ScrollTrigger's own pinning for one section among six
 * would mean two pinning systems fighting over the same document height, which
 * is where the classic refresh-order and failed-unpin bugs come from.
 *
 * Lenis drives the real window scroll, so native scroll events still fire and
 * ScrollTrigger stays in sync. Updating on GSAP's ticker as well keeps the
 * measurement on the same frame as Lenis' interpolation rather than one behind.
 */
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

let registered = false

export function initGsap() {
  if (registered) return { gsap, ScrollTrigger }
  gsap.registerPlugin(ScrollTrigger)
  gsap.ticker.add(ScrollTrigger.update)
  gsap.ticker.lagSmoothing(0)
  registered = true
  return { gsap, ScrollTrigger }
}

export { gsap, ScrollTrigger }
