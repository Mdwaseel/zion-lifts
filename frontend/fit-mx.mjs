/** Confirms the pinned frame fits a single screen at every desktop size. */
import { chromium } from 'playwright'
const b = await chromium.launch()
for (const [w, h] of [[1920, 1080], [1440, 900], [1440, 800], [1280, 800], [1366, 768], [1200, 700], [1280, 720], [1600, 900]]) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1700)
  const box = await p.evaluate(() => {
    const el = document.querySelector('.mx__scroller')
    return { top: el.getBoundingClientRect().top + scrollY, h: el.offsetHeight, vh: innerHeight,
             pinned: el.classList.contains('is-pinned') }
  })
  await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + (box.h - box.vh) * 0.3))
  await p.waitForTimeout(500)
  const f = await p.evaluate(() => {
    const r = document.querySelector('.mx__frame').getBoundingClientRect()
    const st = document.querySelector('.mx__stage').getBoundingClientRect()
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height),
             sw: Math.round(st.width), sh: Math.round(st.height), vh: innerHeight }
  })
  const fits = f.top >= 0 && f.bottom <= f.vh
  console.log(`${w}x${h} pinned=${box.pinned} frame ${f.h}px [${f.top},${f.bottom}] vh=${f.vh} ${fits ? 'FITS' : 'OVERFLOWS'} | photo ${f.sw}x${f.sh}`)
  await p.close()
}
await b.close()
