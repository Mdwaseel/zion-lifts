/* The opening film of /about: made, built in, ridden, lived in.
   Five of Zion's own photographs crossfade under a slow push, and down the
   right third a shaft is drawn in hairline with the car riding it — one floor
   per photograph, then an express run back to the ground floor as the last
   frame dissolves into the first, so the loop has no seam. */
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion'

import { C, Draw, MONO, Note, keys, t } from './kit'

export const HERO = { fps: 30, frames: 360, width: 1920, height: 1080 }

const SHOTS = [
  { src: 'workshop-sparks.jpg', pos: '58% 50%', label: 'Fabrication' },
  { src: 'lekha-hall.jpg', pos: '50% 50%', label: 'Structure' },
  { src: 'chilkuru-capsule.jpg', pos: '50% 50%', label: 'Installation' },
  { src: 'lacheta-glass.jpg', pos: '50% 50%', label: 'Commissioning' },
  { src: 'lekha-aerial.jpg', pos: '50% 50%', label: 'Handover' },
]
const SLOT = 72 // frames each photograph leads
const FADE = 20

/* the shaft */
const SX = 1560
const SW = 150
const TOP = 150
const BOT = 930
const FLOORS = SHOTS.length
const FH = (BOT - TOP) / FLOORS

function Photo({ i, f }) {
  const s = SHOTS[i]
  // local time, wrapped so the first photograph is already fading in at the end
  const local = (f - i * SLOT + FADE + HERO.frames) % HERO.frames
  const life = SLOT + FADE
  if (local > life) return null
  const op = Math.min(1, local / FADE) * (local > SLOT ? 1 - (local - SLOT) / FADE : 1)
  const scale = 1.04 + 0.07 * (local / life)
  return (
    <AbsoluteFill style={{ opacity: op }}>
      <Img
        src={staticFile(s.src)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: s.pos,
          transform: `scale(${scale})`,
          filter: 'saturate(1.08) contrast(1.02) brightness(1.04)',
        }}
      />
    </AbsoluteFill>
  )
}

export function Hero() {
  const f = useCurrentFrame()

  // the floor the car is at: it moves during each crossfade, and runs home at the end
  const ks = [[0, 0]]
  for (let i = 1; i < FLOORS; i++) {
    ks.push([i * SLOT - FADE, i - 1], [i * SLOT + 4, i])
  }
  ks.push([FLOORS * SLOT - FADE - 24, FLOORS - 1], [HERO.frames, 0])
  const level = keys(f, ks)
  const carY = BOT - (level + 1) * FH + 10
  const shown = Math.round(level)
  const going = f > FLOORS * SLOT - FADE - 24 ? -1 : 1
  const moving = Math.abs(level - shown) > 0.02

  // the drawing is on screen from the start of the loop; it never draws out
  const rail = 1

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {SHOTS.map((_, i) => (
        <Photo key={i} i={i} f={f} />
      ))}

      {/* the grade the page type sits on, and a darker band behind the drawing */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(90deg, rgba(8,9,11,0.5) 0%, rgba(8,9,11,0.16) 36%, rgba(8,9,11,0) 58%, rgba(8,9,11,0.42) 100%)',
        }}
      />
      <AbsoluteFill style={{ background: 'linear-gradient(0deg, rgba(8,9,11,0.45) 0%, transparent 30%)' }} />

      <svg width={HERO.width} height={HERO.height} style={{ position: 'absolute', inset: 0 }}>
        {/* guide rails and the shaft wall */}
        <Draw d={`M${SX} ${TOP - 40} V${BOT + 30}`} p={rail} stroke={C.ink} opacity={0.5} w={1.2} />
        <Draw d={`M${SX + SW} ${TOP - 40} V${BOT + 30}`} p={rail} stroke={C.ink} opacity={0.5} w={1.2} />
        <Draw d={`M${SX + 16} ${TOP - 40} V${BOT + 30}`} p={rail} stroke={C.ink} opacity={0.2} w={1} />
        <Draw d={`M${SX + SW - 16} ${TOP - 40} V${BOT + 30}`} p={rail} stroke={C.ink} opacity={0.2} w={1} />

        {/* landings, with the stage each one stands for */}
        {SHOTS.map((s, i) => {
          const y = BOT - i * FH
          const on = shown === i
          return (
            <g key={s.src}>
              <path d={`M${SX - 60} ${y} H${SX}`} stroke={on ? C.teal : C.ink} strokeWidth={1.2} opacity={on ? 1 : 0.35} />
              <path d={`M${SX + SW} ${y} H${SX + SW + 24}`} stroke={C.ink} strokeWidth={1.2} opacity={0.35} />
              <Note x={SX - 72} y={y - 12} anchor="end" color={on ? C.ink : C.dim} size={15} opacity={on ? 1 : 0.7}>
                {s.label.toUpperCase()}
              </Note>
              <Note x={SX - 72} y={y + 22} anchor="end" color={on ? C.teal : C.faint} size={13}>
                {i === 0 ? 'G' : `L${i}`}
              </Note>
            </g>
          )
        })}

        {/* the travelling cable and the car */}
        <path d={`M${SX + SW / 2} ${TOP - 40} V${carY}`} stroke={C.ink} strokeWidth={1} opacity={0.4} />
        <g transform={`translate(${SX + 10} ${carY})`}>
          <rect width={SW - 20} height={FH - 20} fill="rgba(46,201,202,0.10)" stroke={C.teal} strokeWidth={1.6} rx={2} />
          <path d={`M${(SW - 20) / 2} 8 V${FH - 28}`} stroke={C.teal} strokeWidth={1} opacity={0.6} />
          <rect x={10} y={10} width={SW - 40} height={FH - 40} fill="none" stroke={C.teal} strokeWidth={0.8} opacity={0.35} />
        </g>
      </svg>

      {/* the indicator above the shaft: the floor, the way the lift shows it */}
      <div
        style={{
          position: 'absolute',
          left: SX,
          top: TOP - 118,
          width: SW,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 14,
          fontFamily: MONO,
          color: C.teal,
          fontSize: 34,
          letterSpacing: '0.06em',
        }}
      >
        <svg width={18} height={22} viewBox="0 0 18 22" style={{ opacity: moving ? 1 : 0.25, transform: going < 0 ? 'rotate(180deg)' : 'none' }}>
          <path d="M9 2 16 12H2Z" fill={C.teal} />
          <path d="M9 11 16 21H2Z" fill={C.teal} opacity={0.35} />
        </svg>
        <span>{shown === 0 ? 'G' : `0${shown}`}</span>
      </div>

      {/* registration marks at the corners of the frame */}
      <svg width={HERO.width} height={HERO.height} style={{ position: 'absolute', inset: 0 }} opacity={0.5}>
        {[
          [60, 60, 1, 1],
          [HERO.width - 60, 60, -1, 1],
          [60, HERO.height - 60, 1, -1],
          [HERO.width - 60, HERO.height - 60, -1, -1],
        ].map(([x, y, dx, dy], i) => (
          <path key={i} d={`M${x} ${y + dy * 26} V${y} H${x + dx * 26}`} stroke={C.ink} strokeWidth={1.2} fill="none" />
        ))}
      </svg>

      {/* a scan line that crosses the frame once a loop */}
      <AbsoluteFill style={{ pointerEvents: 'none' }}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${t(f, 0, HERO.frames, (x) => x) * 100}%`,
            height: 1,
            background: 'linear-gradient(90deg, transparent, rgba(46,201,202,0.35), transparent)',
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  )
}
