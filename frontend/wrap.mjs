import { chromium } from 'playwright'
const b = await chromium.launch()
for (const [w, h] of [[1920, 1080], [1600, 900], [1440, 900], [1366, 768], [1280, 800], [1200, 700]]) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1700)
  const sc = await p.evaluate(() => { const e = document.querySelector('.mx__scroller'); return { top: e.getBoundingClientRect().top + scrollY, h: e.offsetHeight, vh: innerHeight } })
  await p.evaluate((y) => scrollTo(0, y), Math.round(sc.top + (sc.h - sc.vh) * 0.3))
  await p.waitForTimeout(400)
  const r = await p.evaluate(() => {
    const names = [...document.querySelectorAll('.mx__tab-name')]
    const f = document.querySelector('.mx__frame').getBoundingClientRect()
    const st = document.querySelector('.mx__stage').getBoundingClientRect()
    return { clipped: names.filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.textContent),
      label: getComputedStyle(names[0]).fontSize,
      title: getComputedStyle(document.querySelector('.mx__name')).fontSize,
      body: getComputedStyle(document.querySelector('.mx__summary')).fontSize,
      frame: Math.round(f.height), fits: f.top >= -1 && f.bottom <= innerHeight + 1,
      photo: `${Math.round(st.width)}x${Math.round(st.height)}` }
  })
  console.log(`${w}x${h} label=${r.label} title=${r.title} body=${r.body} frame=${r.frame} fits=${r.fits} photo=${r.photo} clipped=${JSON.stringify(r.clipped)}`)
  await p.close()
}
await b.close()
