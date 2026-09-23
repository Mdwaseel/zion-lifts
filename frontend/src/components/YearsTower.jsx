/** Thirteen years as an elevation.

   The company's history is drawn as a building that goes up a storey at a time:
   each milestone is a floor with architecture of its own — the workshop it
   started in, the factory floor, the office levels, the service desk with its
   light on, the machine at the head of the shaft, the glazed capsule level, the
   crown. A tower crane stands on whatever is the top floor, and a car in the
   shaft beside the building rides to the floor in hand.

   Pure: it is told which storey is current and draws the rest from that. */

const W = 300 // width of a storey
const H = 84 // height of a storey
const LEFT = 118 // where the building starts
const GROUND = 704
const SHAFT = 54 // width of the lift shaft on the building's flank

const top = (i) => GROUND - (i + 1) * H

/* Every storey's own detail, drawn in its local box (0,0)–(300,84). Each stroke
   carries pathLength="1" so the floor can trace itself as it is built. */
const DETAILS = [
  // 2012 — the workshop: a roller shutter, a side door, a bench under a lamp
  <g key="0">
    <rect pathLength="1" x="18" y="22" width="104" height="62" />
    <path pathLength="1" d="M18 32h104M18 42h104M18 52h104M18 62h104M18 72h104" />
    <rect pathLength="1" x="142" y="36" width="26" height="48" />
    <path pathLength="1" d="M196 66h84M204 66v18M272 66v18" />
    <path pathLength="1" d="M238 14v16M228 30h20l-4 9h-12Z" />
  </g>,
  // 2014 — manufacturing: tall factory lights and a gantry crane on its rail
  <g key="1">
    <path pathLength="1" d="M10 16h280" />
    <path pathLength="1" d="M176 16v-6h22v6M187 16v22M181 38h12l-3 8h-6Z" />
    {[22, 76, 130, 184, 238].map((x) => (
      <rect pathLength="1" key={x} x={x} y="30" width="40" height="54" />
    ))}
  </g>,
  // 2016 — commercial and institutional work: two ranks of office windows
  <g key="2">
    {[16, 52, 88, 124, 160, 196, 232, 268].map((x) => (
      <g key={x}>
        <rect pathLength="1" x={x} y="12" width="18" height="24" />
        <rect pathLength="1" x={x} y="48" width="18" height="24" />
      </g>
    ))}
  </g>,
  // 2018 — the service desk: one window lit through the night, a line that is always open
  <g key="3">
    {[16, 64, 112, 208, 256].map((x) => (
      <rect pathLength="1" key={x} x={x} y="18" width="30" height="48" />
    ))}
    <rect pathLength="1" className="yt-lit" x="160" y="18" width="30" height="48" />
    <path pathLength="1" d="M198 30a10 10 0 0 1 0 16M203 25a17 17 0 0 1 0 26" className="yt-wave" />
  </g>,
  // 2020 — gearless, machine-room-less: the machine itself, shown in the wall
  <g key="4">
    <circle pathLength="1" cx="150" cy="42" r="28" />
    <circle pathLength="1" cx="150" cy="42" r="17" />
    <circle pathLength="1" cx="150" cy="42" r="4" />
    <path pathLength="1" d="M150 14v-14M122 42h-16M178 42h16" />
    {[18, 56, 226, 264].map((x) => (
      <rect pathLength="1" key={x} x={x} y="18" width="20" height="48" />
    ))}
  </g>,
  // 2022 — glass and capsule: a fully glazed level, the capsule bowing out of its flank
  <g key="5">
    {Array.from({ length: 14 }, (_, k) => 20 + k * 20).map((x) => (
      <path pathLength="1" key={x} d={`M${x} 6v72`} />
    ))}
    <path pathLength="1" d="M6 6h288M6 78h288" />
    <path pathLength="1" d="M0 10a32 32 0 0 0 0 64" />
  </g>,
  // 2024 — the crown: a set-back top floor, a mast, and the figure on the roof
  <g key="6">
    <path pathLength="1" d="M40 84V26h220v58" />
    <path pathLength="1" d="M28 26h244" />
    {[58, 96, 134, 172, 210].map((x) => (
      <rect pathLength="1" key={x} x={x} y="40" width="24" height="44" />
    ))}
    <path pathLength="1" d="M150 26V-22M142 -10h16M145 -16h10" />
  </g>,
]

