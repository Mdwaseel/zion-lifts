/** End-to-end check that the 3-step enquiry actually reaches Django. */
import { chromium } from 'playwright'

const BASE = process.env.BASE_URL ?? 'http://localhost:5173'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const errors = []
page.on('pageerror', (e) => errors.push(e.message))
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))

// Must run before the app boots — see the note in shots.mjs.
await page.addInitScript(() => sessionStorage.setItem('zion:intro-seen', '1'))
await page.goto(`${BASE}/contact`, { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(1600)

const step = () => page.locator('.enquiry__steps li.is-on button span:last-child').textContent()
const cont = async () => {
  await page.locator('.enquiry__actions button:has-text("Continue")').click()
  await page.waitForTimeout(500)
}

console.log('step ->', await step())
await page.locator('.enquiry .chip', { hasText: 'Villa / house' }).click()
await page.locator('.enquiry .chip', { hasText: 'Under construction' }).click()
await page.locator('.enquiry input[placeholder="Area, city"]').fill('Jubilee Hills, Hyderabad')
await page.locator('.enquiry input[placeholder="e.g. Ground + 3"]').fill('Ground + 3')
await cont()

console.log('step ->', await step())
const chips = await page.locator('.enquiry__panel:not([hidden]) .chip').allTextContents()
console.log('  systems offered:', chips.length, chips.slice(0, 4))
await page.locator('.enquiry__panel:not([hidden]) .chip').first().click()
await page.locator('.enquiry input[placeholder*="persons"]').fill('6 persons / 408 kg')
await page.locator('.enquiry input[placeholder="e.g. 4"]').fill('4')
await cont()

console.log('step ->', await step())
const field = (label) =>
  page.locator('.enquiryrow .enquiry .field').filter({ hasText: label }).first().locator('input')
await field('Name').fill('Automated Test')
await field('Phone').fill('+91 90000 00000')
await field('Email').fill('test@example.com')
await page.locator('.enquiryrow .enquiry textarea').first().fill('End-to-end submission test from the build.')
await page.locator('.enquiryrow .enquiry input[type=checkbox]').first().check()
await page.waitForTimeout(300)

const summary = await page.locator('.summary__list').innerText().catch(() => '(none)')
console.log('live summary:\n  ' + summary.replace(/\n/g, '\n  '))

await page.locator('.enquiryrow .enquiry__actions button[type=submit]').click()
await page.waitForTimeout(3000)

const done = await page.locator('.enquiry--done').count()
console.log('\nsubmitted:', done > 0)
if (done) {
  console.log('reference:', (await page.locator('.enquiry__ref').textContent())?.trim())
} else {
  console.log('errors on page:', await page.locator('.field__error').allTextContents())
}
if (errors.length) console.log('console/page errors:', [...new Set(errors)].slice(0, 5))

await browser.close()
process.exit(done > 0 ? 0 : 1)
