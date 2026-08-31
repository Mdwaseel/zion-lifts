import { chromium } from 'playwright'
const b = await chromium.launch()
for (const [w, h] of [[1440, 900], [1280, 800], [1920, 1080], [1024, 700]]) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  await p.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
  await p.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(1700)
  const box = await p.evaluate(() => {
    const el = document.querySelector('.zc__scroller')
    return { top: el.getBoundingClientRect().top + scrollY, h: el.offsetHeight, vh: innerHeight,
             pinned: el.classList.contains('is-pinned') }
  })
  const runway = box.h - box.vh
  await p.evaluate((y) => scrollTo(0, y), Math.round(box.top + runway * 0.28))
  await p.waitForTimeout(500)
  const fit = await p.evaluate(() => {
    const f = document.querySelector('.zc__frame').getBoundingClientRect()
    return { top: Math.round(f.top), bottom: Math.round(f.bottom), h: Math.round(f.height), vh: innerHeight }
  })
  const clipped = fit.top < 0 || fit.bottom > fit.vh
  console.log(`${w}x${h} pinned=${box.pinned} frame ${fit.h}px at [${fit.top},${fit.bottom}] vh=${fit.vh} ${clipped ? 'CLIPPED' : 'fits'}`)
  if (w === 1440) await p.screenshot({ path: 'C:/Users/Mohd/AppData/Local/Temp/claude/d--Projects-Zion-Lifts/7ccdca15-a9ce-4d60-bc16-08f19b29d5bf/scratchpad/zc/pinned.png' })
  await p.close()
}
await b.close()
