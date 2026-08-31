import { useEffect, useRef, useState } from 'react'

import { useInView, useReducedMotion } from '@/lib/hooks'
import { srcSet, tinySrc } from '@/lib/media'

import './Media.css'

/**
 * Lazy, responsive image with a fixed aspect box so nothing reflows on load.
 * `ratio` is width/height; pass `cover` for a fill layout.
 */
export function Img({
  src,
  alt = '',
  ratio,
  sizes = '100vw',
  priority = false,
  className = '',
  parallax = 0,
  objectPosition,
  ...rest
}) {
  const [ref, inView] = useInView({ threshold: 0.01, rootMargin: '300px 0px' })
  const [loaded, setLoaded] = useState(false)
  const imgRef = useRef(null)
  const reduced = useReducedMotion()
  const show = priority || inView

  // gentle vertical drift as the frame crosses the viewport
  useEffect(() => {
    if (!parallax || reduced) return
    const el = ref.current
    if (!el) return
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        const rect = el.getBoundingClientRect()
        if (rect.bottom < -200 || rect.top > window.innerHeight + 200) return
        const mid = rect.top + rect.height / 2
        const offset = (mid - window.innerHeight / 2) / window.innerHeight
        if (imgRef.current) {
          imgRef.current.style.transform = `translate3d(0, ${(-offset * parallax).toFixed(2)}px, 0) scale(1.08)`
        }
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [parallax, reduced, ref])

  if (!src) return <div ref={ref} className={`media media--empty ${className}`} aria-hidden="true" />

  const placeholder = tinySrc(src)

  return (
    <div
      ref={ref}
      className={`media ${loaded ? 'is-loaded' : ''} ${className}`}
      style={ratio ? { aspectRatio: ratio } : undefined}
    >
      {placeholder && !loaded && (
        <img className="media__blur" src={placeholder} alt="" aria-hidden="true" />
      )}
      {show && (
        <img
          ref={imgRef}
          className="media__img"
          src={src}
          srcSet={srcSet(src)}
          sizes={sizes}
          alt={alt}
          loading={priority ? 'eager' : 'lazy'}
          decoding={priority ? 'sync' : 'async'}
          fetchPriority={priority ? 'high' : 'auto'}
          onLoad={() => setLoaded(true)}
          style={objectPosition ? { objectPosition } : undefined}
          {...rest}
        />
      )}
    </div>
  )
}

/**
 * Muted looping background film. Only starts once on screen, and falls back to
 * the poster still under reduced-motion or when the file cannot play.
 */
export function VideoLoop({
  src,
  poster,
  ratio,
  className = '',
  objectPosition,
  playbackRate = 1,
}) {
  const [ref, inView] = useInView({ threshold: 0.15, rootMargin: '150px 0px' })
  const videoRef = useRef(null)
  const reduced = useReducedMotion()
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const v = videoRef.current
    if (!v || reduced || failed) return
    v.playbackRate = playbackRate
    if (inView) {
      v.play().catch(() => {
        /* autoplay refused — the poster stands in */
      })
    } else {
      v.pause()
    }
  }, [inView, reduced, failed, playbackRate])

  if (reduced || failed || !src) {
    return (
      <Img
        src={poster}
        alt=""
        ratio={ratio}
        className={className}
        objectPosition={objectPosition}
      />
    )
  }

  return (
    <div
      ref={ref}
      className={`media media--video is-loaded ${className}`}
      style={ratio ? { aspectRatio: ratio } : undefined}
    >
      {poster && <img className="media__blur" src={poster} alt="" aria-hidden="true" />}
      <video
        ref={videoRef}
        className="media__img"
        src={inView ? src : undefined}
        poster={poster}
        muted
        loop
        playsInline
        preload="none"
        aria-hidden="true"
        onError={() => setFailed(true)}
        style={objectPosition ? { objectPosition } : undefined}
      />
    </div>
  )
}

/** Full film with sound and native controls — used for project and testimonial reels. */
export function VideoPlayer({ src, poster, ratio = '16 / 9', className = '', label }) {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef(null)

  const start = () => {
    setPlaying(true)
    requestAnimationFrame(() => videoRef.current?.play())
  }

  return (
    <div className={`videoplayer ${className}`} style={{ aspectRatio: ratio }}>
      <video
        ref={videoRef}
        className="videoplayer__el"
        src={src}
        poster={poster}
        controls={playing}
        playsInline
        preload="metadata"
        onPlay={() => setPlaying(true)}
      />
      {!playing && (
        <button type="button" className="videoplayer__cover" onClick={start}>
          <span className="videoplayer__btn" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
          <span className="videoplayer__label">{label ?? 'Play film'}</span>
        </button>
      )}
    </div>
  )
}
