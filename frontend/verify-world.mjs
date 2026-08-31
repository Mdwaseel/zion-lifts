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
    const el = document.querySelector('.world')
    return { top: el.getBoundingClientRect().top + scrollY, h: el.offsetHeight, vh: innerHeight }
  })
  const runway = box.h - box.vh
  const read = () => p.evaluate(() => {
    const on = document.querySelector('.world__rail li.is-on .world__rail-label')
    const pin = document.querySelector('.world__pin').getBoundingClientRect()
    const vis = [...document.querySelectorAll('.world__layer')].map((e) => +(+e.style.opacity).toFixed(2))
    return { active: on?.textContent ?? null, pinTop: Math.round(pin.top), vis }
  })

  const down = []
  for (let i = 0; i < 6; i++) {
    await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + runway * ((i + 0.45) / 6)))
    await p.waitForTimeout(450)
    down.push((await read()).active)
  }
  const up = []
  for (let i = 5; i >= 0; i--) {
    await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + runway * ((i + 0.45) / 6)))
    await p.waitForTimeout(450)
    up.push((await read()).active)
  }
  // past the end: must unpin and the next section must be in view
  await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + box.h + 200))
  await p.waitForTimeout(500)
  const after = await p.evaluate(() => {
    const pin = document.querySelector('.world__pin').getBoundingClientRect()
    const next = document.querySelector('.zc')
    return { pinTop: Math.round(pin.top), unpinned: pin.top < -10, nextTop: next ? Math.round(next.getBoundingClientRect().top) : null }
  })
  console.log(`${label}\n  down: ${down.join(' → ')}\n  up:   ${up.join(' → ')}\n  after end: pinTop=${after.pinTop} unpinned=${after.unpinned} nextSectionTop=${after.nextTop}`)
  await p.close()
}

await run('normal')
await run('reduced-motion', { reducedMotion: 'reduce' })
console.log(errs.length ? `\nERRORS:\n${errs.join('\n')}` : '\nno console errors')
await b.close()
