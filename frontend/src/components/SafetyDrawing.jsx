/** A section through the lift, with every safety system drawn where it lives.

   One system is "in hand" at a time: its part of the drawing lights and traces
   itself, a ring pulses on it, and the camera moves through the shaft to frame
   it. Everything else stays as a quiet line drawing. The component is pure —
   it is told which system is active and does the rest in CSS. */

/* where the camera looks for each system, in drawing units, and how close */
const FOCUS = {
  overload: { x: 200, y: 424, k: 1.75 },
  'power-failure': { x: 176, y: 214, k: 1.7 },
  'emergency-braking': { x: 226, y: 300, k: 1.02 },
  'fire-mode': { x: 170, y: 548, k: 1.5 },
  'door-protection': { x: 200, y: 346, k: 1.95 },
  'emergency-comms': { x: 236, y: 344, k: 2.25 },
  seismic: { x: 200, y: 320, k: 1.0 },
}

/* where the ring sits */
const RING = {
  overload: [200, 436],
  'power-failure': [171, 241],
  'emergency-braking': [286, 56],
  'fire-mode': [44, 608],
  'door-protection': [200, 345],
  'emergency-comms': [243, 343],
  seismic: [112, 180],
}

const VIEW = { w: 400, h: 640 }

export default function SafetyDrawing({ active }) {
  const f = FOCUS[active] ?? { x: 200, y: 320, k: 1 }
  const ring = RING[active]
  const cam = `translate(${(VIEW.w / 2 - f.x * f.k).toFixed(1)}px, ${(VIEW.h / 2 - f.y * f.k).toFixed(1)}px) scale(${f.k})`
  const hot = (slug) => `sd-hot ${active === slug ? 'is-on' : ''}`

  return (
    <svg className="sd" viewBox={`0 0 ${VIEW.w} ${VIEW.h}`} role="img" aria-label="Section through the lift shaft showing where each safety system sits">
      <g className="sd-cam" style={{ transform: cam }}>
        {/* --- the building: shaft, landings, pit --- */}
        <g className="sd-base">
          <rect x="100" y="24" width="200" height="596" />
          <line x1="124" y1="40" x2="124" y2="612" />
          <line x1="276" y1="40" x2="276" y2="612" />
          <line x1="56" y1="190" x2="100" y2="190" />
          <line x1="56" y1="430" x2="100" y2="430" />
          <line x1="56" y1="612" x2="100" y2="612" />
          <path d="M164 612v-8l6-3-12-4 12-4-12-4 6-3v-6M236 612v-8l6-3-12-4 12-4-12-4 6-3v-6" />
          {/* machine */}
          <circle cx="200" cy="62" r="20" />
          <circle cx="200" cy="62" r="4" />
          <rect x="146" y="50" width="32" height="24" rx="2" />
          <line x1="138" y1="86" x2="262" y2="86" />
          <line x1="193" y1="81" x2="193" y2="250" />
          <line x1="207" y1="81" x2="207" y2="250" />
          {/* car */}
          <rect x="146" y="250" width="108" height="180" rx="2" />
          <rect x="168" y="262" width="64" height="166" />
          <line x1="200" y1="262" x2="200" y2="428" />
          <line x1="140" y1="430" x2="260" y2="430" className="sd-thick" />
        </g>
        <g className="sd-text">
          <text x="40" y="194">2</text>
          <text x="40" y="434">1</text>
          <text x="40" y="616">G</text>
        </g>

        {/* --- overload: load cells under the platform --- */}
        <g className={hot('overload')}>
          <rect pathLength="1" x="156" y="432" width="14" height="7" />
          <rect pathLength="1" x="193" y="432" width="14" height="7" />
          <rect pathLength="1" x="230" y="432" width="14" height="7" />
          <path pathLength="1" d="M178 392v24m-5-6 5 6 5-6M200 386v30m-5-6 5 6 5-6M222 392v24m-5-6 5 6 5-6" />
        </g>

        {/* --- automatic rescue: the battery on the car roof --- */}
        <g className={hot('power-failure')}>
          <rect pathLength="1" x="152" y="232" width="38" height="18" rx="2" />
          <rect pathLength="1" x="190" y="238" width="3" height="6" />
          <path pathLength="1" d="M173 235l-5 8h5l-3 6" />
          <path pathLength="1" className="sd-dash" d="M160 232V120h-8V74" />
        </g>

        {/* --- overspeed governor, its rope, and the jaws on the rails --- */}
        <g className={hot('emergency-braking')}>
          <circle pathLength="1" cx="286" cy="56" r="10" />
          <circle pathLength="1" cx="286" cy="56" r="2" />
          <line pathLength="1" x1="286" y1="66" x2="286" y2="595" />
          <circle pathLength="1" cx="286" cy="602" r="7" />
          <line pathLength="1" x1="254" y1="300" x2="286" y2="300" />
          <path pathLength="1" d="M124 408l13 9-13 9Z" />
          <path pathLength="1" d="M276 408l-13 9 13 9Z" />
        </g>

        {/* --- firefighter recall: down to the ground landing --- */}
        <g className={hot('fire-mode')}>
          <line pathLength="1" x1="56" y1="612" x2="100" y2="612" />
          <circle pathLength="1" cx="44" cy="608" r="11" />
          <path pathLength="1" className="sd-dash" d="M200 446v128" />
          <path pathLength="1" d="M193 566l7 9 7-9" />
          <path pathLength="1" d="M74 566c1 5 7 8 7 15a7 7 0 0 1-14 0c0-3 1.4-5 3-6.5 0.3 2.2 1.3 3.5 2.6 4.1-0.6-4.4 0.1-9.4 1.4-12.6Z" />
        </g>

        {/* --- door light curtain: beams across the opening --- */}
        <g className={hot('door-protection')}>
          <rect pathLength="1" x="168" y="270" width="3" height="150" />
          <rect pathLength="1" x="229" y="270" width="3" height="150" />
          {[285, 305, 325, 345, 365, 385, 405].map((y, i) => (
            <line key={y} className="sd-beam" style={{ '--b': i }} x1="172" y1={y} x2="228" y2={y} />
          ))}
        </g>

        {/* --- alarm and intercom: the panel in the car, calling out --- */}
        <g className={hot('emergency-comms')}>
          <rect pathLength="1" x="238" y="318" width="10" height="50" rx="1.5" />
          <circle pathLength="1" cx="243" cy="328" r="2" />
          <circle pathLength="1" cx="243" cy="343" r="2" />
          <path pathLength="1" className="sd-wave" style={{ '--b': 0 }} d="M254 335a11 11 0 0 1 0 16" />
          <path pathLength="1" className="sd-wave" style={{ '--b': 1 }} d="M259 329a19 19 0 0 1 0 28" />
          <path pathLength="1" className="sd-wave" style={{ '--b': 2 }} d="M264 323a27 27 0 0 1 0 40" />
        </g>

        {/* --- structural and seismic restraint: the rail brackets --- */}
        <g className={hot('seismic')}>
          {[110, 180, 490, 560].map((y) => (
            <g key={y}>
              <path pathLength="1" d={`M100 ${y}h24M100 ${y + 12}l24-12`} />
              <path pathLength="1" d={`M300 ${y}h-24M300 ${y + 12}l-24-12`} />
              <rect pathLength="1" x="120" y={y - 4} width="8" height="8" />
              <rect pathLength="1" x="272" y={y - 4} width="8" height="8" />
            </g>
          ))}
        </g>

        {ring && <circle key={active} className="sd-ring" cx={ring[0]} cy={ring[1]} r="7" />}
      </g>
    </svg>
  )
}
