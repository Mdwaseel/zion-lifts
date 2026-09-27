import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Arrow, Close, Pin } from '@/components/icons'
import { useReducedMotion } from '@/lib/hooks'
import { loadLeaflet } from '@/lib/leaflet'

import { RiseIn } from '../lift/shared'

import './installations.css'

const pad = (n) => String(n).padStart(2, '0')
const DATA = '/data/installations.json'
/* CARTO's Voyager tiles are already the quiet street map the section wants,
   so no filter has to run over the tile layer on every frame */
const MAP_KEY = import.meta.env.VITE_MAP_API_KEY
const TILES =
  'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png' +
  (MAP_KEY ? `?key=${encodeURIComponent(MAP_KEY)}` : '')
const CREDIT =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

/** how close choosing a single installation goes: street level */
const CLOSE = 16
/** the furthest out choosing an area is allowed to leave the map, so a
    scattered area still reads as having been zoomed into */
const AREA_MIN = 13.5

/* distance over the ground between two points, in km */
function km(a, b) {
  const R = 6371
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLng = ((b.lng - a.lng) * Math.PI) / 180
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}

const fmtKm = (d) => (d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(d < 10 ? 1 : 0)} km`)

/* --- every installation, on the map ------------------------------------------
   Every lift Zion has installed, pinned where it stands, on a map of the city
   (Leaflet on OpenStreetMap tiles, loaded only when the section is near).
   Press a pin and the map flies to it while its details come up in the panel;
   search an area, or find the installations nearest to you. */

export function Installations() {
  const sec = useRef(null)
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const markers = useRef([])
  const halo = useRef(null)
  const you = useRef(null)
  const listRef = useRef(null)
  const reduced = useReducedMotion()

  const [data, setData] = useState(null)
  const [status, setStatus] = useState('idle') // idle · loading · ready · failed
  const [sel, setSel] = useState(null)
  const [q, setQ] = useState('')
  const [near, setNear] = useState(null) // { lat, lng } of the visitor
  const [geo, setGeo] = useState('') // a note under the "near me" button

  const items = data?.items ?? []
  const office = data?.office

  // the areas, each with its installations, for the list
  const areas = useMemo(() => {
    const m = new Map()
    items.forEach((it, i) => {
      const key = it.area.toLowerCase()
      if (!m.has(key)) m.set(key, { key, area: it.area, city: it.city, idx: [] })
      m.get(key).idx.push(i)
    })
    const list = [...m.values()]
    if (near) {
      list.forEach((a) => {
        a.d = Math.min(...a.idx.map((i) => km(near, items[i])))
      })
      list.sort((a, b) => a.d - b.d)
    } else {
      list.sort((a, b) => b.idx.length - a.idx.length || a.area.localeCompare(b.area))
    }
    return list
  }, [items, near])

  const shown = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return areas
    return areas.filter((a) => a.area.toLowerCase().includes(s) || a.city.toLowerCase().includes(s))
  }, [areas, q])

  // load the register and the map library once the section is near
  useEffect(() => {
    const el = sec.current
    if (!el) return undefined
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return
        io.disconnect()
        setStatus('loading')
        Promise.all([fetch(DATA).then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status)))), loadLeaflet()])
          .then(([json]) => {
            setData(json)
            setStatus('ready')
          })
          .catch(() => setStatus('failed'))
      },
      { rootMargin: '600px 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  const select = useCallback(
    (i, { fly = true } = {}) => {
      setSel(i)
      const L = window.L
      const map = mapRef.current
      const it = items[i]
      if (!L || !map || !it) return
      markers.current.forEach((m, k) => m.setOn(k === i))
      if (halo.current) halo.current.setLatLng([it.lat, it.lng])
      else halo.current = L.marker([it.lat, it.lng], { icon: L.divIcon({ className: 'inst-halo', iconSize: [40, 40], iconAnchor: [20, 20] }), interactive: false, keyboard: false, zIndexOffset: -1000 }).addTo(map)
      if (fly) {
        // choosing one installation always goes in close enough to read the
        // street it stands on, never merely recentres the city
        const z = Math.max(map.getZoom(), CLOSE)
        if (reduced) map.setView([it.lat, it.lng], z)
        else map.flyTo([it.lat, it.lng], z, { duration: 1.1 })
      }
    },
    [items, reduced],
  )

  // build the map once the library and the register are in
  useEffect(() => {
    if (status !== 'ready' || !mapEl.current || mapRef.current || !items.length) return undefined
    const L = window.L
    const map = L.map(mapEl.current, { scrollWheelZoom: false, preferCanvas: true, zoomControl: true })
    mapRef.current = map
    L.tileLayer(TILES, { attribution: CREDIT, maxZoom: 19, subdomains: 'abcd' }).addTo(map)
    // the wheel only zooms the map once the visitor has put their hand on it
    map.on('click focus', () => map.scrollWheelZoom.enable())
    map.on('mouseout blur', () => map.scrollWheelZoom.disable())

    const group = L.featureGroup().addTo(map)
    markers.current = items.map((it, i) => {
      const m = pinMarker(L, [it.lat, it.lng], {}).addTo(group)
      m.bindTooltip(`${it.area}, ${it.city}`, { direction: 'top', offset: [0, -30], opacity: 0.95 })
      m.on('click', () => select(i))
      return m
    })
    if (office) {
      L.marker([office.lat, office.lng], {
        icon: L.divIcon({ className: 'inst-office', html: '<span>Z</span>', iconSize: [30, 30] }),
        keyboard: false,
      })
        .addTo(map)
        .bindTooltip(office.name, { direction: 'top', offset: [0, -14] })
    }
    map.fitBounds(cityBounds(L, items, office), { padding: [24, 24] })
    return () => {
      map.remove()
      mapRef.current = null
      markers.current = []
      halo.current = null
      you.current = null
    }
    // `select` is stable for a given register; the map is built once per register
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, items, office])

  // the whole register again
  const showAll = () => {
    setSel(null)
    setNear(null)
    setQ('')
    const L = window.L
    const map = mapRef.current
    if (!map) return
    markers.current.forEach((m) => m.setOn(false))
    if (halo.current) {
      halo.current.remove()
      halo.current = null
    }
    if (you.current) {
      you.current.remove()
      you.current = null
    }
    const b = cityBounds(L, items, office)
    if (reduced) map.fitBounds(b, { padding: [24, 24] })
    else map.flyToBounds(b, { padding: [24, 24], duration: 1 })
  }

  /* An area from the list: one pin, or that area's pins together in view.

     `flyToBounds` alone was the bug here. It fits whatever it is given, and an
     area whose installations are spread across the city fits at about the zoom
     the city already sits at — so choosing Kompally or Jubilee Hills moved the
     map a little and looked like nothing had happened. Leaflet's bounds
     options cap the zoom but cannot floor it, so the fitting zoom is worked
     out first and then clamped from below as well as above. */
  const pickArea = (a) => {
    const map = mapRef.current
    if (a.idx.length === 1 || !map) {
      select(a.idx[0])
      return
    }
    select(a.idx[0], { fly: false })
    const L = window.L
    const b = L.latLngBounds(a.idx.map((i) => [items[i].lat, items[i].lng])).pad(0.12)
    const fit = map.getBoundsZoom(b, false)
    const z = Math.min(CLOSE, Math.max(AREA_MIN, fit))
    if (reduced) map.setView(b.getCenter(), z)
    else map.flyTo(b.getCenter(), z, { duration: 1 })
  }

  // the installations nearest the visitor
  const findNear = () => {
    if (!navigator.geolocation) {
      setGeo('Your browser cannot share a location.')
      return
    }
    setGeo('Finding you…')
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const here = { lat: coords.latitude, lng: coords.longitude }
        setNear(here)
        setGeo('')
        setQ('')
        const L = window.L
        const map = mapRef.current
        if (!L || !map) return
        if (you.current) you.current.setLatLng([here.lat, here.lng])
        else you.current = L.marker([here.lat, here.lng], { icon: L.divIcon({ className: 'inst-you', iconSize: [18, 18] }), keyboard: false }).addTo(map).bindTooltip('You', { direction: 'top', offset: [0, -8] })
        const nearest = [...items].sort((a, b) => km(here, a) - km(here, b)).slice(0, 6)
        const b = L.latLngBounds([[here.lat, here.lng], ...nearest.map((it) => [it.lat, it.lng])]).pad(0.2)
        if (reduced) map.fitBounds(b)
        else map.flyToBounds(b, { duration: 1.2 })
      },
      () => setGeo('We could not read your location. You can still search an area.'),
      { enableHighAccuracy: true, timeout: 12000 },
    )
  }

  // the list scrolls to the area of the pin that was pressed
  useEffect(() => {
    if (sel === null || !listRef.current) return
    const key = items[sel]?.area.toLowerCase()
    const row = listRef.current.querySelector(`[data-area="${CSS.escape(key ?? '')}"]`)
    row?.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' })
  }, [sel, items, reduced])

  const cur = sel !== null ? items[sel] : null
  const curArea = cur ? areas.find((a) => a.key === cur.area.toLowerCase()) : null
  const n = items.length

  return (
    <section ref={sec} id="installations" className="inst on-paper" aria-labelledby="inst-title">
      <div className="inst__head">
        <div>
          <p className="ld-label">Where we have installed</p>
          <RiseIn id="inst-title" className="inst__title" text={n ? `${n} lifts. One city.` : 'Every lift, on the map.'} />
        </div>
        <p className="inst__lead">
          Every installation Zion has made across Hyderabad and Secunderabad, pinned where it stands. Press a pin, search
          an area, or find the ones nearest to you.
        </p>
      </div>

      <div className="inst__body">
        <div className="inst__map-wrap">
          <div ref={mapEl} className="inst__map" data-lenis-prevent aria-label="Map of Zion Lifts installations" />
          {status !== 'ready' && (
            <p className="inst__state" role="status">
              {status === 'failed' ? 'The map could not be loaded. Please try again later.' : 'Loading the map…'}
            </p>
          )}
          {n > 0 && (
            <button type="button" className="inst__all" onClick={showAll}>
              Show all {n}
            </button>
          )}
        </div>

        <aside className="inst__panel" aria-label="Installations">
          {cur ? (
            <div className="inst__card" key={sel}>
              <p className="inst__card-k">
                <Pin size={13} aria-hidden="true" />
                Installation {pad(sel + 1)} of {n}
              </p>
              <h3 className="inst__card-name">{cur.area}</h3>
              <p className="inst__card-city">{cur.city}</p>
              <dl className="inst__card-facts">
                {curArea && curArea.idx.length > 1 && (
                  <div>
                    <dt>In this area</dt>
                    <dd>{curArea.idx.length} lifts</dd>
                  </div>
                )}
                {office && (
                  <div>
                    <dt>From our office</dt>
                    <dd>{fmtKm(km(office, cur))}</dd>
                  </div>
                )}
                {near && (
                  <div>
                    <dt>From you</dt>
                    <dd>{fmtKm(km(near, cur))}</dd>
                  </div>
                )}
                <div>
                  <dt>Position</dt>
                  <dd>
                    {cur.lat.toFixed(4)}, {cur.lng.toFixed(4)}
                  </dd>
                </div>
              </dl>
              <div className="inst__card-row">
                <a
                  className="inst__go"
                  href={`https://www.google.com/maps/dir/?api=1&destination=${cur.lat},${cur.lng}`}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  Directions <Arrow size={14} />
                </a>
                <button type="button" className="inst__close" onClick={() => setSel(null)} aria-label="Close">
                  <Close size={14} />
                </button>
              </div>
            </div>
          ) : (
            <div className="inst__intro">
              <p className="inst__count">
                <strong>{n ? pad(n) : '—'}</strong> installations · <strong>{areas.length}</strong> areas
              </p>
              <p className="inst__note">Press a pin on the map, or choose an area below.</p>
            </div>
          )}

          <div className="inst__tools">
            <label className="inst__search">
              <span className="sr-only">Search an area</span>
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search an area — Kompally, Banjara Hills…"
                disabled={!n}
              />
            </label>
            <button type="button" className="inst__near" onClick={findNear} disabled={!n}>
              <Pin size={14} aria-hidden="true" />
              Near me
            </button>
          </div>
          {geo && <p className="inst__geo">{geo}</p>}

          <ol ref={listRef} className="inst__list" aria-label="Areas">
            {shown.map((a) => {
              const on = cur && a.key === cur.area.toLowerCase()
              return (
                <li key={a.key} data-area={a.key}>
                  <button type="button" className={`inst__area ${on ? 'is-on' : ''}`} onClick={() => pickArea(a)} aria-current={on ? 'true' : undefined}>
                    <span className="inst__area-name">{a.area}</span>
                    <span className="inst__area-city">{a.city}</span>
                    <span className="inst__area-n">{near ? fmtKm(a.d) : `${a.idx.length} ${a.idx.length === 1 ? 'lift' : 'lifts'}`}</span>
                  </button>
                </li>
              )
            })}
            {n > 0 && !shown.length && <li className="inst__empty">No area matches that.</li>}
          </ol>
        </aside>
      </div>
    </section>
  )
}

