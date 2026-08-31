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

## Tests

```bash
cd backend && ../.venv/Scripts/python manage.py test apps            # 94 tests
cd backend && ../.venv/Scripts/python manage.py test apps.accounts   # 66 auth tests
cd frontend && npm test                                             # 12 auth-client tests
cd frontend && npm run build                                        # bundle check
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

---

## Authentication

A React login page at `/login` signs staff into the Django admin. One user
record — `django.contrib.auth.User` — is the only source of truth; there is no
second account table and no second password.

### The flow

```
/login  ──POST /api/accounts/login/──▶  validate CAPTCHA
                                        validate email + password
                                        mint JWT access + refresh
                                        write both to HttpOnly cookies
                                        open a Django session (staff only)
                                   ◀──  { "detail": ..., "user": {...} }
        ──▶ /admin/
```

The JSON never contains a token. Both tokens are HttpOnly cookies, so no script
on the page can read them — that is the whole point of the design, and there is
nothing in `localStorage` or `sessionStorage` to steal either.

The admin is server-rendered and authenticates from Django's session cookie, so
a JWT alone would not open it. Rather than bolt a second authentication path
onto the admin, a successful **staff** login also calls
`django.contrib.auth.login()` for the same user: one request, one user, two
credentials. `login()` cycles the session key, which closes session fixation. A
non-staff user authenticates for the API but gets no session and sees an
unauthorised panel instead of the admin.

### Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/accounts/captcha/` | none | New challenge; also seeds the CSRF cookie |
| `POST` | `/api/accounts/login/` | none | Email + password + CAPTCHA → auth cookies |
| `POST` | `/api/accounts/refresh/` | refresh cookie | New access cookie, rotated refresh |
| `POST` | `/api/accounts/logout/` | none | Blacklist refresh, clear cookies, end session |
| `GET` | `/api/accounts/me/` | access cookie | The signed-in user |

**`GET /api/accounts/captcha/`**

```json
{ "captcha_id": "opaque-public-id", "image": "data:image/png;base64,..." }
```

The answer is never sent to the browser. Only a salted SHA-256 HMAC of it is
stored, in the cache, for five minutes. A challenge is single-use, dies after
three wrong guesses, and is case-insensitive. Call this first: the response also
carries the `csrftoken` cookie the login POST has to echo back.

**`POST /api/accounts/login/`**

```json
{
  "email": "admin@example.com",
  "password": "********",
  "captcha_id": "opaque-public-id",
  "captcha_answer": "A7K92"
}
```

```json
{
  "detail": "Login successful.",
  "user": { "id": 1, "email": "admin@example.com", "name": "Admin",
            "is_staff": true, "is_superuser": true }
}
```

`user` is returned so the front end can route without a second round trip. It
is the same payload as `/me/` and holds nothing secret.

Sets `access_token` (path `/`) and `refresh_token` (path `/api/accounts/`), both
HttpOnly, `SameSite` per `AUTH_COOKIE_SAMESITE`, and Secure outside DEBUG.

**`POST /api/accounts/refresh/`** reads the refresh cookie — the client sends
nothing — and returns `{"detail": "Token refreshed."}` with fresh cookies. The
refresh token is rotated and the spent one blacklisted, so replaying a stolen
token fails.

**`POST /api/accounts/logout/`** → `{"detail": "Logged out successfully."}`.
Blacklists the refresh token, deletes both cookies, ends the Django session.
Open to unauthenticated callers so an expired session can still clear itself,
but CSRF-protected so another site cannot sign you out.

**`GET /api/accounts/me/`** → the user object above, or 401.

### Errors

| Status | When | Body |
| --- | --- | --- |
| 400 | Malformed request | DRF field errors |
| 400 | Bad or expired CAPTCHA | `{"detail": "Invalid or expired CAPTCHA.", "code": "captcha_invalid"}` |
| 401 | Wrong password *or* unknown address | `{"detail": "Invalid email or password.", "code": "invalid_credentials"}` |
| 401 | Missing/expired/blacklisted refresh | `{"code": "no_refresh_token"}` / `{"code": "refresh_invalid"}` |
| 429 | Rate limited | DRF throttle detail, with `Retry-After` |

The 401 is deliberately identical for a wrong password and an address that does
not exist, and the backend runs the password hasher either way so the timing
matches — login must not become an account-enumeration oracle.

### CSRF

The cookies are sent by the browser automatically, so CSRF protection is not
optional and nothing here is `@csrf_exempt`. DRF exempts its own views from
`CsrfViewMiddleware` and expects the authentication class to run the check
instead: `JWTCookieAuthentication` does exactly that for authenticated unsafe
requests, and `/login/` and `/refresh/`, which have no user yet, are wrapped in
`csrf_protect`. The React client reads `csrftoken` — the one cookie Django
deliberately exposes — and sends it as `X-CSRFToken`.

### Rate limits

Per IP on `/login/` and `/captcha/`, plus a per-address cap that only counts
*failures*, so a distributed run against one account is capped even when no
single IP looks busy. All three are environment variables; see
`backend/.env.example`.

**Set `NUM_PROXIES` to match the deployment.** It decides which address a limit
counts against. Left unset, DRF keys the bucket on the whole client-supplied
`X-Forwarded-For` header, so varying that header puts every request in a fresh
bucket and the rate limits do not bind at all. `0` for direct access, `1` behind
the single nginx this project deploys with.

### Layout

```
backend/apps/accounts/
├── authentication.py   JWT-from-cookie, with the CSRF check
├── backends.py         email → the existing auth.User
├── captcha.py          challenge generation and verification
├── permissions.py      IsStaffUser
├── serializers.py      login input, user output
├── services.py         tokens, cookies, admin session
├── throttling.py       per-IP and per-account limits
└── views.py            the five endpoints

frontend/src/
├── api/client.js       fetch + credentials + CSRF + single-flight refresh
├── api/auth.js         the five calls and their error text
├── lib/auth.jsx        AuthProvider / useAuth
├── components/auth/Captcha.jsx
└── pages/Login.jsx
```

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
6. Set `REDIS_URL`. Throttle buckets and CAPTCHA challenges have to be visible
   to every worker; the in-memory fallback is per-process, so with more than one
   gunicorn worker a CAPTCHA would only validate on the worker that issued it
   and each rate limit would effectively be multiplied by the worker count.
7. Set `AUTH_COOKIE_SECURE=true` and `NUM_PROXIES=1` (one nginx). With
   `DJANGO_DEBUG=0` the settings module refuses to start unless the cookies are
   Secure, the signing key is real, and `CORS_ALLOWED_ORIGINS` names the actual
   site rather than localhost — misconfiguration fails loudly instead of
   quietly shipping an insecure deployment.

`DJANGO_DEBUG` still defaults to `1`, which is how this project has always
worked locally. Every production guard above is inside `if not DEBUG`, so a
deployment that forgets `DJANGO_DEBUG=0` gets none of them **and** signs its
JWTs with the development `SECRET_KEY` committed in `settings.py` — which would
let anyone holding this repository mint a token for any user. Set
`DJANGO_DEBUG=0` first, before anything else.
