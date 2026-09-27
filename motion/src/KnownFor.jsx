/* What Zion is known for — eight short loops, one per promise, each a line
   drawing of the part of the lift the promise is about. Captions live on the
   page; the films carry only the marks a drawing would. Every loop ends where
   it began. */
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion'

import { C, Doors, Draw, Ground, MONO, Note, keys, t, tween } from './kit'

export const TILE = { fps: 30, width: 720, height: 900 }
const TAU = Math.PI * 2

/* the in-and-out every drawing shares: draw on, hold, fade out before the loop */
const life = (f, total, inEnd = 40, outStart = total - 24) => ({
  p: t(f, 4, inEnd),
  o: 1 - t(f, outStart, total - 2),
})

/* --- 01 · a technically sound workforce --------------------------------- */

export function Workforce() {
  const f = useCurrentFrame()
  const total = 180
  const { p, o } = life(f, total, 50)
  // three checks on the car frame at the man's feet
  const pts = [
    [210, 790],
    [470, 735],
    [600, 820],
  ]
  const k = keys(f, [
    [0, 0],
    [50, 0],
    [80, 1],
    [110, 1],
    [140, 2],
    [180, 2],
  ])
  const a = pts[Math.floor(k)] ?? pts[2]
  const b = pts[Math.min(2, Math.floor(k) + 1)]
  const fr = k - Math.floor(k)
  const cx = a[0] + (b[0] - a[0]) * fr
  const cy = a[1] + (b[1] - a[1]) * fr
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Img
        src={staticFile('workshop-frame.jpg')}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: '46% 50%',
          transform: `scale(${1.08 + 0.05 * (f / total)})`,
          filter: 'saturate(0.85) brightness(0.62)',
        }}
      />
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(8,9,11,0.35), rgba(8,9,11,0.1) 45%, rgba(8,9,11,0.7))' }} />
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }} opacity={o}>
        {/* a dimension line across the car frame */}
        <Draw d="M110 640 H610" p={p} stroke={C.teal} w={1.4} />
        <Draw d="M110 624 V656 M610 624 V656" p={p} stroke={C.teal} w={1.4} />
        <Note x={360} y={618} anchor="middle" color={C.teal} size={17} opacity={p}>
          1 400 MM
        </Note>
        {/* the gauge point moving between the checks */}
        <g transform={`translate(${cx} ${cy})`} opacity={t(f, 30, 50)}>
          <circle r={26} fill="none" stroke={C.ink} strokeWidth={1.2} />
          <circle r={3} fill={C.teal} />
          <path d="M-40 0 H-30 M30 0 H40 M0 -40 V-30 M0 30 V40" stroke={C.ink} strokeWidth={1.2} />
        </g>
        {pts.map(([x, y], i) => (
          <g key={i} opacity={t(f, 60 + i * 30, 72 + i * 30)}>
            <path d={`M${x} ${y - 30} V${y - 58}`} stroke={C.ink} strokeWidth={1} fill="none" opacity={0.7} />
            <Note x={x} y={y - 66} anchor={x > 500 ? 'end' : x < 260 ? 'start' : 'middle'} color={C.ink} size={14}>
              {['LEVEL ✓', 'SQUARE ✓', '± 0.5 MM ✓'][i]}
            </Note>
          </g>
        ))}
      </svg>
    </AbsoluteFill>
  )
}

/* --- 02 · custom lifts, to the client's brief ---------------------------- */

