/**
 * End-to-end check of the control room, in a real browser.
 *
 *   CONTROL_EMAIL=you@example.com CONTROL_PASSWORD=... node e2e-control.mjs
 *   node e2e-control.mjs --mobile          # 390px viewport
 *
 * Needs both dev servers running. It signs in through Django's own
 * /admin/login/ — which has no CAPTCHA — and the panel then authenticates from
 * that session, so this exercises the panel rather than the login page.
 * `e2e-enquiry.mjs` covers the public form; this covers the other end.
 *
 * It edits one record and puts it back, so run it against a development
 * database rather than anything you care about.
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const BASE = process.env.BASE_URL ?? 'http://localhost:5173'
const EMAIL = process.env.CONTROL_EMAIL
const PASSWORD = process.env.CONTROL_PASSWORD
const OUT = process.env.SHOT_DIR ?? 'shots'
const mobile = process.argv.includes('--mobile')

if (!EMAIL || !PASSWORD) {
  console.error('Set CONTROL_EMAIL and CONTROL_PASSWORD to a staff account before running.')
  process.exit(2)
}

mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({
  viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 950 },
})

const errors = []
page.on('console', (m) => m.type() === 'error' && errors.push(`${page.url()} :: ${m.text()}`))
page.on('pageerror', (e) => errors.push(`${page.url()} :: ${e.message}`))

const results = []
const check = (label, ok, extra = '') => {
  results.push(ok)
  console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${label} ${extra}`)
}
const shot = (name) =>
  page.screenshot({ path: path.join(OUT, `${name}${mobile ? '-m' : ''}.png`), fullPage: true })

// --- sign in ---------------------------------------------------------------
await page.goto(`${BASE}/admin/login/?next=/admin/`, { waitUntil: 'domcontentloaded' })
await page.fill('#id_username', EMAIL)
await page.fill('#id_password', PASSWORD)
await Promise.all([page.waitForNavigation(), page.click('input[type=submit]')])
check(
  'signed in (the email backend accepts an address here too)',
  page.url().includes('/admin/') && !page.url().includes('/admin/login'),
  page.url(),
)

// --- dashboard -------------------------------------------------------------
await page.goto(`${BASE}/control`, { waitUntil: 'networkidle' })
await page.waitForTimeout(600)
check('control room loads', await page.locator('.cf-topbar__brand').isVisible())
check(
  'dashboard heading',
  (await page.locator('.cf-page__title').first().innerText()).includes('Overview'),
)
check('stat cards render', (await page.locator('.cf-stat').count()) === 4)
const navLinks = await page.locator('.cf-nav__link').count()
check('sidebar is built from the registry', navLinks > 25, `-> ${navLinks} links`)
await shot('control-dashboard')

// --- a list screen ---------------------------------------------------------
await page.goto(`${BASE}/control/lifts`, { waitUntil: 'networkidle' })
await page.waitForTimeout(500)
const rows = await page.locator('.cf-table tbody tr').count()
check('list renders rows', rows > 0, `-> ${rows}`)
const headers = (await page.locator('.cf-table thead th').allInnerTexts()).join('|').toLowerCase()
check(
  'columns come from list_display',
  ['name', 'tagline', 'capacity', 'speed'].every((h) => headers.includes(h)),
)
await shot('control-list')

// --- search lives in the URL ----------------------------------------------
await page.fill('#cf-search', 'capsule')
await page.waitForTimeout(900)
const searched = await page.locator('.cf-table tbody tr').count()
check('search narrows the table', searched > 0 && searched < rows, `-> ${searched} of ${rows}`)
check('search is shareable', page.url().includes('search=capsule'))

// --- the generated form ----------------------------------------------------
await page.goto(`${BASE}/control/lifts`, { waitUntil: 'networkidle' })
await page.locator('.cf-table tbody tr').first().locator('a.cf-link').click()
await page.waitForSelector('.cf-fieldset')
const legends = await page.locator('.cf-fieldset__legend').allInnerTexts()
check('form is sectioned from the fieldsets', legends.length >= 6, legends.join(', '))
check('a hex column renders a colour picker', (await page.locator('.cf-color__swatch').count()) > 0)
// Relation options are fetched after the form paints.
await page.waitForSelector('.cf-checks', { timeout: 10000 }).catch(() => {})
check('relations render as checkboxes', (await page.locator('.cf-checks').count()) > 0)
await shot('control-form')

// --- an edit, and put it back ---------------------------------------------
const tagline = page.locator('#field-tagline')
const original = await tagline.inputValue()
await tagline.fill(`${original} (edited)`)
await page.click('button[type=submit]')
await page.waitForSelector('.cf-toast', { timeout: 5000 })
check('saving confirms', (await page.locator('.cf-toast').innerText()).includes('saved'))
await page.reload({ waitUntil: 'networkidle' })
check('the edit persisted', (await page.locator('#field-tagline').inputValue()).includes('(edited)'))
await page.locator('#field-tagline').fill(original)
await page.click('button[type=submit]')
await page.waitForTimeout(700)
check('restored', (await page.locator('#field-tagline').inputValue()) === original)

// --- the registry's permissions reach the UI -------------------------------
await page.goto(`${BASE}/control/enquiries`, { waitUntil: 'networkidle' })
await page.waitForTimeout(400)
check(
  'a collection that forbids creation offers no New button',
  (await page.locator('.cf-page__actions a').count()) === 0,
)

await page.goto(`${BASE}/control/not-a-collection`, { waitUntil: 'networkidle' })
await page.waitForTimeout(600)
check(
  'an unknown collection shows an error, not a blank page',
  await page.locator('.cf-state').first().isVisible(),
)

await browser.close()

// A 404 from the deliberate bad-collection probe is expected, not a defect.
const real = [...new Set(errors)].filter((e) => !e.includes('not-a-collection'))
console.log(real.length ? `\n--- console errors ---\n${real.slice(0, 10).join('\n')}` : '\nno console errors')

const failed = results.filter((r) => !r).length
console.log(failed ? `\n${failed} CHECK(S) FAILED` : '\nALL CHECKS PASSED')
process.exit(failed ? 1 : 0)
