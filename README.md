# Zion Lifts — website

Django REST API + React front end for Zion Lifts, Hyderabad. Built from
`zion-lifts-wireframes.html` and the studio's own photography, renders and
project films.

```
backend/       Django 5.2 + DRF — models, control room, API, seed content
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
- Control room — <http://localhost:5173/control> (sign in at `/login`)
- Django admin — <http://localhost:8000/admin/>

### The assistant

The **Ask Zion** assistant needs three more processes. Without them the widget
still loads and every question ends at a handled error with a link to the
contact form, so the rest of the site is unaffected by leaving them off.

```bash
# Redis — the queue Django and the worker share
docker run -d -p 6379:6379 redis:7-alpine

# the API, which answers questions
cd ai_service && uvicorn app.main:app --port 8080

# the worker, which indexes documents. Same image, same code, different job.
cd ai_service && celery -A app.tasks.celery_app:celery_app worker \n    --queues=ai_ingestion --concurrency=1 --loglevel=info
```

Or all three at once:

```bash
cd ai_service/docker && docker compose up          # redis, ai_api, ai_worker
docker compose --profile local-qdrant up           # ...and a local Qdrant
```

Vite proxies `/ai` to the API. If the service has `API_KEYS` set, give the dev
server the key so it can attach it — the browser must never hold it:

```bash
AI_SERVICE_API_KEY=<key> npm run dev      # AI_SERVICE_URL overrides the port
```

Two settings must agree across the two services or ingestion silently does
nothing: `REDIS_URL` (including the database number) and
`AI_SERVICE_INTERNAL_TOKEN`. Generate the token with
`python -c "import secrets; print(secrets.token_urlsafe(48))"` and put the same
value in `backend/.env` and `ai_service/.env`.

## Tests

CI runs all three suites on every push and pull request — see
`.github/workflows/ci.yml`. The backend job runs against a real Postgres,
because the constraints being tested (unique version numbers per document) are
database behaviour that SQLite would let pass vacuously.

```bash
cd backend && ../.venv/Scripts/python manage.py test apps            # 331 tests
cd backend && ../.venv/Scripts/python manage.py test apps.accounts   # 66 auth tests
cd frontend && npm test                                             # 12 auth-client tests
cd ai_service && .venv/Scripts/python -m pytest -m 'not integration'  # 248 tests
cd ai_service && REDIS_URL=redis://localhost:6379/1 QDRANT_TEST_URL=http://localhost:6333 \n    .venv/Scripts/python -m pytest -m integration
cd ai_service && .venv/Scripts/python -m ruff check . && .venv/Scripts/python -m ruff format --check .
cd ai_service && .venv/Scripts/python -m mypy app
cd frontend && npm run build                                        # bundle check
cd frontend && node e2e-enquiry.mjs                                 # enquiry, end to end
cd frontend && CONTROL_EMAIL=… CONTROL_PASSWORD=… node e2e-control.mjs   # control room
cd frontend && node shots.mjs                                   # screenshot every route
cd frontend && node shots.mjs --mobile --full /lifts            # one route, 390px, full page
```

`shots.mjs` and `probe.mjs` need the dev servers running. They exist for visual
review during development, not for CI.

---

## Content

Everything on the site is editable in the control room at `/control` — nothing
is hard-coded in the React components except section headings and the four
editorial captions in Home's "The engineering".

Every model lives in **one app**, `backend/apps/adminpanel/`, which owns the
site's data, the staff API over it (`/api/admin/`) and the anonymous API the
website reads (`/api/`). There is no second app holding a second copy.

| Control-room section | What it drives |
| --- | --- |
| **Inbox** | Incoming project enquiries with their drawings, and service requests, each with a pipeline status |
| **Lifts** | The nine systems: copy, specs, variants, spec tables, gallery images — plus finishes, applications, safety features and components |
| **Projects** | The seven case studies: story, specification, staged imagery, films |
| **Blogs** | The journal — posts, categories, featured flag |
| **Editorial** | FAQ, testimonials, gallery, team, timeline, awards, service pillars, legal pages |
| **Site settings** | Phone, email, addresses, founded year, installation count — the footer and every contact link — plus offices, stats, partners and certifications |
| **Knowledge base** | The assistant's corpus (see below) |

`python manage.py seed` is idempotent — it refreshes content in place rather
than duplicating it. `--flush` clears first.

### One record, one screen

A project used to be three tables — `Project`, `ProjectCategory`,
`ProjectImage` — which meant three screens to publish one case study. A lift was
five. Two rules collapsed them:

**A category is a field, not a table.** `ProjectCategory`, `JournalCategory` and
`FAQCategory` were each a slug and a name maintained by hand, joined to exactly
one parent, and used by the site only to draw a filter chip. They are `choices`
on the parent now, and `/api/project-categories/`, `/api/journal-categories/`
and `/api/faq-categories/` derive the list — with live counts — from the rows
themselves. A category can no longer be orphaned, misspelt in two places, or
exist with nothing in it.

**A child row that is only ever read with its parent is JSON on the parent.** A
project's photographs, a lift's images, variants and spec rows, a legal page's
clauses and an enquiry's attachments are never queried alone, never sorted
independently, and never joined to anything else. They are `JSONField` lists, so
the detail endpoints are one query instead of four and the form is one save.

The public JSON did not change. `category` still serialises as
`{"slug", "name"}` and `images` is still a list of objects — how content is
stored and edited is not the front end's business.

What did **not** collapse: `Application`, `SafetyFeature`, `Finish` and the
organisation models are genuinely shared or listed on their own by the public
API, so they stay addressable rows.

### Adding a lift

Control room → Lifts → Add. Slug becomes the URL (`/lifts/<slug>`). Fill the
headline specs (they appear under the product hero), then `images`, `variants`
and `specs` — three JSON lists in the same form, on the same page as the copy
they belong to. `kind=hero` is used if `hero_image_url` is blank. The product
page renders whatever is present and skips what is not.

---

## Assets

`assets-src/` rebuilds `frontend/public/media/` from the masters. That output
is ~164 MB and is **not** in version control.

| Script | Input | Output |
| --- | --- | --- |
| `build_brand.py` | `logos/*.png` | Logo cut out of its white field, dark + light wordmark |
| `build_chatbot.py` | `brand-src/chatbot.png` | The assistant's mascot at 64/96/128px, webp + png |
| `build_images.py` | `Zion HD Photos - Generated/`, `Zion Website/` | 10 interiors, 13 product renders, responsive webp + jpg |
| `build_frames.py` | the 4K `.mov` project masters | 56 hand-picked stills at chosen timestamps |
| `build_video.py` | the same masters | Web mp4 (~8–18 MB from 180–440 MB), muted loop, poster |
| `fetch_openverse.py` | Openverse API | CC-licensed stand-ins for what Zion has no photograph of |
| `prune_sourced.py` | — | Deletes the unusable ones, writes `ATTRIBUTION.md` |

```bash
python assets-src/build_all.py                  # brand, chatbot, images, frames, video
python assets-src/build_all.py frames video     # just those steps
python assets-src/build_all.py --with-sourced   # also re-fetch the CC stand-ins
```

Every step skips outputs that already exist, so re-running is cheap.

Masters live **outside** `frontend/public/media/`, because that directory is
gitignored — anything dropped straight into it is lost on the next clone. A new
brand asset goes in `brand-src/` (or `logos/`) with a script that emits the
web-ready sizes.

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

---

## Control room

A custom admin panel at `/control`, backed by `backend/apps/adminpanel/` — the
same app that owns the models, so the panel decides the shape of the data it
exists to edit rather than inheriting it from five other apps.

Django's own admin is still mounted at `/admin/`, but the site's content is no
longer registered there — `/control` is the only place it is edited, so the two
cannot disagree. `/admin/` administers users and groups, which is what
`django.contrib.auth` already does well.

Sign in at `/login`; a staff account lands in `/control`.

### How it manages twenty-five collections with one screen each

`adminpanel` is a registry, not twenty-five viewsets. Each collection is
declared once in `resources.py`, against a model in the same app:

```python
register(
    key="blogs",
    model=BlogPost,
    group=BLOGS,
    label="Blog post",
    label_plural="Blogs",
    list_display=("title", "category", "published_at", "is_featured", "is_published"),
    list_editable=("is_featured", "is_published"),
    search_fields=("title", "excerpt", "body"),
    filter_fields=("category", "is_featured"),
    slug_source=("slug", "title"),
    fieldsets=(...),
)
```

That one entry produces the routes, the table, the filters, the form and the
sidebar link. `schema.py` reads Django's own model metadata to describe each
field — its type, whether it is required, a choice field's options — and the
React panel has **one** table component and **one** form component that render
from that description. Add a field to a model and it appears in the form; there
is no second place to update.

Registration order is sidebar order and `group` is the sidebar heading, so this
one file is the map of the panel: read it top to bottom and you have read the
navigation. A model absent from it cannot be reached through the admin API at
all, which makes it the audit surface too.

### Endpoints

All under `/api/admin/`, all staff-only.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `navigation/` | The signed-in user and the grouped sidebar |
| `GET` | `dashboard/` | Pipelines, urgent work, recent activity, counts |
| `GET` | `activity/` | The audit trail |
| `GET` | `<key>/` | List — paginated, searchable, filterable, sortable |
| `POST` | `<key>/` | Create |
| `GET` `PATCH` `DELETE` | `<key>/<id>/` | Read, update, delete |
| `GET` | `<key>/schema/` | The field description the form renders from |
| `GET` | `<key>/options/` | Choices for this collection's relation fields |
| `POST` | `<key>/bulk/` | Publish / unpublish / delete the selected rows |

List rows carry two extras the table uses: `_str` (the model's own `__str__`)
and `_labels` (readable text for choice and relation fields, so a cell shows
"Home Elevator" rather than `7` without a second request).

### What it will and will not do

Permissions are per collection, declared in the registry and enforced by
`permissions.ResourceAllowsMethod` — not remembered in each handler:

- **Enquiries and service requests** cannot be created or deleted, and every
  field the customer filled in is read-only. Staff set a status and add internal
  notes; the record of what someone actually asked for is not editable.
- **Site settings** is a single row: no list, no create, no delete.
- Everything else is full CRUD.

### Audit trail

Writes are recorded in `django.contrib.admin.models.LogEntry` — the table
Django's own admin already writes to — so a change made in either admin lands in
one trail, readable from either. The message names the fields that changed and
never their values: enquiries hold names, phone numbers and addresses, and a log
that copied them would be a second copy of that data.

A logging failure is caught and never fails the edit; a broken log table must
not make the site uneditable.

### Adding a collection

1. `register(...)` it in `apps/adminpanel/resources.py`.
2. Run the tests. `test_schema.py` checks every registered resource describes
   itself, that every column and filter names a field that exists, and that the
   schema's "required" matches what the serializer actually enforces — a typo
   in a registration fails there rather than as a 500 on a real table.

There is nothing else to wire up: routes, sidebar and screens all follow.

## Knowledge base

The assistant answers from documents, and those documents are **Django's**
records, not Qdrant's. The vector index is a derived representation: rebuildable,
disposable, and the wrong place to ask who uploaded a file or which edition is
live. `apps/knowledge` owns that.

```
KnowledgeBase  →  Document  →  DocumentVersion  →  IngestionJob  →  vectors
```

A **Document** is what an operator thinks about ("the 2026 warranty policy"). A
**DocumentVersion** is one immutable edition of its bytes, and it is the thing
that gets indexed — so replacing a document leaves the edition currently
answering questions untouched, and a failed re-index means a failed *job*, not a
broken document. An **IngestionJob** is one attempt: kept as history, because
three failures and one failure are different problems.

These four use UUID primary keys, unlike the rest of the site. They cross a
service boundary — through Redis to a worker this process cannot see, and into
vector payloads that outlive any single database — and a sequential integer
there is both an enumeration surface and unsafe to compare across environments.

### The lifecycle

```
UPLOADED → PROCESSING → EXTRACTING → CHUNKING → EMBEDDING → INDEXING → READY
                ↓            ↓           ↓           ↓          ↓
              FAILED  ←──────┴───────────┴───────────┴──────────┘
                ↓
            PROCESSING (retry)      READY → PROCESSING (reindex)
                                    any   → DELETING → DELETED
```

`apps/knowledge/states.py` is the whole specification, and the only way to move
is `document.transition_to(...)`, which raises `InvalidTransition` rather than
accepting a status nothing expects. One shortcut is deliberate and documented
there: `PROCESSING → READY`. A Document *summarises* its versions rather than
being extracted itself, so re-indexing one that already has three editions does
not march it through stages nothing reports on its behalf.

### Where the two services meet

Django never imports `ai_service`. It knows a task name and a payload shape —
both in `apps/knowledge/dispatch.py`, which is the entire coupling — and posts
to Redis. The worker lives in the `ai_service` image, where torch and the Qdrant
client already are; sharing one Celery app would mean Django installing a
two-gigabyte ML stack to enqueue a job. `test_boundary.py` walks the AST of every
backend module and fails if that line is ever crossed.

The message carries identifiers and a content hash, never file bytes, so the
broker never holds a document. It is sent **after** the transaction commits —
Celery is quite fast enough to deliver a message about rows that are not visible
yet.

### Endpoints

Browsing and filtering go through the registry like every other collection, at
`/api/admin/knowledge-documents/`. The operations the generic CRUD cannot
express live at `/api/admin/knowledge/`:

```
POST   documents/upload/          multipart: knowledge_base, file, name?
GET    documents/{id}/versions/   editions, newest first
POST   documents/{id}/versions/   replace; 409 if the bytes are already stored
GET    documents/{id}/status/     for polling while something is processing
POST   documents/{id}/reindex/    re-run ingestion for the live edition
POST   documents/{id}/retry/      a failed document, from its newest edition
POST   documents/{id}/delete/     begin removal — clears vectors first
```

There is no `POST /documents/` and no `DELETE`: creating a document means
storing a file and queuing work, and removing one means clearing an index. Both
are operations rather than row writes, and naming them keeps that visible.

### Uploads

Validated in the request and parsed nowhere near it. `validators.py` checks the
extension, the declared type, the size, and then the first five bytes — because
a name ending in `.pdf` and a `Content-Type` header are both supplied by the
client, and neither is evidence. Filenames are sanitised for storage and
display, but the storage path itself is built from UUIDs, so a hostile name has
nothing to reach.

Identical bytes are refused with a 409 naming the existing version. Re-uploading
the same file is nearly always a repeated click, and honouring it would mean a
second copy of every chunk, a second embedding bill, and two versions to tell
apart.

### Ingestion

An upload is accepted in the request and processed nowhere near it. Django
stores the file, writes a job, and puts a message on Redis; a worker in the
`ai_service` image picks it up and reports back over the internal route.

```
admin → Django ──store file, write job──▶ Postgres
                └──send_task────────────▶ Redis ──▶ ai_worker
                                                      │ extract → chunk
                                                      │ → embed → index
                                                      ▼
                                                    Qdrant
                ◀──POST ingestion-report──────────────┘
```

The worker owns no business data. Its only way to change anything in Postgres
is `POST /api/internal/knowledge/ingestion-report/`, which authenticates with
`AI_SERVICE_INTERNAL_TOKEN`, checks that the job, document and version in the
report genuinely describe each other, and refuses anything out of order.

**File access.** The worker needs the actual PDF, and it must not be assumed
that two containers with a path called `/uploads` are looking at the same disk.
`DOCUMENT_STORAGE=http` (the default) has the worker fetch each file from the
backend over the internal route, which assumes nothing about where it runs.
`DOCUMENT_STORAGE=local` reads a directory instead — faster, and correct only
when the deployment really does mount Django's `MEDIA_ROOT` there. The volume is
written out, commented, in `ai_service/docker/docker-compose.yml`. The bytes are
hashed on arrival and checked against the version record, so a file that has
changed underneath is refused rather than indexed.

**Why a partial index is never visible.** Chunks are written with
`active: false` and flipped in one server-side call after the whole version has
been written. A run that dies at chunk 700 of 1000 leaves 700 chunks that
nothing retrieves — not 700 chunks answering as though they were a document. The
retrieval filter carries `active: true` on every knowledge-base query, which is
also what lets several versions share one collection safely.

**Why the old version keeps answering.** Nothing belonging to the previous
edition is touched until the new one is completely written and flipped active;
only then is the old one deleted. Version 2 failing leaves version 1 with the
same points, the same flag and the same answers. Django activates a version only
when it receives `READY`, and the worker sends `READY` only after the flip.

**What retries, and what does not.** `app/core/errors.py` is the list. A corrupt
PDF, a hash mismatch, a vector of the wrong width and a malformed message are
permanent — retrying produces the same failure and delays every document behind
it. Qdrant being unreachable, a provider rate-limiting and a callback timing out
are transient, retried with exponential backoff up to
`CELERY_TASK_MAX_RETRIES`. A job about to be retried is left RUNNING: it has not
failed yet, and saying otherwise sends an operator after a document that is
going to fix itself.

**Why a retry cannot duplicate anything.** A point's id is a UUID5 of
`document_version_id/chunk_index`, so a second pass writes to the same ids and
replaces them. Re-embedding on retry is deliberate — a few seconds of CPU in
exchange for not keeping intermediate state consistent across process restarts.

**Collections.** `kb_<knowledge base>__<model>_<version>_d<dimension>`, built by
`CollectionNameBuilder` from the embedding provider that actually answered. The
whole model name goes in, organisation included — `org-a/embed` and
`org-b/embed` are different models producing incomparable vectors, and keeping
only the segment after the slash would have put them in one collection. Long
names get a digest appended rather than being truncated into a collision. If a
fallback model produced the vectors, its name is in the collection name, because
384-dimensional vectors cannot be compared with 768-dimensional ones and must
not share an index. A width that disagrees with the collection fails the run
before a single point is written; nothing is ever padded or truncated.

### Retrieval

```
query
 ├── dense vector  ──▶ Qdrant (named "dense")
 └── sparse vector ──▶ Qdrant (named "sparse", IDF applied server-side)
                             ↓
                      Reciprocal Rank Fusion
                             ↓
                        deduplicate
                             ↓
                    cross-encoder rerank
                             ↓
                       context builder
                             ↓
                       confidence gate
```

**Lexical search is Qdrant's job now.** It used to be done by scrolling up to two
thousand chunks out of the store and building a BM25 index over them, per query —
linear in corpus size on every request, and silently truncating past the scan
limit. Chunks now carry a sparse vector alongside their dense one, the collection
declares `Modifier.IDF`, and Qdrant computes inverse document frequency across
the whole corpus at query time. `app/retrieval/sparse.py` keeps the only part
that must stay client-side: which dimension a term occupies, hashed with BLAKE2
rather than Python's `hash()`, which is salted per process and would have put a
term in one dimension in the worker and another in the API.

**Both halves, or a refusal.** One retriever failing degrades the answer and is
recorded in `last_degradation`; both failing raises rather than returning an
empty list, because an empty list is indistinguishable from "the corpus has
nothing on this" and would produce a polite refusal while the real problem went
unreported.

**Deduplication is by identity**, not text similarity — the point id, which the
ingestion pipeline derives from the version and chunk index. Two chunks that
overlap because of the chunker's overlap window are genuinely two chunks, and
collapsing them on similarity would quietly narrow the context.

**Comparing retrieval modes.** `scripts/evaluate.py --compare` runs the same
dataset through dense only, sparse only, hybrid, and hybrid with the reranker,
and tabulates recall, precision, MRR, nDCG, groundedness, citation validity,
refusal correctness and p50/p95/p99 latency. Four stages that each cost latency
and are each *assumed* to help; this is how that assumption becomes a number.

**Worker concurrency is 1 by default.** Each child loads its own copy of the
embedding model and the cross-encoder, so concurrency multiplies resident memory
rather than throughput. Measure before raising `CELERY_WORKER_CONCURRENCY`.

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

**The assistant.** A docked panel over the RAG service in `ai_service/`, mounted
in `Layout` so it is available on every public page.

```
src/lib/assistant.js                 SSE client, session id, error mapping
src/components/Assistant.jsx         panel, state machine, focus and scroll
src/components/assistant/Answer.jsx  markdown-lite renderer + [n] markers
src/components/assistant/Sources.jsx citations and the low-confidence notice
```

Four decisions are load-bearing:

*It talks to `/ai`, not to the service.* The service is guarded by an
`X-API-Key`, and a key in the bundle is a key in every visitor's DevTools. The
dev-server proxy attaches it in Node (`vite.config.js`), and in production the
edge proxy does — so the same origin-relative path works in both, and the key
lives in neither.

*Streaming degrades rather than fails.* `ask()` reads `POST /chat/stream` as SSE,
but a stream that returns no body, or closes without a single delta, is
indistinguishable from a proxy that buffered it — so it re-asks `POST /chat` and
delivers the answer in one piece instead of rendering nothing.

*Answers are never trusted to be markup.* `Answer.jsx` builds React elements and
never touches `innerHTML`; a `<script>` in a generated answer renders as text.
The grammar it understands is deliberately small, and it is correct at every
intermediate string, because it is parsing text that is still arriving.

*Grounding is visible.* `[1]` markers in the prose open the passage behind them,
and a `confidence_level` of `low` says so above the sources. High confidence
shows nothing — a badge on every answer is a badge nobody reads.

Below 640px the panel becomes a modal sheet with the page behind it locked; above
it, it is a non-modal docked bubble and does not trap focus. It loads on
`requestIdleCallback`, in its own chunk, so it costs the first paint nothing.

---

## Deploying

1. `pip install -r requirements.txt`, set `backend/.env` from `.env.example` —
   at minimum `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`,
   `CORS_ALLOWED_ORIGINS`, and real SMTP settings so enquiries are emailed.
2. `python manage.py migrate && python manage.py collectstatic && python manage.py seed`
3. `npm run build` in `frontend/` → `frontend/dist/`.
3a. Deploy the assistant, if it is in use: `ai_api` and `ai_worker` from the
   same `ai_service` image, plus the Redis they share with Django. The worker
   runs Celery, never uvicorn, and never inside the API container — a long
   ingestion must not be able to make the site's chat endpoint unresponsive.
   `AI_SERVICE_INTERNAL_TOKEN` and `REDIS_URL` must be identical on both sides;
   with `DJANGO_DEBUG=0` the settings module refuses to start without the token.

4. Serve `dist/` as static files with a SPA fallback to `index.html`, and
   `frontend/public/media/` alongside it. Proxy `/api` and `/admin` to Django
   (gunicorn/uvicorn behind nginx). `backend/uploads/` holds enquiry
   attachments — back it up.
   If the assistant is deployed, `/ai` proxies to the RAG service, and nginx —
   not the bundle — holds its API key. Buffering must be off, or answers arrive
   in one lump at the end instead of streaming:

   ```nginx
   location /ai/ {
       proxy_pass http://127.0.0.1:8080/;
       proxy_set_header X-API-Key $ai_service_key;   # from an env/map, never inline
       proxy_http_version 1.1;
       proxy_buffering off;                          # SSE
       proxy_read_timeout 120s;
   }
   ```
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