export function Custom() {
  const f = useCurrentFrame()
  // plan of the car: three briefs, then back to the first
  const w = keys(f, [
    [0, 300],
    [30, 300],
    [60, 380],
    [90, 380],
    [120, 270],
    [150, 270],
    [180, 300],
  ])
  const d = keys(f, [
    [0, 360],
    [30, 360],
    [60, 290],
    [90, 290],
    [120, 270],
    [150, 270],
    [180, 360],
  ])
  const r = keys(f, [
    [0, 4],
    [90, 4],
    [120, 135],
    [150, 135],
    [180, 4],
  ])
  const cx = 360
  const cy = 420
  const x = cx - w / 2
  const y = cy - d / 2
  const mm = (v) => Math.round((v * 3.4) / 10) * 10
  const round = r > 60
  return (
    <Ground>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }}>
        {/* the shaft in plan, and the car inside it */}
        <rect x={150} y={180} width={420} height={480} fill="none" stroke={C.ink} strokeWidth={1.4} opacity={0.35} strokeDasharray="6 6" />
        <rect x={x} y={y} width={w} height={d} rx={r} fill="rgba(46,201,202,0.10)" stroke={C.teal} strokeWidth={2} />
        {/* the door on the front face */}
        <path d={`M${cx - Math.min(w, 220) / 2 + 20} ${y + d + 16} H${cx + Math.min(w, 220) / 2 - 20}`} stroke={C.ink} strokeWidth={4} />
        {/* dimensions */}
        <path d={`M${x} ${y - 36} H${x + w} M${x} ${y - 46} V${y - 26} M${x + w} ${y - 46} V${y - 26}`} stroke={C.dim} strokeWidth={1.2} />
        <Note x={cx} y={y - 52} anchor="middle" color={C.ink} size={16}>
          {round ? `Ø ${mm(w)}` : `${mm(w)} MM`}
        </Note>
        {!round && (
          <g>
            <path d={`M${x + w + 36} ${y} V${y + d} M${x + w + 26} ${y} H${x + w + 46} M${x + w + 26} ${y + d} H${x + w + 46}`} stroke={C.dim} strokeWidth={1.2} />
            <Note x={x + w + 52} y={cy + 5} color={C.ink} size={16}>
              {mm(d)}
            </Note>
          </g>
        )}
        <Note x={360} y={740} anchor="middle" color={C.teal} size={15}>
          {round ? 'CAPSULE · 4 PERSONS' : w > 340 ? 'WIDE CAR · 8 PERSONS' : 'HOME LIFT · 4 PERSONS'}
        </Note>
      </svg>
    </Ground>
  )
}

/* --- 03 · to the latest safety standards --------------------------------- */

const CHECKS = ['DOOR LOCKS', 'SAFETY GEAR', 'OVERSPEED GOVERNOR', 'BUFFERS', 'EMERGENCY ALARM']

export function Standards() {
  const f = useCurrentFrame()
  const total = 180
  const { p, o } = life(f, total, 36)
  return (
    <Ground>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }} opacity={o}>
        {/* the shield */}
        <Draw d="M360 150 L470 190 V290 C470 360 420 400 360 430 C300 400 250 360 250 290 V190 Z" p={p} stroke={C.teal} w={2} />
        <Draw d="M312 290 L348 326 L412 256" p={t(f, 130, 150)} stroke={C.teal} w={3} />
        {/* the checklist */}
        {CHECKS.map((c, i) => {
          const y = 520 + i * 58
          const on = t(f, 40 + i * 18, 54 + i * 18)
          return (
            <g key={c}>
              <rect x={170} y={y - 22} width={28} height={28} rx={4} fill="none" stroke={C.ink} strokeWidth={1.3} opacity={0.6} />
              <Draw d={`M${176} ${y - 8} L${183} ${y} L${194} ${y - 16}`} p={on} stroke={C.teal} w={2.4} />
              <Note x={220} y={y} color={on > 0.5 ? C.ink : C.dim} size={17}>
                {c}
              </Note>
              <path d={`M170 ${y + 18} H550`} stroke={C.hair} strokeWidth={1} />
            </g>
          )
        })}
      </svg>
    </Ground>
  )
}

/* --- 04 · latest control systems, energy saving --------------------------- */

