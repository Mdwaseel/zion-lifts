/* The drawing kit every film shares: the site's dark ground, its teal, a
   hairline stroke, and a few easing helpers. Everything is drawn in SVG so the
   films stay line drawings of lifts, not illustrations. */
import { AbsoluteFill, Easing, interpolate } from 'remotion'

export const C = {
  bg: '#08090b',
  card: '#0d0f12',
  ink: '#f5f5f2',
  dim: 'rgba(245,245,242,0.42)',
  faint: 'rgba(245,245,242,0.14)',
  hair: 'rgba(245,245,242,0.08)',
  teal: '#2ec9ca',
  tealDeep: '#066f70',
  warn: '#ff6b5a',
}

export const FONT = "Inter, 'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
export const MONO = "'JetBrains Mono', Consolas, 'SF Mono', monospace"

export const ease = Easing.bezier(0.22, 0.61, 0.36, 1)
export const inOut = Easing.bezier(0.65, 0, 0.35, 1)

/** 0 → 1 between two frames, eased */
export const t = (f, a, b, e = inOut) =>
  interpolate(f, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: e })

/** a value held at `from`, moving to `to` between frames a and b */
export const tween = (f, a, b, from, to, e = inOut) => from + (to - from) * t(f, a, b, e)

/** piecewise: keys = [[frame, value], ...], eased between each pair */
export const keys = (f, ks, e = inOut) => {
  if (f <= ks[0][0]) return ks[0][1]
  for (let i = 1; i < ks.length; i++) {
    if (f <= ks[i][0]) return tween(f, ks[i - 1][0], ks[i][0], ks[i - 1][1], ks[i][1], e)
  }
  return ks[ks.length - 1][1]
}

/** a stroke that draws on: pass the drawn fraction 0..1 */
export const Draw = ({ d, p = 1, stroke = C.ink, w = 1.5, opacity = 1, ...rest }) => (
  <path
    d={d}
    pathLength={1}
    fill="none"
    stroke={stroke}
    strokeWidth={w}
    strokeLinecap="round"
    strokeLinejoin="round"
    strokeDasharray="1 1"
    strokeDashoffset={1 - p}
    opacity={opacity}
    {...rest}
  />
)

/** the ground every tile sits on: dark and plain; a drafting grid only when asked for */
export const Ground = ({ children, grid = 0, glow = true }) => (
  <AbsoluteFill style={{ background: C.bg, fontFamily: FONT, color: C.ink }}>
    {grid > 0 && (
    <AbsoluteFill
      style={{
        backgroundImage: `linear-gradient(${C.hair} 1px, transparent 1px), linear-gradient(90deg, ${C.hair} 1px, transparent 1px)`,
        backgroundSize: `${grid}px ${grid}px`,
        backgroundPosition: 'center center',
        maskImage: 'radial-gradient(ellipse at 50% 45%, #000 30%, transparent 80%)',
        WebkitMaskImage: 'radial-gradient(ellipse at 50% 45%, #000 30%, transparent 80%)',
      }}
    />
    )}
    {glow && (
      <AbsoluteFill
        style={{ background: 'radial-gradient(ellipse 60% 45% at 50% 42%, rgba(46,201,202,0.10), transparent 70%)' }}
      />
    )}
    {children}
  </AbsoluteFill>
)

/** a small mono label, the way a drawing is annotated */
export const Note = ({ x, y, children, color = C.dim, size = 15, anchor = 'start', opacity = 1, weight = 500 }) => (
  <text
    x={x}
    y={y}
    fill={color}
    fontFamily={MONO}
    fontSize={size}
    fontWeight={weight}
    letterSpacing="0.08em"
    textAnchor={anchor}
    opacity={opacity}
  >
    {children}
  </text>
)

/** a pair of landing doors in elevation, `open` 0..1, centre-opening */
export const Doors = ({ x, y, w, h, open, stroke = C.ink, fill = C.card, inside = null }) => {
  const leaf = (w / 2) * (1 - open * 0.94)
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill="#050607" />
      {inside}
      <rect x={x} y={y} width={leaf} height={h} fill={fill} stroke={stroke} strokeWidth={1.4} />
      <rect x={x + w - leaf} y={y} width={leaf} height={h} fill={fill} stroke={stroke} strokeWidth={1.4} />
      <rect x={x - 6} y={y - 6} width={w + 12} height={h + 6} fill="none" stroke={stroke} strokeWidth={1.4} opacity={0.6} />
    </g>
  )
}
