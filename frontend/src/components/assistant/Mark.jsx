/**
 * The assistant's mascot.
 *
 * Built by `assets-src/build_chatbot.py` from the master in `brand-src/`, at
 * 64/96/128px — two and three times the sizes it is drawn at, so a retina
 * screen has a real pixel per device pixel and nothing is upscaled. The master
 * itself is 1.1 MB and is never shipped.
 *
 * Always decorative: everywhere it appears there is already a visible "Ask
 * Zion" label beside it, so an alt text would make a screen reader say the name
 * twice.
 */

const BASE = '/media/chatbot'

// The trimmed master, 1402x1102. Stating both dimensions reserves the right
// space before the image loads, so the launcher does not shift as it arrives.
// This has to track the artwork: `build_chatbot.py` prints the master's size,
// and the mascot sits in the Zion triangle now, which is wider than the round
// mark it replaced.
const ASPECT = 1402 / 1102

export default function Mark({ size = 26, className }) {
  const height = Math.round(size / ASPECT)

  return (
    <picture className={className}>
      <source
        type="image/webp"
        srcSet={`${BASE}/chatbot-64.webp 64w, ${BASE}/chatbot-96.webp 96w, ${BASE}/chatbot-128.webp 128w`}
        sizes={`${size}px`}
      />
      <img
        src={`${BASE}/chatbot.png`}
        alt=""
        width={size}
        height={height}
        decoding="async"
        draggable="false"
      />
    </picture>
  )
}
