# Zion Lifts — website

Django REST API + React front end for Zion Lifts, Hyderabad. Built from
`zion-lifts-wireframes.html` and the studio's own photography, renders and
project films.

```
backend/       Django 5.2 + DRF — models, admin, API, seed content
frontend/      React 19 + Vite 8 — the site
assets-src/    Scripts that turn the masters into web assets
```

---

## Running it

Two processes. Django serves the API on `:8000`; Vite serves the site on
`:5173` and proxies `/api` to Django, so the app is same-origin in development.

```bash
# once
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Windows
# .venv/bin/python -m pip install -r requirements.txt        # macOS / Linux

cd backend
../.venv/Scripts/python manage.py migrate
../.venv/Scripts/python manage.py seed
../.venv/Scripts/python manage.py createsuperuser

cd ../frontend
npm install
python ../assets-src/build_all.py     # builds frontend/public/media (~10 min)
```

```bash
# every time — two terminals
cd backend  && ../.venv/Scripts/python manage.py runserver 8000
cd frontend && npm run dev
```

- Site — <http://localhost:5173>
- API — <http://localhost:8000/api/>
- Admin — <http://localhost:8000/admin/>

## Hosting on Vercel (static preview)

The site can be hosted as plain files, with no Django behind it: the API is
frozen into `frontend/public/api` as JSON and the front end reads that
instead. `vercel.json` at the root builds it (`npm run build:static`), serves
`frontend/dist`, and rewrites every route to `index.html`.

```bash
# 1. with the API running, freeze its content
cd frontend && npm run snapshot          # writes frontend/public/api

# 2. commit the snapshot and the media, push
git add frontend/public/api frontend/public/media vercel.json
git commit -m "Static snapshot for hosting" && git push

# 3. vercel.com → Add New → Project → import this repository → Deploy
#    (no settings to change; vercel.json carries them)
```

What the preview cannot do: send the enquiry and service forms — they show
a note with the phone number and email instead — and reflect admin edits
until the snapshot is re-run and pushed. Preview it locally with
`npm run build:static && npm run preview`.

## Tests

```bash
cd backend && ../.venv/Scripts/python manage.py test apps      # 28 tests
cd frontend && npm run build                                    # type/bundle check
cd frontend && node e2e-enquiry.mjs                             # enquiry, end to end
cd frontend && node shots.mjs                                   # screenshot every route
cd frontend && node shots.mjs --mobile --full /lifts            # one route, 390px, full page
```

`shots.mjs` and `probe.mjs` need the dev servers running. They exist for visual
review during development, not for CI.

---

## Content

Everything on the site is editable in the Django admin — nothing is hard-coded
in the React components except section headings and the four editorial captions
in Home's "The engineering".

| Admin section | What it drives |
| --- | --- |
| **Site settings** | Phone, email, addresses, founded year, installation count — the footer and every contact link |
| **Lifts** | The nine systems: copy, specs, variants, spec tables, gallery images, applications, safety features |
| **Projects** | The seven case studies: story, specification, staged imagery, films |
| **Editorial** | FAQ, journal, testimonials, timeline, team, awards, service pillars, gallery, legal documents |
| **Enquiries** | Incoming project enquiries with their drawings, and service requests, each with a pipeline status |

`python manage.py seed` is idempotent — it refreshes content in place rather
than duplicating it. `--flush` clears first.

### Adding a lift type

Admin → Lifts → Add. Slug becomes the URL (`/lifts/<slug>`). Fill the headline
specs (they appear under the product hero), add images inline (`kind=hero` is
used if `hero_image_url` is blank), then variants and spec rows. The product
page template renders whatever is present and skips what is not.

---

## Assets

`assets-src/` rebuilds `frontend/public/media/` from the masters. That output
is ~164 MB and is **not** in version control.

