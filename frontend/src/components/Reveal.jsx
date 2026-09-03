import { Children, cloneElement, isValidElement } from 'react'

import { useInView, useReducedMotion } from '@/lib/hooks'

import './Reveal.css'

/**
 * The site's single reveal primitive. Everything that animates in on scroll
 * goes through here so the timing stays consistent across sixty-odd sections.
 */
export default function Reveal({
  children,
  as: Tag = 'div',
  variant = 'up',
  delay = 0,
  className = '',
  style,
  ...rest
}) {
  const [ref, inView] = useInView()
  const reduced = useReducedMotion()

  return (
    <Tag
      ref={ref}
      className={`reveal reveal--${variant} ${inView || reduced ? 'is-in' : ''} ${className}`}
      style={delay && !reduced ? { ...style, transitionDelay: `${delay}ms` } : style}
      {...rest}
    >
      {children}
    </Tag>
  )
}

/** Reveals its children one after another. */
export function RevealGroup({ children, step = 90, variant = 'up', className = '', ...rest }) {
  const [ref, inView] = useInView()
  const reduced = useReducedMotion()

  return (
    <div ref={ref} className={className} {...rest}>
      {Children.map(children, (child, i) =>
        isValidElement(child)
          ? cloneElement(child, {
              className: `reveal reveal--${variant} ${inView || reduced ? 'is-in' : ''} ${child.props.className ?? ''}`,
              style: {
                ...child.props.style,
                ...(reduced ? {} : { transitionDelay: `${i * step}ms` }),
              },
            })
          : child,
      )}
    </div>
  )
}

/**
 * Splits a heading into lines that rise from a mask. Used sparingly — only on
 * the statement lines the art direction actually calls out.
 */
export function SplitLines({ lines, as: Tag = 'h2', className = '', step = 110 }) {
  const [ref, inView] = useInView({ threshold: 0.3 })
  const reduced = useReducedMotion()
  const on = inView || reduced

  return (
    <Tag ref={ref} className={`split ${className}`}>
      {lines.map((line, i) => (
        <span className="split__mask" key={i}>
          <span
            className={`split__line ${on ? 'is-in' : ''}`}
            style={reduced ? undefined : { transitionDelay: `${i * step}ms` }}
          >
            {line}
          </span>
        </span>
      ))}
    </Tag>
  )
}
