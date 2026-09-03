/**
 * Helpers for the responsive asset tree built by `assets-src/*.py`.
 *
 * Every optimised image ships as `<name>-<width>.webp` alongside a `<name>.jpg`
 * fallback, so a srcset can be derived from the .jpg path alone.
 */

const WIDTHS_BY_DIR = {
  interiors: [480, 960, 1600],
  contexts: [480, 960, 1600, 2400],
  cabin: [480, 960, 1600],
  engineering: [480, 960, 1600],
  finishes: [480, 960, 1600],
  frames: [480, 960, 1600],
  process: [480, 960, 1600],
  products: [480, 960, 1600, 2400],
  projects: [480, 960, 1600, 2400],
  sourced: [640, 1280, 1920],
}

/** Splits "/media/frames/lekha-cabin.jpg" into its directory and stem. */
function parse(src) {
  if (!src || typeof src !== 'string') return null
  const m = src.match(/^(.*\/media\/([^/]+))\/([^/]+)\.(jpg|jpeg|png|webp)$/i)
  if (!m) return null
  return { dir: m[1], bucket: m[2], stem: m[3] }
}

export function srcSet(src) {
  const p = parse(src)
  if (!p) return undefined
  const widths = WIDTHS_BY_DIR[p.bucket]
  if (!widths) return undefined
  return widths.map((w) => `${p.dir}/${p.stem}-${w}.webp ${w}w`).join(', ')
}

/** A small blurred stand-in used while the full image decodes. */
export function tinySrc(src) {
  const p = parse(src)
  if (!p) return undefined
  const widths = WIDTHS_BY_DIR[p.bucket]
  return widths ? `${p.dir}/${p.stem}-${widths[0]}.webp` : undefined
}

export function posterFor(project) {
  return project?.poster_url || project?.hero_image_url || undefined
}

/** Formats "1,750" style figures from a raw number. */
export function formatCount(n) {
  return new Intl.NumberFormat('en-IN').format(n)
}

/** Splits a stat value like "1,750+" into { number, suffix } for count-up. */
export function parseStat(value) {
  const m = String(value ?? '').match(/^([\d,.]+)(.*)$/)
  if (!m) return { number: null, suffix: String(value ?? '') }
  const number = Number(m[1].replace(/,/g, ''))
  return Number.isFinite(number) ? { number, suffix: m[2] } : { number: null, suffix: value }
}

export function telHref(phone) {
  return `tel:${String(phone ?? '').replace(/[^\d+]/g, '')}`
}

export function whatsappHref(number, message) {
  const digits = String(number ?? '').replace(/\D/g, '')
  const text = message ? `?text=${encodeURIComponent(message)}` : ''
  return `https://wa.me/${digits}${text}`
}