/* the first view is the city, not the two or three jobs an hour out of it */
function cityBounds(L, items, office) {
  const core = office ? items.filter((it) => km(office, it) < 32) : items
  return L.latLngBounds((core.length > 10 ? core : items).map((it) => [it.lat, it.lng])).pad(0.04)
}

/* The pins are drawn on the map's one canvas rather than as 377 separate
   images: an image a pin was hundreds of layers for the browser to repaint
   every frame the page scrolled. Same teal teardrop, same shadow, same
   tooltip and click; the one that has been pressed is larger and
   white-faced, and drawn on top. */
const PIN_PATH = 'M12 1C6.5 1 2 5.4 2 10.9c0 7.4 8.6 18.1 9.3 19 .4.4 1 .4 1.4 0 .7-.9 9.3-11.6 9.3-19C22 5.4 17.5 1 12 1z'
let PinMarker = null
let path2d = null

function pinMarker(L, latlng, opts) {
  if (!PinMarker) {
    // the drawing is 24 x 32 with its tip at (12, 30); `k` scales it to the pin's height
    const scaleOf = (on) => (on ? 40 : 30) / 32
    PinMarker = L.CircleMarker.extend({
      options: { on: false, radius: 12, bubblingMouseEvents: false },
      setOn(on) {
        if (this.options.on === on) return this
        this.options.on = on
        if (on) this.bringToFront()
        return this.redraw()
      },
      _updateBounds() {
        const k = scaleOf(this.options.on)
        const p = this._point
        this._pxBounds = L.bounds(p.subtract([13 * k, 31 * k]), p.add([13 * k, 2 * k]))
      },
      _containsPoint(pt) {
        const k = scaleOf(this.options.on)
        return pt.distanceTo(this._point.subtract([0, 19 * k])) <= 12 * k
      },
      _updatePath() {
        const r = this._renderer
        if (!r._drawing || this._empty()) return
        const ctx = r._ctx
        const k = scaleOf(this.options.on)
        path2d ??= new Path2D(PIN_PATH)
        ctx.save()
        ctx.translate(this._point.x - 12 * k, this._point.y - 30 * k)
        ctx.scale(k, k)
        ctx.fillStyle = 'rgba(0,0,0,0.22)'
        ctx.beginPath()
        ctx.ellipse(12, 30.4, 4.2, 1.4, 0, 0, Math.PI * 2)
        ctx.fill()
        ctx.fillStyle = this.options.on ? '#ffffff' : '#2ec9ca'
        ctx.strokeStyle = '#066f70'
        ctx.lineWidth = 1.5
        ctx.fill(path2d)
        ctx.stroke(path2d)
        ctx.fillStyle = '#066f70'
        ctx.beginPath()
        ctx.arc(12, 11, 3.6, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
      },
    })
  }
  return new PinMarker(latlng, opts)
}
