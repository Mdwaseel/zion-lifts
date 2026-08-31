/**
 * Screenshot harness for reviewing the site while building it.
 *
 *   node shots.mjs                     # every route, desktop
 *   node shots.mjs /lifts /contact     # just these
 *   node shots.mjs --mobile /          # 390px viewport
 *   node shots.mjs --full /            # whole page, not just the fold
 *   node shots.mjs --scroll 3 /        # capture at N scroll positions
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const OUT =
  process.env.SHOT_DIR ??
  'C:/Users/Mohd/AppData/Local/Temp/claude/d--Projects-Zion-Lifts/7ccdca15-a9ce-4d60-bc16-08f19b29d5bf/scratchpad/shots'
const BASE = process.env.BASE_URL ?? 'http://localhost:5173'

const ALL = [
  '/', '/lifts', '/lifts/home-elevator', '/projects', '/projects/lekha-nilayam',
  '/about', '/contact', '/gallery', '/faq', '/journal',
  '/journal/how-to-size-a-home-lift', '/privacy',
]

const args = process.argv.slice(2)
const mobile = args.includes('--mobile')
const full = args.includes('--full')
const scrollIdx = args.indexOf('--scroll')
const scrollSteps = scrollIdx >= 0 ? Number(args[scrollIdx + 1]) : 0
const routes = args.filter((a) => a.startsWith('/'))
const targets = routes.length ? routes : ALL

mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({
  viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 900 },
  deviceScaleFactor: 1,
})

const errors = []
page.on('console', (m) => m.type() === 'error' && errors.push(`${page.url()} :: ${m.text()}`))
page.on('pageerror', (e) => errors.push(`${page.url()} :: ${e.message}`))

// Has to run before the app boots. Setting it after goto() only takes effect
// on the *next* navigation, which left the intro overlay fading over every
// shot — its wordmark and floor counter looked like stray page content.
await page.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))

for (const route of targets) {
  const slug = (route === '/' ? 'home' : route.slice(1).replace(/\//g, '_')) + (mobile ? '-m' : '')
  try {
    await page.goto(BASE + route, { waitUntil: 'networkidle', timeout: 45000 })
  } catch {
    await page.waitForTimeout(2500) // networkidle can hang on looping video
  }
  await page.waitForTimeout(900)

  if (scrollSteps > 0) {
    const height = await page.evaluate(() => document.body.scrollHeight)
    for (let i = 0; i < scrollSteps; i++) {
      const y = Math.round((height - 900) * (i / Math.max(1, scrollSteps - 1)))
      await page.evaluate((v) => window.scrollTo(0, v), y)
      await page.waitForTimeout(1100)
      await page.screenshot({ path: path.join(OUT, `${slug}-${i}.png`) })
    }
  } else {
    await page.screenshot({ path: path.join(OUT, `${slug}.png`), fullPage: full })
  }
  console.log('shot', route)
}

await browser.close()
if (errors.length) {
  console.log('\n--- console errors ---')
  for (const e of [...new Set(errors)].slice(0, 25)) console.log(e)
} else {
  console.log('\nno console errors')
}
