/** Confirms the collection pins, advances through all nine, and releases. */
import { chromium } from 'playwright'
const b = await chromium.launch()
const errs = []

async function run(label, opts) {
  const p = await b.newPage({ viewport: { width: 1440, height: 900 }, ...opts })
  p.on('pageerror', (e) => errs.push(`${label} :: ${e.message}`))
  p.on('console', (m) => m.type() === 'error' && errs.push(`${label} :: ${m.text()}`))
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1800)
  const box = await p.evaluate(() => {
    const el = document.querySelector('.zc__scroller')
    return { top: el.getBoundingClientRect().top + scrollY, h: el.offsetHeight, vh: innerHeight,
             pinned: el.classList.contains('is-pinned') }
  })
  const runway = box.h - box.vh
  console.log(`${label}: pinned=${box.pinned} scrollerH=${box.h}px runway=${runway}px`)
  const name = () => p.evaluate(() => document.querySelector('.zc__info-name')?.textContent)

  const down = []
  for (let i = 0; i < 9; i++) {
    await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + runway * ((i + 0.5) / 9)))
    await p.waitForTimeout(320)
    down.push(await name())
  }
  const up = []
  for (let i = 8; i >= 0; i--) {
    await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + runway * ((i + 0.5) / 9)))
    await p.waitForTimeout(320)
    up.push(await name())
  }
  await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + box.h + 300))
  await p.waitForTimeout(500)
  const after = await p.evaluate(() => {
    const pin = document.querySelector('.zc__pin').getBoundingClientRect()
    const proof = document.querySelector('.zc__proof').getBoundingClientRect()
    return { released: pin.bottom < window.innerHeight, proofTop: Math.round(proof.top) }
  })
  console.log(`  down: ${down.join(' → ')}`)
  console.log(`  up:   ${up.join(' → ')}`)
  console.log(`  after runway: released=${after.released} proofTop=${after.proofTop}`)
  await p.close()
}

await run('desktop')
await run('reduced-motion', { reducedMotion: 'reduce' })
const p = await b.newPage({ viewport: { width: 768, height: 1000 } })
await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
await p.waitForTimeout(1800)
console.log('tablet 768: pinned =', await p.evaluate(() => document.querySelector('.zc__scroller').classList.contains('is-pinned')))
await p.close()
console.log(errs.length ? `\nERRORS:\n${errs.join('\n')}` : '\nno console errors')
await b.close()