| Script | Input | Output |
| --- | --- | --- |
| `build_brand.py` | `logos/*.png` | Logo cut out of its white field, dark + light wordmark |
| `build_images.py` | `Zion HD Photos - Generated/`, `Zion Website/` | 10 interiors, 13 product renders, responsive webp + jpg |
| `build_frames.py` | the 4K `.mov` project masters | 56 hand-picked stills at chosen timestamps |
| `build_video.py` | the same masters | Web mp4 (~8–18 MB from 180–440 MB), muted loop, poster |
| `fetch_openverse.py` | Openverse API | CC-licensed stand-ins for what Zion has no photograph of |
| `prune_sourced.py` | — | Deletes the unusable ones, writes `ATTRIBUTION.md` |

```bash
python assets-src/build_all.py                  # brand, images, frames, video
python assets-src/build_all.py frames video     # just those steps
python assets-src/build_all.py --with-sourced   # also re-fetch the CC stand-ins
```

Every step skips outputs that already exist, so re-running is cheap.

### What is real and what is not

Every photograph of a Zion **lift, cabin, shaft, control panel, project or
building** is Zion's own — the ten HD interiors, the capsule / car-stacker /
dumbwaiter renders, and 56 stills lifted from the seven project films.

The **factory, component-macro and people** sections use 15 Creative Commons
stand-ins, credited in `frontend/public/media/ATTRIBUTION.md`. They are marked
`replace_with_real_shoot` in `assets-src/sourced-manifest.json`.

> **Before launch:** shoot the factory floor, the team, and macro details of
> Zion's own components, and swap those 15 files. The brief calls for authentic
> footage in exactly those sections, and CC images of other companies' factories
> are the weakest thing on the site. CC BY / BY-SA also require the credit to
> stay visible wherever they are published.

Two further gaps worth closing with real photography: the **goods / freight**
lift page borrows shaft-structure imagery from another project, and there is no
**platform / accessibility lift** page because there is no imagery for one.

---

## Architecture notes

**Scroll choreography.** Pinned sections (Home's hero, contexts, cabin, project
reel, final ascent; About's installation counter; the case-study sequence) are a
`position: sticky` stage inside a tall runway element. `useScrollProgress` in
`src/lib/hooks.js` measures progress through the runway; `mode: 'travel'`
measures an element crossing the viewport instead. Every pinned section unpins
under `prefers-reduced-motion`.

**Reveals.** One primitive — `Reveal` / `RevealGroup` / `SplitLines` in
`src/components/Reveal.jsx`. The `wipe` variant clips the reveal's *children*,
never the observed element: a node with `clip-path: inset(100%)` has zero
intersection area, so an observer watching it would never fire and the reveal
would deadlock shut.

**Images.** `Img` emits a `srcset` derived from the `.jpg` path — every asset
ships as `<name>-<width>.webp` beside `<name>.jpg`. Widths per directory live in
`src/lib/media.js`; changing them means changing the matching build script.

**Films.** `VideoLoop` only loads and plays a file once it is on screen, and
falls back to the poster under reduced motion or if playback is refused.

**The enquiry form** carries the cabin configuration through: choosing finishes
on Home or a product page links to `/contact?config=…&lift=…`, which the form
reads and posts as `configuration` JSON, shown formatted in the admin.

**Spam.** Both forms have an off-screen honeypot and sit behind a 12/hour
per-IP scoped throttle. A notification-email failure is logged but never fails
the request — the lead is saved first.

---

## Deploying

1. `pip install -r requirements.txt`, set `backend/.env` from `.env.example` —
   at minimum `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`,
   `CORS_ALLOWED_ORIGINS`, and real SMTP settings so enquiries are emailed.
2. `python manage.py migrate && python manage.py collectstatic && python manage.py seed`
3. `npm run build` in `frontend/` → `frontend/dist/`.
4. Serve `dist/` as static files with a SPA fallback to `index.html`, and
   `frontend/public/media/` alongside it. Proxy `/api` and `/admin` to Django
   (gunicorn/uvicorn behind nginx). `backend/uploads/` holds enquiry
   attachments — back it up.
5. Swap SQLite for Postgres in `DATABASES` before any real traffic.
