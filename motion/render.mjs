/* Renders the site's compositions to muted H.264 loops plus a poster still,
   into frontend/public/media/motion. `node render.mjs about-hero` renders one. */
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { bundle } from '@remotion/bundler'
import { renderMedia, renderStill, selectComposition, getCompositions } from '@remotion/renderer'

const here = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.resolve(here, '../frontend/public/media/motion')
/* the films the site shows; the dark originals stay in the project as the
   source of the light ones and render only when named */
const USED = [
  'about-modernise-light',
  'known-standards-light',
  'known-energy-light',
  'known-rescue-light',
  'known-schedule-light',
]
const only = process.argv.length > 2 ? process.argv.slice(2) : USED

const serveUrl = await bundle({ entryPoint: path.join(here, 'src/index.jsx'), publicDir: path.join(here, 'public') })
const all = await getCompositions(serveUrl)

for (const { id } of all) {
  if (!only.includes(id)) continue
  const composition = await selectComposition({ serveUrl, id })
  const wide = composition.width > 1200
  await renderMedia({
    serveUrl,
    composition,
    codec: 'h264',
    crf: wide ? 24 : 26,
    pixelFormat: 'yuv420p',
    muted: true,
    concurrency: 4,
    outputLocation: path.join(OUT, `${id}.mp4`),
    onProgress: ({ progress }) => process.stdout.write(`\r${id} ${Math.round(progress * 100)}%   `),
  })
  // the poster is the frame the film settles on, so a still page looks finished
  await renderStill({
    serveUrl,
    composition,
    frame: Math.round(composition.durationInFrames * 0.42),
    imageFormat: 'jpeg',
    jpegQuality: 84,
    output: path.join(OUT, `${id}.jpg`),
  })
  console.log(`\r${id} done`)
}
