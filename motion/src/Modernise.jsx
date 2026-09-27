/* Modernisation, in one landing: the old manual collapsible gate folds open
   and shut, a sweep crosses the doorway, and behind it stand automatic
   centre-opening doors with an indicator and a call button — which open on a
   lit car. The sweep goes back the other way so the loop closes on itself. */
import { AbsoluteFill, useCurrentFrame } from 'remotion'

import { C, Doors, Ground, Note, keys, t, tween } from './kit'

export const MODERNISE = { fps: 30, frames: 270, width: 1080, height: 1080 }

const X = 330
const Y = 250
const W = 420
const H = 600

function Gate({ open }) {
  // the lattice folds towards the left jamb
  const n = 9
  const span = W * (1 - open * 0.86)
  const step = span / (n - 1)
  const bars = Array.from({ length: n }, (_, i) => X + i * step)
  const rows = 6
  const rh = H / rows
  return (
    <g stroke={C.ink} strokeWidth={1.4} fill="none">
      {bars.map((x, i) => (
        <path key={i} d={`M${x} ${Y} V${Y + H}`} opacity={0.85} />
      ))}
      {bars.slice(0, -1).map((x, i) =>
        Array.from({ length: rows }, (_, r) => (
          <path
            key={`${i}-${r}`}
            d={`M${x} ${Y + r * rh} L${x + step} ${Y + (r + 1) * rh} M${x + step} ${Y + r * rh} L${x} ${Y + (r + 1) * rh}`}
            opacity={0.45}
          />
        )),
      )}
      {/* the handle on the leading bar */}
      <rect x={bars[n - 1] - 5} y={Y + H * 0.48} width={10} height={40} fill={C.bg} stroke={C.ink} />
    </g>
  )
}

function Cabin() {
  return (
    <g>
      <rect x={X} y={Y} width={W} height={H} fill="rgba(46,201,202,0.12)" />
      <path d={`M${X + 40} ${Y + 30} H${X + W - 40}`} stroke={C.teal} strokeWidth={3} opacity={0.9} />
      <path d={`M${X + 30} ${Y + H * 0.55} H${X + W - 30}`} stroke={C.teal} strokeWidth={1.2} opacity={0.5} />
      <rect x={X + W - 70} y={Y + H * 0.35} width={26} height={120} fill="none" stroke={C.teal} strokeWidth={1.2} opacity={0.7} />
    </g>
  )
}

export function Modernise() {
  const f = useCurrentFrame()

  // the old gate: open and shut once
  const gate = keys(f, [
    [0, 0],
    [14, 0],
    [44, 1],
    [62, 1],
    [92, 0],
  ])
  // the sweep that turns old into new, and back again at the end
  const wipe = keys(f, [
    [0, 0],
    [98, 0],
    [132, 1],
    [232, 1],
    [266, 0],
  ])
  // the new doors open on the lit car, and close
  const doors = keys(f, [
    [0, 0],
    [146, 0],
    [170, 1],
    [202, 1],
    [226, 0],
  ])
  const called = f > 136 && f < 226
  const edge = X - 60 + wipe * (W + 120)

  return (
    <Ground>
      <svg width={1080} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <clipPath id="old">
            <rect x={edge} y={0} width={1080} height={1080} />
          </clipPath>
          <clipPath id="new">
            <rect x={0} y={0} width={edge} height={1080} />
          </clipPath>
        </defs>

        {/* the wall and the floor the landing stands in */}
        <path d={`M120 ${Y + H} H960`} stroke={C.ink} strokeWidth={1.4} opacity={0.6} />
        <path d={`M120 ${Y + H + 14} H960`} stroke={C.ink} strokeWidth={1} opacity={0.18} />

        {/* before */}
        <g clipPath="url(#old)">
          <rect x={X - 16} y={Y - 16} width={W + 32} height={H + 16} fill="none" stroke={C.ink} strokeWidth={1.4} opacity={0.5} />
          <rect x={X} y={Y} width={W} height={H} fill="#050607" />
          <Gate open={gate} />
          <Note x={X} y={Y - 44} color={C.dim}>
            MANUAL COLLAPSIBLE GATE
          </Note>
        </g>

        {/* after */}
        <g clipPath="url(#new)">
          <Doors x={X} y={Y} w={W} h={H} open={doors} inside={<Cabin />} />
          {/* indicator */}
          <rect x={X + W / 2 - 60} y={Y - 74} width={120} height={40} rx={4} fill="#050607" stroke={C.ink} strokeWidth={1.2} opacity={0.9} />
          <Note x={X + W / 2} y={Y - 47} anchor="middle" color={C.teal} size={20}>
            {called ? '▲ 03' : '03'}
          </Note>
          {/* the call button */}
          <rect x={X + W + 46} y={Y + H * 0.46} width={34} height={86} rx={6} fill="none" stroke={C.ink} strokeWidth={1.2} opacity={0.8} />
          <circle cx={X + W + 63} cy={Y + H * 0.46 + 43} r={9} fill={called ? C.teal : 'none'} stroke={C.teal} strokeWidth={1.5} />
          <Note x={X} y={Y - 110} color={C.dim}>
            AUTOMATIC DOORS · VVVF CONTROL
          </Note>
        </g>

        {/* the sweep */}
        {wipe > 0.001 && wipe < 0.999 && (
          <g>
            <path d={`M${edge} 120 V${Y + H + 60}`} stroke={C.teal} strokeWidth={2} />
            <path d={`M${edge} 120 V${Y + H + 60}`} stroke={C.teal} strokeWidth={14} opacity={0.12} />
          </g>
        )}
      </svg>

      {/* the state, captioned at the foot */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 110,
          display: 'flex',
          justifyContent: 'center',
          gap: 40,
          fontSize: 22,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
        }}
      >
        <span style={{ color: C.ink, opacity: tween(f, 98, 132, 1, 0.3) + t(f, 232, 266) * 0.7 }}>Before</span>
        <span style={{ color: C.teal, opacity: 0.3 + t(f, 98, 132) * 0.7 - t(f, 232, 266) * 0.7 }}>After</span>
      </div>
    </Ground>
  )
}
