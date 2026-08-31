/**
 * Captures the pinned contexts section at each of its six states.
 *
 *   node shot-world.mjs            # 1440
 *   node shot-world.mjs 1920 390   # any list of widths
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const OUT =
  process.env.SHOT_DIR ??
  'C:/Users/Mohd/AppData/Local/Temp/claude/d--Projects-Zion-Lifts/7ccdca15-a9ce-4d60-bc16-08f19b29d5bf/scratchpad/world'
const BASE = process.env.BASE_URL ?? 'http://localhost:5173'
const widths = process.argv.slice(2).map(Number).filter(Boolean)
const targets = widths.length ? widths : [1440]

mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch()
const errors = []

for (const w of targets) {
  const page = await browser.newPage({
    viewport: { width: w, height: w < 700 ? 844 : 900 },
    deviceScaleFactor: 1,
  })
  page.on('console', (m) => m.type() === 'error' && errors.push(`${w} :: ${m.text()}`))
  page.on('pageerror', (e) => errors.push(`${w} :: ${e.message}`))
  await page.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2000)

  const box = await page.evaluate(() => {
    const el = document.querySelector('.world')
    const r = el.getBoundingClientRect()
    return { top: r.top + window.scrollY, height: el.offsetHeight, vh: window.innerHeight }
  })
  const runway = box.height - box.vh

  for (let i = 0; i < 6; i++) {
    // land mid-slot so each capture is a held state, not a crossfade
    const y = Math.round(box.top + runway * ((i + 0.45) / 6))
    await page.evaluate((v) => window.scrollTo(0, v), y)
    await page.waitForTimeout(700)
    const file = path.join(OUT, `w${w}-${i + 1}.png`)
    await page.screenshot({ path: file })
    console.log('shot', path.basename(file))
  }

  // horizontal overflow check
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  console.log(`  ${w}px horizontal overflow: ${overflow}px`)
  await page.close()
}

console.log(errors.length ? `\nconsole errors:\n${errors.join('\n')}` : '\nno console errors')
await browser.close()
