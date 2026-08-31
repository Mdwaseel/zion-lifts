/** Line marks used across the site. Deliberately thin and uniform. */

const base = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export function Arrow({ size = 16, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

export function ArrowDown({ size = 16, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </svg>
  )
}

export function Plus({ size = 16, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function Close({ size = 16, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  )
}

export function Check({ size = 16, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M4 12.5l5 5L20 6.5" />
    </svg>
  )
}

/* --- service pillar marks ------------------------------------------------ */

export function Wrench({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M15.5 3.5a5 5 0 00-6.1 6.4L3.6 15.7a2 2 0 102.8 2.8l5.8-5.8a5 5 0 006.4-6.1l-2.9 2.9-2.6-.6-.6-2.6z" />
    </svg>
  )
}

export function Calendar({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <rect x="3.5" y="5" width="17" height="15.5" rx="1.5" />
      <path d="M3.5 9.5h17M8 3v4M16 3v4" />
    </svg>
  )
}

export function Bolt({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M13.5 2.5L5 13.5h6L10.5 21.5 19 10.5h-6z" />
    </svg>
  )
}

export function Refresh({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M20.5 12a8.5 8.5 0 11-2.6-6.1" />
      <path d="M20.5 3.5V9H15" />
    </svg>
  )
}

export function Box({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 2.8l8.5 4.6v9.2L12 21.2l-8.5-4.6V7.4z" />
      <path d="M3.5 7.4L12 12l8.5-4.6M12 12v9.2" />
    </svg>
  )
}

export function Phone({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M6.5 3.5h3l1.5 4-2 1.5a12 12 0 006 6l1.5-2 4 1.5v3a2 2 0 01-2.2 2A17.5 17.5 0 014.5 5.7 2 2 0 016.5 3.5z" />
    </svg>
  )
}

export function Chat({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M20.5 12.5a7.5 7.5 0 01-10.8 6.7L4 20.5l1.4-5.5A7.5 7.5 0 1120.5 12.5z" />
    </svg>
  )
}

export function Mail({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <rect x="2.8" y="5" width="18.4" height="14" rx="1.6" />
      <path d="M3.2 6.4L12 12.8l8.8-6.4" />
    </svg>
  )
}

export function Shield({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 2.7l7.5 3v6c0 4.4-3 8.3-7.5 9.6-4.5-1.3-7.5-5.2-7.5-9.6v-6z" />
      <path d="M9 12l2.2 2.2L15.5 10" />
    </svg>
  )
}

export function Pin({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 21.5s7-6 7-11a7 7 0 10-14 0c0 5 7 11 7 11z" />
      <circle cx="12" cy="10.5" r="2.6" />
    </svg>
  )
}

/* --- lift-system marks ---------------------------------------------------- */
/* One per system in the collection, drawn on the same 24px grid and stroke as
   everything else so the set reads as one family rather than nine borrowings. */

export function HomeMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M4 10.5L12 4l8 6.5V20H4z" />
      <path d="M9.6 20v-5.2h4.8V20" />
    </svg>
  )
}

export function CapsuleMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M7.5 9a4.5 4.5 0 019 0v11h-9z" />
      <path d="M12 9.5v10" />
    </svg>
  )
}

export function MrlMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <rect x="4.5" y="4.5" width="15" height="15" rx="1" />
      <path d="M12 4.5v15" />
      <path d="M8.2 10.4L9.9 8.6l1.7 1.8M12.4 13.6l1.7 1.8 1.7-1.8" />
    </svg>
  )
}

export function DropletMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 3.5s5.5 6 5.5 9.6a5.5 5.5 0 11-11 0C6.5 9.5 12 3.5 12 3.5z" />
    </svg>
  )
}

export function UsersMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <circle cx="8.6" cy="8" r="2.6" />
      <circle cx="16" cy="9.2" r="2.1" />
      <path d="M4 19.5c0-2.6 2-4.4 4.6-4.4s4.6 1.8 4.6 4.4" />
      <path d="M15 15.4c2.4 0 4 1.6 4 4.1" />
    </svg>
  )
}

export function CrossMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <rect x="4.5" y="4.5" width="15" height="15" rx="1.5" />
      <path d="M12 8.6v6.8M8.6 12h6.8" />
    </svg>
  )
}

export function PackageMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 3.6l7.5 4.1v8.6L12 20.4 4.5 16.3V7.7z" />
      <path d="M4.7 7.8L12 11.8l7.3-4M12 11.8v8.5" />
    </svg>
  )
}

export function DumbwaiterMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <rect x="4.5" y="4.5" width="15" height="15" rx="1" />
      <rect x="8.4" y="8.4" width="7.2" height="7.2" rx="0.6" />
    </svg>
  )
}

export function CarMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M4 15.4v-2l1.7-4.2A2 2 0 017.6 8h8.8a2 2 0 011.9 1.2L20 13.4v2" />
      <path d="M4 15.4h16v2.4h-2.6M4 15.4v2.4h2.6" />
      <circle cx="8" cy="17.8" r="1.4" />
      <circle cx="16" cy="17.8" r="1.4" />
    </svg>
  )
}

export function CogMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <circle cx="12" cy="12" r="7.7" />
      <circle cx="12" cy="12" r="3.1" />
      <path d="M12 4.3v1.9M12 17.8v1.9M19.7 12h-1.9M6.2 12H4.3M17.4 6.6l-1.3 1.3M7.9 16.1l-1.3 1.3M17.4 17.4l-1.3-1.3M7.9 7.9L6.6 6.6" />
    </svg>
  )
}

export function LayersMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M12 3.8l8 4.1-8 4.1-8-4.1z" />
      <path d="M4 12.2l8 4.1 8-4.1M4 16.3l8 4.1 8-4.1" />
    </svg>
  )
}

export function GaugeMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <circle cx="12" cy="12" r="8.2" />
      <path d="M12 12l3.4-3.4" />
      <path d="M12 3.8v1.4M20.2 12h-1.4M12 20.2v-1.4M3.8 12h1.4" />
    </svg>
  )
}

export function UpDownMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M8.4 20V4.6M8.4 4.6L5.3 7.7M8.4 4.6l3.1 3.1" />
      <path d="M15.6 4v15.4M15.6 19.4l3.1-3.1M15.6 19.4l-3.1-3.1" />
    </svg>
  )
}

export function CrosshairMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <circle cx="12" cy="12" r="7.4" />
      <circle cx="12" cy="12" r="2.6" />
      <path d="M12 1.9v3.2M12 18.9v3.2M22.1 12h-3.2M5.1 12H1.9" />
    </svg>
  )
}

export function WaveMark({ size = 22, ...rest }) {
  return (
    <svg {...base} width={size} height={size} {...rest}>
      <path d="M2.6 12h1.6M7 8.4v7.2M10.2 5.6v12.8M13.4 9.6v4.8M16.6 7.2v9.6M19.8 10.4v3.2M22.4 12h-0.8" />
    </svg>
  )
}

/** slug -> mark, for the collection selector */
export const LIFT_ICONS = {
  'home-elevator': HomeMark,
  'capsule-elevator': CapsuleMark,
  'mrl-traction': MrlMark,
  'hydraulic-elevator': DropletMark,
  'passenger-elevator': UsersMark,
  'hospital-elevator': CrossMark,
  'goods-elevator': PackageMark,
  dumbwaiter: DumbwaiterMark,
  'car-stacker': CarMark,
}

export const PILLAR_ICONS = {
  wrench: Wrench,
  calendar: Calendar,
  bolt: Bolt,
  refresh: Refresh,
  box: Box,
  shield: Shield,
}
