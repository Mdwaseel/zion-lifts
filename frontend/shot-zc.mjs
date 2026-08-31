/** Captures the Zion Collection section across widths and product states. */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
const OUT = process.env.SHOT_DIR ?? 'C:/Users/Mohd/AppData/Local/Temp/claude/d--Projects-Zion-Lifts/7ccdca15-a9ce-4d60-bc16-08f19b29d5bf/scratchpad/zc'
const BASE = process.env.BASE_URL ?? 'http://localhost:5173'
const widths = process.argv.slice(2).map(Number).filter(Boolean)
mkdirSync(OUT, { recursive: true })
const b = await chromium.launch()
const errs = []
for (const w of (widths.length ? widths : [1440])) {
  const p = await b.newPage({ viewport: { width: w, height: w < 700 ? 844 : 1000 } })
  p.on('pageerror', (e) => errs.push(`${w} :: ${e.message}`))
  p.on('console', (m) => m.type() === 'error' && errs.push(`${w} :: ${m.text()}`))
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto(BASE, { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1800)
  // scroll so the section clears the fixed nav, then shoot the viewport —
  // an element screenshot would still have the nav composited over it
  const top = await p.evaluate(() => document.querySelector('.zc').getBoundingClientRect().top + scrollY)
  await p.evaluate((y) => scrollTo(0, y), Math.round(top - 8))
  await p.waitForTimeout(900)
  await p.screenshot({ path: path.join(OUT, `zc-${w}-a.png`) })
  await p.evaluate((y) => scrollTo(0, y), Math.round(top - 8 + (w < 700 ? 700 : 860)))
  await p.waitForTimeout(700)
  await p.screenshot({ path: path.join(OUT, `zc-${w}-b.png`) })
  const ov = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  console.log(`${w}px  overflow=${ov}px`)
  await p.close()
}
console.log(errs.length ? `\nERRORS:\n${errs.join('\n')}` : '\nno console errors')
await b.close()
