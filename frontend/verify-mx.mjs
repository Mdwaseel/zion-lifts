/** Checks every product state in the Enter the machine explorer. */
import { chromium } from 'playwright'
const b = await chromium.launch()
const errs = []

const EXPECT = [
  ['Home Elevator', '/media/frames/lacheta-lobby.jpg', '/lifts/home-elevator'],
  ['Capsule Elevator', '/media/products/capsule-02.jpg', '/lifts/capsule-elevator'],
  ['MRL Traction Elevator', '/media/interiors/interior-05.jpg', '/lifts/mrl-traction'],
  ['Hydraulic Elevator', '/media/interiors/interior-10.jpg', '/lifts/hydraulic-elevator'],
  ['Commercial Passenger Elevator', '/media/frames/chath-entrance.jpg', '/lifts/passenger-elevator'],
  ['Hospital Elevator', '/media/frames/owaisi-doors.jpg', '/lifts/hospital-elevator'],
  ['Goods & Freight Elevator', '/media/frames/kashi-structure.jpg', '/lifts/goods-elevator'],
  ['Dumbwaiter', '/media/products/dumbwaiter-02.jpg', '/lifts/dumbwaiter'],
  ['Car Stacker & Parking Lift', '/media/products/car-stacker-02.jpg', '/lifts/car-stacker'],
]

async function run(label, opts) {
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, ...opts })
  p.on('pageerror', (e) => errs.push(`${label} :: ${e.message}`))
  p.on('console', (m) => m.type() === 'error' && errs.push(`${label} :: ${m.text()}`))
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1600)
  await p.locator('.mx').scrollIntoViewIfNeeded()
  await p.waitForTimeout(500)

  const read = () => p.evaluate(() => {
    const shot = [...document.querySelectorAll('.mx__shot')].find((e) => e.classList.contains('is-on'))
    const img = shot?.querySelector('img')
    return {
      row: document.querySelector('.mx__tab.is-on .mx__tab-name')?.textContent,
      title: document.querySelector('.mx__name')?.textContent,
      img: (img?.getAttribute('src') || '').split('?')[0],
      alt: img?.getAttribute('alt'),
      cta: document.querySelector('.mx__cta span')?.textContent,
      href: document.querySelector('.mx__cta')?.getAttribute('href'),
      dot: [...document.querySelectorAll('.mx__dot')].findIndex((e) => e.classList.contains('is-on')),
      dots: document.querySelectorAll('.mx__dot').length,
      icon: !!document.querySelector('.mx__panel-icon svg'),
      specs: [...document.querySelectorAll('.mx__spec')].map((e) => e.querySelector('dt').textContent.trim() + '=' + e.querySelector('dd').textContent.trim()),
      specIcons: document.querySelectorAll('.mx__spec dt svg').length,
    }
  })

  const bad = []
  for (let i = 0; i < EXPECT.length; i++) {
    const [name, img, href] = EXPECT[i]
    await p.locator('.mx__tab').nth(i).click()
    await p.waitForTimeout(300)
    const r = await read()
    const ok = r.row === name && r.title === name && r.href === href && r.dot === i &&
               r.dots === 9 && r.icon && r.specs.length === 4 && r.specIcons === 4 &&
               r.img.includes(img.replace('.jpg', '')) && r.alt === `${name} by Zion Lifts`
    if (!ok) bad.push(`  ${i} ${name}\n    ${JSON.stringify(r)}\n    wanted img~${img} href=${href} dot=${i}`)
  }
  console.log(`${label}: ${bad.length ? 'FAILURES\n' + bad.join('\n') : 'all 9 correct (row/title/image/alt/icon/4 specs+icons/CTA/route/dot)'}`)

  // dots must drive the same state
  await p.locator('.mx__dot').nth(4).click()
  await p.waitForTimeout(300)
  const viaDot = await read()
  console.log(`  dot 5 -> ${viaDot.title} | ${viaDot.cta} -> ${viaDot.href} | row=${viaDot.row}`)

  // keyboard
  await p.locator('.mx__tab.is-on').focus()
  await p.keyboard.press('ArrowDown')
  await p.waitForTimeout(250)
  const k1 = await read()
  await p.keyboard.press('End')
  await p.waitForTimeout(250)
  const k2 = await read()
  console.log(`  keyboard: ArrowDown -> ${k1.title} | End -> ${k2.title}`)
  return p
}

const p1 = await run('normal')
// autoplay only when left alone
await p1.waitForTimeout(6200)
const auto = await p1.evaluate(() => document.querySelector('.mx__name')?.textContent)
console.log(`  autoplay after idle: ${auto}`)
await p1.close()

const p2 = await run('reduced-motion', { reducedMotion: 'reduce' })
const before = await p2.evaluate(() => document.querySelector('.mx__name')?.textContent)
await p2.waitForTimeout(6500)
const after = await p2.evaluate(() => document.querySelector('.mx__name')?.textContent)
console.log(`  reduced motion autoplay: ${before} -> ${after} (${before === after ? 'held, correct' : 'ADVANCED — should not'})`)
await p2.close()

console.log(errs.length ? `\nERRORS:\n${errs.join('\n')}` : '\nno console errors')
await b.close()