export default function YearsTower({ years, active, zoomed, sign, onPick }) {
  const n = Math.min(years.length, DETAILS.length)
  const at = Math.min(active, n - 1)
  // on a narrow screen the camera moves in on the floor in hand
  const k = zoomed ? 1.65 : 1
  const fx = LEFT + W / 2 + 12
  const fy = zoomed ? top(at) + H / 2 - 6 : 392
  const cam = `translate(${(260 - fx * k).toFixed(1)}px, ${(392 - fy * k).toFixed(1)}px) scale(${k})`

  return (
    <svg className="yt" viewBox="0 0 520 784" role="img" aria-label={`A building drawn one storey per milestone; the floor for ${years[at]} is current`}>
      <g className="yt-cam" style={{ transform: cam }}>
        {/* the ground it stands on */}
        <g className="yt-ground">
          <path d={`M24 ${GROUND}h472`} />
          <path d={`M36 ${GROUND + 8}l10 -8M66 ${GROUND + 8}l10 -8M96 ${GROUND + 8}l10 -8M430 ${GROUND + 8}l10 -8M460 ${GROUND + 8}l10 -8`} />
        </g>

        {years.slice(0, n).map((year, i) => {
          const state = i === at ? 'is-on is-built' : i < at ? 'is-built' : ''
          return (
            <g
              key={year}
              className={`yt-storey ${state}`}
              transform={`translate(${LEFT} ${top(i)})`}
              onClick={() => onPick?.(i)}
            >
              {/* what is still to come, pencilled in */}
              <rect className="yt-ghost" x="0" y="0" width={W + SHAFT} height={H} />
              <g className="yt-lines">
                <rect pathLength="1" x="0" y="0" width={W} height={H} />
                {/* this floor's length of lift shaft, and its landing door */}
                <path pathLength="1" d={`M${W} 0h${SHAFT}v${H}`} />
                <path pathLength="1" d={`M${W + 12} ${H}V34h${SHAFT - 24}v50`} className="yt-door" />
                {DETAILS[i]}
              </g>
              <g className="yt-level">
                <path d={`M-14 ${H}h10`} />
                <text x="-20" y={H - 30} textAnchor="end">
                  {year}
                </text>
                <text x="-20" y={H - 16} textAnchor="end" className="yt-level__n">
                  L{i + 1}
                </text>
              </g>
              <rect className="yt-hit" x="-70" y="0" width={W + SHAFT + 70} height={H} />
            </g>
          )
        })}

        {/* the figure on the roof, once the crown is on */}
        <text className={`yt-sign ${at === n - 1 ? 'is-on' : ''}`} x={LEFT + W / 2} y={top(n - 1) - 34} textAnchor="middle">
          {sign}
        </text>

        {/* the car, riding to the floor in hand */}
        <g className="yt-car" style={{ transform: `translate(${LEFT + W + 9}px, ${top(at) + 20}px)` }}>
          <rect x="0" y="0" width={SHAFT - 18} height={H - 26} rx="2" />
          <path d={`M${(SHAFT - 18) / 2} 0V${H - 26}`} />
        </g>

        {/* the tower crane, standing on whatever is the top floor */}
        <g className={`yt-crane ${at === n - 1 ? 'is-gone' : ''}`} style={{ transform: `translate(${LEFT + 46}px, ${top(at)}px)` }}>
          <path d="M0 0v-96M8 0v-96M0 -12l8 -12l-8 -12l8 -12l-8 -12l8 -12l-8 -12" />
          <path d="M-34 -96h210M-34 -96l38 -18l172 18M4 -114v18" />
          <path d="M-34 -96v12h16v-12" />
          <path className="yt-hook" d="M132 -96v34M127 -62h10l-2 8h-6Z" />
        </g>
      </g>
    </svg>
  )
}