export function Energy() {
  const f = useCurrentFrame()
  const total = 180
  const ph = (f / total) * TAU * 2 // two cycles per loop: seamless
  // the drive smooths a hard supply into a sine the motor wants
  const square = []
  const sine = []
  for (let x = 0; x <= 520; x += 4) {
    const a = (x / 520) * TAU * 2 + ph
    square.push(`${x === 0 ? 'M' : 'L'}${100 + x} ${260 - Math.sign(Math.sin(a)) * 50}`)
    sine.push(`${x === 0 ? 'M' : 'L'}${100 + x} ${560 - Math.sin(a) * 60}`)
  }
  // a meter whose needle settles low and breathes
  const needle = -60 + 14 * Math.sin((f / total) * TAU) + 6
  const rot = (f / total) * 360 * 2
  return (
    <Ground>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }}>
        <Note x={100} y={180} color={C.dim}>
          SUPPLY
        </Note>
        <path d={square.join(' ')} stroke={C.ink} strokeWidth={1.4} fill="none" opacity={0.4} />
        {/* the VVVF drive in between */}
        <rect x={290} y={360} width={140} height={90} rx={6} fill={C.card} stroke={C.teal} strokeWidth={1.6} />
        <Note x={360} y={413} anchor="middle" color={C.teal} size={18}>
          VVVF
        </Note>
        <path d="M360 318 V360 M360 450 V488" stroke={C.teal} strokeWidth={1.4} strokeDasharray="4 5" />
        <Note x={100} y={480} color={C.dim}>
          TO MOTOR
        </Note>
        <path d={sine.join(' ')} stroke={C.teal} strokeWidth={2.2} fill="none" />
        {/* the motor, turning */}
        <g transform="translate(250 740)">
          <circle r={56} fill="none" stroke={C.ink} strokeWidth={1.4} opacity={0.6} />
          <g transform={`rotate(${rot})`}>
            {[0, 60, 120, 180, 240, 300].map((a) => (
              <path key={a} d="M0 0 L0 -44" transform={`rotate(${a})`} stroke={C.ink} strokeWidth={1.2} opacity={0.6} />
            ))}
          </g>
        </g>
        {/* the energy meter */}
        <g transform="translate(470 770)">
          <path d="M-80 0 A80 80 0 0 1 80 0" fill="none" stroke={C.faint} strokeWidth={10} />
          <path d="M-80 0 A80 80 0 0 1 -40 -69" fill="none" stroke={C.teal} strokeWidth={10} />
          <path d="M0 0 L0 -66" stroke={C.ink} strokeWidth={2.4} transform={`rotate(${needle})`} strokeLinecap="round" />
          <circle r={6} fill={C.ink} />
          <Note x={0} y={32} anchor="middle" color={C.dim} size={13}>
            ENERGY DRAW
          </Note>
        </g>
      </svg>
    </Ground>
  )
}

/* --- 05 · silent travel ---------------------------------------------------- */

export function Silent() {
  const f = useCurrentFrame()
  const total = 180
  const y = keys(f, [
    [0, 600],
    [20, 600],
    [80, 230],
    [100, 230],
    [160, 600],
    [180, 600],
  ])
  const moving = (f > 20 && f < 80) || (f > 100 && f < 160)
  return (
    <Ground>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }}>
        {/* the shaft */}
        <path d="M170 140 V820 M330 140 V820" stroke={C.ink} strokeWidth={1.3} opacity={0.5} />
        {[230, 415, 600].map((ly) => (
          <path key={ly} d={`M130 ${ly + 120} H170`} stroke={C.ink} strokeWidth={1.2} opacity={0.4} />
        ))}
        <rect x={182} y={y} width={136} height={120} rx={2} fill="rgba(46,201,202,0.10)" stroke={C.teal} strokeWidth={1.8} />
        <path d={`M250 140 V${y}`} stroke={C.ink} strokeWidth={1} opacity={0.4} />
        {/* the faint rings the car gives off */}
        {[0, 1, 2].map((i) => {
          const k = ((f / 60 + i / 3) % 1)
          return (
            <circle
              key={i}
              cx={250}
              cy={y + 60}
              r={70 + k * 60}
              fill="none"
              stroke={C.teal}
              strokeWidth={1}
              opacity={(moving ? 0.22 : 0.08) * (1 - k)}
            />
          )
        })}
        {/* the sound meter: a flat line well under the limit */}
        <g transform="translate(420 260)">
          <path d="M0 0 V440" stroke={C.ink} strokeWidth={1} opacity={0.3} />
          <path d="M0 60 H200" stroke={C.warn} strokeWidth={1.2} strokeDasharray="5 6" opacity={0.7} />
          <Note x={0} y={46} color={C.warn} size={13} opacity={0.85}>
            NOISY
          </Note>
          {Array.from({ length: 10 }, (_, i) => {
            const h = 10 + (moving ? 22 : 8) * (0.5 + 0.5 * Math.sin(f * 0.35 + i * 1.7))
            return <rect key={i} x={i * 20} y={440 - h} width={12} height={h} rx={2} fill={C.teal} opacity={0.8} />
          })}
          <Note x={0} y={480} color={C.dim} size={13}>
            IN THE CAR · dB(A)
          </Note>
        </g>
      </svg>
    </Ground>
  )
}

/* --- 06 · automatic rescue device, overload warning ----------------------- */

export const RESCUE_FRAMES = 240

