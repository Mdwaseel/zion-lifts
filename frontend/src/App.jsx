import { Suspense, lazy, useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'

import Layout from '@/components/Layout'
import Preloader, { hasSeenIntro } from '@/components/Preloader'
import { prefetchCore } from '@/lib/api'
import { useReducedMotion } from '@/lib/hooks'
import { SiteProvider } from '@/lib/site'

import Home from '@/pages/Home'

// Everything past the home page is split out — the first paint should only
// carry the hero and its imagery.
const Lifts = lazy(() => import('@/pages/Lifts'))
const LiftDetail = lazy(() => import('@/pages/LiftDetail'))
const Projects = lazy(() => import('@/pages/Projects'))
const ProjectDetail = lazy(() => import('@/pages/ProjectDetail'))
const About = lazy(() => import('@/pages/About'))
const Contact = lazy(() => import('@/pages/Contact'))
const Gallery = lazy(() => import('@/pages/Gallery'))
const Faq = lazy(() => import('@/pages/Faq'))
const Journal = lazy(() => import('@/pages/Journal'))
const JournalDetail = lazy(() => import('@/pages/JournalDetail'))
const Legal = lazy(() => import('@/pages/Legal'))
const NotFound = lazy(() => import('@/pages/NotFound'))

function RouteFallback() {
  return (
    <div className="route-fallback" role="status" aria-live="polite">
      <span className="sr-only">Loading</span>
      <span className="route-fallback__bar" />
    </div>
  )
}

/** Smooth momentum scrolling, unless the visitor has asked for reduced motion. */
function useLenis(enabled) {
  const reduced = useReducedMotion()

  useEffect(() => {
    if (!enabled || reduced) return
    let lenis
    let raf
    let cancelled = false

    import('lenis').then(({ default: Lenis }) => {
      if (cancelled) return
      lenis = new Lenis({ duration: 1.05, smoothWheel: true, wheelMultiplier: 0.95 })
      // Exposed so in-page controls can scroll through Lenis rather than
      // calling window.scrollTo, which Lenis' own rAF loop would fight.
      window.__lenis = lenis
      const loop = (t) => {
        lenis.raf(t)
        raf = requestAnimationFrame(loop)
      }
      raf = requestAnimationFrame(loop)
    })

    return () => {
      cancelled = true
      if (raf) cancelAnimationFrame(raf)
      lenis?.destroy()
      if (window.__lenis === lenis) delete window.__lenis
    }
  }, [enabled, reduced])
}

export default function App() {
  const [intro, setIntro] = useState(() => !hasSeenIntro())
  useLenis(!intro)

  useEffect(() => {
    prefetchCore()
  }, [])

  return (
    <SiteProvider>
      {intro && <Preloader onDone={() => setIntro(false)} />}
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="lifts" element={<Lifts />} />
            <Route path="lifts/:slug" element={<LiftDetail />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:slug" element={<ProjectDetail />} />
            <Route path="about" element={<About />} />
            <Route path="contact" element={<Contact />} />
            <Route path="gallery" element={<Gallery />} />
            <Route path="faq" element={<Faq />} />
            <Route path="journal" element={<Journal />} />
            <Route path="journal/:slug" element={<JournalDetail />} />
            <Route path="privacy" element={<Legal slug="privacy" />} />
            <Route path="terms" element={<Legal slug="terms" />} />
            <Route path="cookies" element={<Legal slug="cookies" />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </SiteProvider>
  )
}
