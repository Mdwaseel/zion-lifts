/**
 * Refreshes public/data/installations.json from the installation register —
 * the Google Sheet behind the "Find nearest Zion Lifts" page. Columns: Area,
 * City, Latitude, Longitude. Rows without a usable position are dropped, and
 * an area pinned twice at the same spot is kept once.
 *
 *   node scripts/fetch-installations.mjs
 */
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const SHEET_ID = '16LRappMeg2N4TCif4dEAE9zTzey9LvZt34p8_CBWgnk'
const URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:json&headers=1`
const OFFICE = { name: 'Zion Lifts, head office', lat: 17.458693, lng: 78.478792 }

const raw = await (await fetch(URL)).text()
const json = JSON.parse(raw.slice(raw.indexOf('(') + 1, raw.lastIndexOf(')')))
const seen = new Set()
const items = []
for (const row of json.table.rows) {
  const c = row.c ?? []
  const v = (i) => (c[i] && c[i].v != null ? String(c[i].v).trim() : '')
  const area = v(0).replace(/[,\s]+$/, '')
  let city = v(1)
  const lat = parseFloat(v(2))
  const lng = parseFloat(v(3))
  if (!area || !(lat > 16 && lat < 19 && lng > 77 && lng < 80)) continue
  if (/^secund/i.test(city)) city = 'Secunderabad'
  const key = `${area.toLowerCase()}|${lat.toFixed(5)}|${lng.toFixed(5)}`
  if (seen.has(key)) continue
  seen.add(key)
  items.push({ area, city, lat: +lat.toFixed(6), lng: +lng.toFixed(6) })
}

const out = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/data/installations.json')
writeFileSync(
  out,
  JSON.stringify(
    { source: `Zion Lifts installation register (Google Sheet ${SHEET_ID})`, fetched: new Date().toISOString().slice(0, 10), office: OFFICE, items },
    null,
    0,
  ),
)
console.log(`${items.length} installations → ${out}`)
