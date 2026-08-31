/** Captures the Engineering section across the sizes the brief lists. */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
const OUT = 'C:/Users/Mohd/AppData/Local/Temp/claude/d--Projects-Zion-Lifts/7ccdca15-a9ce-4d60-bc16-08f19b29d5bf/scratchpad/eng'
mkdirSync(OUT, { recursive: true })
const sizes = process.argv.slice(2).length
  ? process.argv.slice(2).map((s) => s.split('x').map(Number))
  : [[1440, 900], [1600, 900], [1920, 1080], [1024, 1366], [834, 1194], [390, 844], [375, 812]]
const b = await chromium.launch()
const errs = []
for (const [w, h] of sizes) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  p.on('pageerror', (e) => errs.push(`${w} :: ${e.message}`))
  p.on('console', (m) => m.type() === 'error' && errs.push(`${w} :: ${m.text()}`))
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1900)
  const top = await p.evaluate(() => document.querySelector('.eng').getBoundingClientRect().top + scrollY)
  await p.evaluate((y) => scrollTo(0, y), Math.round(top - 60))
  await p.waitForTimeout(1200)
  await p.screenshot({ path: path.join(OUT, `eng-${w}x${h}.png`) })
  const ov = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  const clip = await p.evaluate(() => {
    const out = []
    for (const s of ['.eng__title', '.eng__lead', '.eng__line', '.eng__body', '.eng__label']) {
      for (const el of document.querySelectorAll(s)) {
        if (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2) out.push(s)
      }
    }
    return [...new Set(out)]
  })
  console.log(`${w}x${h} overflow=${ov}px clipped=${JSON.stringify(clip)}`)
  await p.close()
}
console.log(errs.length ? `\nERRORS:\n${errs.join('\n')}` : '\nno console errors')
await b.close()
