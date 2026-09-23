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

// The artwork is very slightly wider than tall. Stating both dimensions keeps
// it from distorting and reserves the space before it loads.
const ASPECT = 96 / 89

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
