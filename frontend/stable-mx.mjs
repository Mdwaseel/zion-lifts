/** The pinned frame must be one constant height across all nine systems, and
 *  must never exceed the viewport. */
import { chromium } from 'playwright'
const b = await chromium.launch()
let bad = 0
for (const [w, h] of [[1920, 1080], [1600, 900], [1440, 900], [1440, 800], [1366, 768], [1280, 800], [1280, 720], [1200, 700]]) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1800)
  const sc = await p.evaluate(() => { const e = document.querySelector('.mx__scroller'); return { top: e.getBoundingClientRect().top + scrollY, h: e.offsetHeight, vh: innerHeight } })
  await p.evaluate((y) => scrollTo(0, y), Math.round(sc.top + (sc.h - sc.vh) * 0.05))
  await p.waitForTimeout(600)
  const heights = [], overflow = []
  for (let i = 0; i < 9; i++) {
    await p.locator('.mx__tab').nth(i).click()
    await p.waitForTimeout(320)
    const r = await p.evaluate(() => {
      const f = document.querySelector('.mx__frame').getBoundingClientRect()
      const panel = document.querySelector('.mx__panel')
      return { h: Math.round(f.height), over: panel.scrollHeight - panel.clientHeight,
               fits: f.top >= -1 && f.bottom <= innerHeight + 1,
               name: document.querySelector('.mx__name').textContent.slice(0, 22) }
    })
    heights.push(r.h)
    if (r.over > 1 || !r.fits) overflow.push(`${r.name}(h=${r.h} over=${r.over} fits=${r.fits})`)
  }
  const uniq = [...new Set(heights)]
  const ok = uniq.length === 1 && overflow.length === 0
  if (!ok) bad++
  console.log(`${w}x${h} ${ok ? 'OK' : 'PROBLEM'} heights=${uniq.join('/')} ${overflow.length ? '| ' + overflow.join(' ') : ''}`)
  await p.close()
}
console.log(bad ? `\n${bad} viewport(s) with problems` : '\nconstant height and fits everywhere')
await b.close()