export function Rescue() {
  const f = useCurrentFrame()
  const MID = 340 // stuck between floors
  const LAND = 470 // the floor below
  const carY = keys(f, [
    [0, MID],
    [44, MID],
    [104, LAND],
    [216, LAND],
    [240, MID],
  ])
  const dark = keys(f, [
    [0, 0],
    [18, 0],
    [26, 1],
    [130, 1],
    [140, 0],
  ])
  const open = keys(f, [
    [0, 0],
    [108, 0],
    [124, 1],
    [196, 1],
    [212, 0],
  ])
  const load = keys(f, [
    [0, 0],
    [132, 0],
    [160, 1.08],
    [182, 1.08],
    [194, 0.7],
    [206, 0],
  ])
  const over = load > 1
  const blink = over && Math.floor(f / 5) % 2 === 0
  const rescuing = f >= 26 && f < 124

  return (
    <Ground glow={false}>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }}>
        {/* the shaft, three landings */}
        <path d="M200 120 V820 M420 120 V820" stroke={C.ink} strokeWidth={1.3} opacity={0.5} />
        {[-50, 210, 470].map((ly) => (
          <path key={ly} d={`M150 ${ly + 180} H200`} stroke={C.ink} strokeWidth={1.2} opacity={0.4} />
        ))}
        {/* the car, with its doors */}
        <Doors
          x={214}
          y={carY}
          w={192}
          h={180}
          open={open}
          inside={<rect x={214} y={carY} width={192} height={180} fill={`rgba(46,201,202,${0.08 + 0.18 * (1 - dark)})`} />}
        />
        {/* the load bar inside the car */}
        <g opacity={t(f, 128, 136) * (1 - t(f, 206, 214))}>
          <rect x={440} y={carY + 20} width={20} height={140} rx={3} fill="none" stroke={C.ink} strokeWidth={1.2} opacity={0.6} />
          <rect
            x={442}
            y={carY + 158 - 136 * Math.min(1, load)}
            width={16}
            height={136 * Math.min(1, load)}
            rx={2}
            fill={over ? C.warn : C.teal}
          />
          <Note x={474} y={carY + 34} color={over ? C.warn : C.dim} size={14} opacity={blink || !over ? 1 : 0.35}>
            {over ? 'OVERLOAD' : 'LOAD'}
          </Note>
        </g>
        {/* the rescue unit: a battery that takes over when the mains go */}
        <g transform="translate(470 160)" opacity={t(f, 22, 30) * (1 - t(f, 124, 134))}>
          <rect width={70} height={36} rx={5} fill="none" stroke={C.teal} strokeWidth={1.6} />
          <rect x={70} y={11} width={6} height={14} fill={C.teal} />
          <rect x={6} y={6} width={58 * (0.4 + 0.6 * ((f % 30) / 30))} height={24} rx={2} fill={C.teal} opacity={0.7} />
          <Note x={0} y={64} color={C.teal} size={14}>
            ARD ON
          </Note>
          <Note x={0} y={86} color={C.dim} size={13}>
            TO NEAREST FLOOR
          </Note>
        </g>
        {rescuing && (
          <path d={`M310 ${carY + 200} V${LAND + 186}`} stroke={C.teal} strokeWidth={1.4} strokeDasharray="4 6" opacity={0.7} />
        )}
      </svg>
      {/* the mains going out */}
      <AbsoluteFill style={{ background: `rgba(0,0,0,${0.5 * dark})` }} />
      <div
        style={{
          position: 'absolute',
          left: 40,
          top: 40,
          fontFamily: MONO,
          fontSize: 14,
          letterSpacing: '0.1em',
          color: dark > 0.5 ? C.warn : C.dim,
        }}
      >
        {dark > 0.5 ? 'MAINS  ✕' : 'MAINS  ●'}
      </div>
    </Ground>
  )
}

/* --- 07 · genuine spares ---------------------------------------------------- */

