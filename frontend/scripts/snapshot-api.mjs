/**
 * Freezes the Django API into JSON files under public/api, so the site can be
 * hosted as plain static files (Vercel, Netlify, any CDN) without a Python
 * backend behind it.
 *
 *   cd backend  && ../.venv/Scripts/python manage.py runserver 8000
 *   cd frontend && npm run snapshot
 *
 * The file layout mirrors what lib/api.js asks for in static mode:
 *
 *   /api/lifts/                       → public/api/lifts/index.json
 *   /api/lifts/home-elevator/         → public/api/lifts/home-elevator/index.json
 *   /api/stats/?group=about           → public/api/stats/_q/group=about.json
 *
 * Every collection the front end reads is listed here, plus the detail pages
 * for each slug and the filtered variants the pages ask for. Re-run it after
 * changing content in the admin or the seed, then commit public/api.
 */
import { mkdir, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const API = process.env.API_BASE ?? 'http://127.0.0.1:8000/api'
const OUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/api')

const COLLECTIONS = [
  'site',
  'lifts',
  'applications',
  'safety-features',
  'finishes',
  'components',
  'projects',
  'project-categories',
  'faq-categories',
  'journal-categories',
  'journal',
  'testimonials',
  'milestones',
  'team',
  'awards',
  'service-pillars',
  'gallery',
  'legal',
  'offices',
  'stats',
  'partners',
  'certifications',
]

/** collections whose members have their own page */
const DETAIL = ['lifts', 'projects', 'journal', 'legal']

/** filtered requests the pages make (see the useApi calls) */
const FILTERS = [
  ['stats', { group: 'about' }],
  ['stats', { group: 'projects' }],
  ['faq-categories', { scope: 'contact' }],
]

function unwrap(data) {
  return data && !Array.isArray(data) && Array.isArray(data.results) ? data.results : data
}

async function fetchJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`)
  return unwrap(await res.json())
}

async function save(rel, data) {
  const file = path.join(OUT, rel)
  await mkdir(path.dirname(file), { recursive: true })
  await writeFile(file, JSON.stringify(data))
  return file
}

async function main() {
  await rm(OUT, { recursive: true, force: true })
  let files = 0
  const collections = {}

  for (const name of COLLECTIONS) {
    const data = await fetchJson(`${API}/${name}/`)
    collections[name] = data
    await save(`${name}/index.json`, data)
    files += 1
  }

  for (const name of DETAIL) {
    for (const item of collections[name]) {
      if (!item.slug) continue
      const data = await fetchJson(`${API}/${name}/${item.slug}/`)
      await save(`${name}/${item.slug}/index.json`, data)
      files += 1
    }
  }

  // projects filtered by lift type, one file per lift
  for (const lift of collections.lifts) {
    FILTERS.push(['projects', { lift_type__slug: lift.slug }])
  }

  for (const [name, params] of FILTERS) {
    const qs = new URLSearchParams(params).toString()
    const data = await fetchJson(`${API}/${name}/?${qs}`)
    await save(`${name}/_q/${qs}.json`, data)
    files += 1
  }

  const mediaRefs = JSON.stringify(collections).match(/\/uploads\/[^"]+/g) ?? []
  console.log(`snapshot: ${files} files written to ${OUT}`)
  if (mediaRefs.length) {
    console.warn(
      `warning: ${mediaRefs.length} reference(s) to /uploads — admin-uploaded files are not part of the static site:\n  ${[...new Set(mediaRefs)].join('\n  ')}`,
    )
  }
}

main().catch((err) => {
  console.error(err.message)
  console.error('Is the Django API running? Start it with: cd backend && ../.venv/Scripts/python manage.py runserver 8000')
  process.exit(1)
})
