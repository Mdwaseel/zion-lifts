/** Exercises the collection selector: pointer, keyboard, links, reduced motion. */
import { chromium } from 'playwright'
const b = await chromium.launch()
const errs = []

async function run(label, opts) {
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, ...opts })
  p.on('pageerror', (e) => errs.push(`${label} :: ${e.message}`))
  p.on('console', (m) => m.type() === 'error' && errs.push(`${label} :: ${m.text()}`))
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1600)
  await p.locator('.zc').scrollIntoViewIfNeeded()
  await p.waitForTimeout(500)

  const read = () => p.evaluate(() => ({
    tab: document.querySelector('.zc__tab.is-on .zc__tab-name')?.textContent,
    n: document.querySelector('.zc__info-n')?.textContent,
    name: document.querySelector('.zc__info-name')?.textContent,
    cta: document.querySelector('.zc__info-cta')?.textContent.trim(),
    href: document.querySelector('.zc__info-cta')?.getAttribute('href'),
    specs: [...document.querySelectorAll('.zc__spec dt')].map((e) => e.textContent),
    shown: [...document.querySelectorAll('.zc__shot-layer')].findIndex((e) => e.classList.contains('is-on')),
  }))

  const n = await p.locator('.zc__tab').count()
  console.log(`${label}: ${n} systems`)
  const bad = []
  for (let i = 0; i < n; i++) {
    await p.locator('.zc__tab').nth(i).click()
    await p.waitForTimeout(260)
    const r = await read()
    const okSync = r.n === String(i + 1).padStart(2, '0') && r.shown === i && r.tab === r.name
    if (!okSync || !r.href || r.specs.length !== 4) bad.push(`${i}: ${JSON.stringify(r)}`)
  }
  console.log(bad.length ? `  OUT OF SYNC:\n   ${bad.join('\n   ')}` : '  all 9 in sync (tab / number / image / title / specs / link)')
  const sample = await read()
  console.log(`  last: ${sample.name} | ${sample.cta} -> ${sample.href} | specs ${sample.specs.join(', ')}`)

  // keyboard: arrow keys move selection
  await p.locator('.zc__tab').first().click()
  await p.locator('.zc__tab.is-on').focus()
  await p.keyboard.press('ArrowDown')
  await p.keyboard.press('ArrowDown')
  await p.waitForTimeout(250)
  const kb = await read()
  await p.keyboard.press('End')
  await p.waitForTimeout(250)
  const kbEnd = await read()
  console.log(`  keyboard: ArrowDown×2 -> ${kb.name} | End -> ${kbEnd.name}`)
  await p.close()
}

await run('normal')
await run('reduced-motion', { reducedMotion: 'reduce' })
console.log(errs.length ? `\nERRORS:\n${errs.join('\n')}` : '\nno console errors')
await b.close()