export function Spares() {
  const f = useCurrentFrame()
  const total = 180
  // exploded apart, then seated, then apart again for the loop
  const s = keys(f, [
    [0, 1],
    [14, 1],
    [70, 0],
    [140, 0],
    [176, 1],
  ])
  const seal = t(f, 76, 112) * (1 - t(f, 134, 146))
  const at = (x, y, dx, dy) => `translate(${x + dx * s} ${y + dy * s})`
  return (
    <Ground>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }}>
        {/* the motor */}
        <g transform={at(120, 330, -50, -80)}>
          <rect width={170} height={150} rx={10} fill={C.card} stroke={C.ink} strokeWidth={1.4} />
          {[0, 1, 2, 3, 4].map((i) => (
            <path key={i} d={`M20 ${24 + i * 26} H150`} stroke={C.ink} strokeWidth={1} opacity={0.3} />
          ))}
        </g>
        {/* the brake */}
        <g transform={at(294, 322, 0, -150)}>
          <rect width={52} height={166} rx={6} fill={C.card} stroke={C.ink} strokeWidth={1.4} />
          <path d="M10 20 V146 M42 20 V146" stroke={C.teal} strokeWidth={2} opacity={0.8} />
        </g>
        {/* the bearing */}
        <g transform={at(374, 405, 30, 170)}>
          <circle r={44} fill="none" stroke={C.ink} strokeWidth={1.4} />
          <circle r={26} fill="none" stroke={C.ink} strokeWidth={1.4} />
          {Array.from({ length: 10 }, (_, i) => (
            <circle key={i} cx={Math.cos((i / 10) * TAU) * 35} cy={Math.sin((i / 10) * TAU) * 35} r={5} fill={C.ink} opacity={0.7} />
          ))}
        </g>
        {/* the grooved sheave */}
        <g transform={at(490, 405, 70, 0)}>
          <g transform={`rotate(${f * 2})`}>
            <circle r={92} fill={C.card} stroke={C.ink} strokeWidth={1.6} />
            {[80, 70, 60].map((r) => (
              <circle key={r} r={r} fill="none" stroke={C.teal} strokeWidth={1.2} opacity={0.6} />
            ))}
            <path d="M0 -40 V40 M-40 0 H40" stroke={C.ink} strokeWidth={1} opacity={0.4} />
            <circle r={16} fill="none" stroke={C.ink} strokeWidth={1.4} />
          </g>
        </g>
        {/* the base the machine is bolted to */}
        <path d="M90 520 H610" stroke={C.ink} strokeWidth={1.4} opacity={0.5 * (1 - s)} />
        {/* the seal: genuine, from the maker */}
        <g transform="translate(360 700)" opacity={seal}>
          <Draw d="M0 -70 A70 70 0 1 1 -0.1 -70" p={seal} stroke={C.teal} w={2} />
          <circle r={58} fill="none" stroke={C.teal} strokeWidth={1} opacity={0.5} />
          <Note x={0} y={-6} anchor="middle" color={C.teal} size={17} weight={600}>
            GENUINE
          </Note>
          <Note x={0} y={20} anchor="middle" color={C.dim} size={12}>
            OEM SPARES
          </Note>
        </g>
      </svg>
    </Ground>
  )
}

/* --- 08 · the maintenance schedule, kept ------------------------------------ */

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

export function Schedule() {
  const f = useCurrentFrame()
  const total = 180
  const reset = 1 - t(f, 160, 176)
  const cell = (i) => t(f, 12 + i * 11, 20 + i * 11) * reset
  const cur = Math.min(11, Math.max(0, Math.floor((f - 12) / 11)))
  return (
    <Ground>
      <svg width={720} height={900} style={{ position: 'absolute', inset: 0 }}>
        <Note x={130} y={200} color={C.dim}>
          SERVICE VISITS · ONE YEAR
        </Note>
        {MONTHS.map((m, i) => {
          const col = i % 3
          const row = Math.floor(i / 3)
          const x = 130 + col * 160
          const y = 230 + row * 130
          const done = cell(i)
          const now = i === cur && f < 150
          return (
            <g key={m}>
              <rect
                x={x}
                y={y}
                width={140}
                height={110}
                rx={10}
                fill={done > 0.5 ? 'rgba(46,201,202,0.08)' : 'none'}
                stroke={now ? C.teal : C.faint}
                strokeWidth={now ? 1.8 : 1.2}
              />
              <Note x={x + 16} y={y + 30} color={done > 0.5 ? C.ink : C.dim} size={14}>
                {m}
              </Note>
              <Draw d={`M${x + 52} ${y + 66} L${x + 66} ${y + 80} L${x + 92} ${y + 52}`} p={done} stroke={C.teal} w={2.6} />
            </g>
          )
        })}
        <Note x={360} y={790} anchor="middle" color={C.teal} size={15} opacity={reset}>
          {`${Math.round(tween(f, 12, 145, 0, 12, (x) => x))} / 12 ON SCHEDULE`}
        </Note>
      </svg>
    </Ground>
  )
}

export const KNOWN = [
  { id: 'known-workforce', component: Workforce, frames: 180 },
  { id: 'known-custom', component: Custom, frames: 180 },
  { id: 'known-standards', component: Standards, frames: 180 },
  { id: 'known-energy', component: Energy, frames: 180 },
  { id: 'known-silent', component: Silent, frames: 180 },
  { id: 'known-rescue', component: Rescue, frames: RESCUE_FRAMES },
  { id: 'known-spares', component: Spares, frames: 180 },
  { id: 'known-schedule', component: Schedule, frames: 180 },
]
