/** Reports the rendered box of selectors, to catch collapsed layouts. */
import { chromium } from 'playwright'

const BASE = process.env.BASE_URL ?? 'http://localhost:5173'
const route = process.argv[2] ?? '/'
const selectors = process.argv.slice(3)

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
// Must run before the app boots — see the note in shots.mjs.
await page.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
await page.goto(BASE + route, { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(1500)

// walk the whole page so lazy images and reveals trigger
const height = await page.evaluate(() => document.body.scrollHeight)
for (let y = 0; y < height; y += 300) {
  await page.evaluate((v) => window.scrollTo(0, v), y)
  await page.waitForTimeout(140)
}
await page.waitForTimeout(800)

for (const sel of selectors) {
  const info = await page.evaluate((s) => {
    const el = document.querySelector(s)
    if (!el) return null
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    const img = el.querySelector('img')
    return {
      w: Math.round(r.width),
      h: Math.round(r.height),
      display: cs.display,
      clip: cs.clipPath,
      opacity: cs.opacity,
      img: img ? { w: Math.round(img.getBoundingClientRect().width), h: Math.round(img.getBoundingClientRect().height), src: img.currentSrc?.split('/').pop() } : null,
    }
  }, sel)
  console.log(sel.padEnd(34), info ? JSON.stringify(info) : 'NOT FOUND')
}

await browser.close()
