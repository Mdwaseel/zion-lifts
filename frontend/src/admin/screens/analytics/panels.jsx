/**
 * The pieces the analytics screens are assembled from.
 *
 * Each panel owns its own fetch. That is the important decision in this file:
 * the dashboard is eight independent reports, and having one component load all
 * of them would mean the slowest query decides when anything appears, one
 * failure blanks the screen, and changing the date range refetches panels that
 * did not need it. Owning the fetch also means each panel carries its own
 * loading, error and empty states, which is why they are consistent.
 *
 * Every panel takes `range` and refetches when it changes — that is the whole
 * contract, and it is what makes the date filter work without any coordination.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { BarList, DonutChart, colorFor, compact } from '../../components/charts'
import { EmptyState, ErrorState, Pagination, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fetchDevices, fetchPages, fetchRealtime, fetchSources } from '../../analytics-api'

/* ==========================================================================
   Frame
   ========================================================================== */

/** A titled card. Every panel below sits in one, so they align without effort. */
export function Panel({ title, subtitle, actions, children, className = '' }) {
  return (
    <section className={`cf-anpanel ${className}`}>
      <header className="cf-anpanel__head">
        <div>
          <h2 className="cf-anpanel__title">{title}</h2>
          {subtitle && <p className="cf-anpanel__sub">{subtitle}</p>}
        </div>
        {actions && <div className="cf-anpanel__actions">{actions}</div>}
      </header>
      <div className="cf-anpanel__body">{children}</div>
    </section>
  )
}

/**
 * Loading / error / empty, in the order they can occur.
 *
 * Hoisted into one component because the alternative is the same four-branch
 * ternary in eight panels, and the eighth one always renders emptiness slightly
 * differently from the other seven.
 */
export function PanelState({ state, isEmpty, emptyTitle, emptyBody, children }) {
  if (state.loading && !state.data) return <Spinner label="Loading" />
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />
  if (isEmpty) return <EmptyState title={emptyTitle} body={emptyBody} />
  return children
}

/* ==========================================================================
   Summary cards
   ========================================================================== */

/**
 * One statistic.
 *
 * `change` is null whenever there was no previous period to compare against,
 * and the card then shows nothing rather than an arrow — a dashboard that
 * reports "↑ 100%" on its first day teaches people to distrust it.
 */
export function StatCard({ card }) {
  const { change, direction, is_live: live } = card
  return (
    <article className="cf-ancard">
      <header className="cf-ancard__head">
        <span className="cf-ancard__icon" aria-hidden="true">
          {ICONS[card.key] ?? ICONS.default}
        </span>
        <p className="cf-ancard__label">{card.label}</p>
      </header>
      <p className="cf-ancard__value">{card.display}</p>
      <footer className="cf-ancard__foot">
        {live ? (
          <span className="cf-ancard__live">
            <span className="cf-ancard__pulse" aria-hidden="true" />
            Live
          </span>
        ) : change === null || change === undefined ? (
          <span className="cf-ancard__flat">No earlier period</span>
        ) : (
          <span className={`cf-ancard__delta cf-ancard__delta--${direction}`}>
            {direction === 'up' ? '↑' : '↓'} {Math.abs(change)}%
          </span>
        )}
        <span className="cf-ancard__note">{card.description}</span>
      </footer>
    </article>
  )
}

// Deliberately text, not an icon set: eight glyphs do not justify a dependency
// or an SVG sprite, and these read correctly at every size and in both themes.
const ICONS = {
  visitors: '◎',
  page_views: '▤',
  visitors_today: '☀',
  page_views_today: '▦',
  visitors_week: '▥',
  visitors_month: '▣',
  online: '◉',
  avg_session: '◷',
  default: '▪',
}

/* ==========================================================================
   Traffic overview
   ========================================================================== */

export function TrafficOverview({ traffic }) {
  const rows = [
    ['Total visitors', traffic.visitors.toLocaleString()],
    ['New visitors', traffic.new_visitors.toLocaleString()],
    ['Returning visitors', traffic.returning_visitors.toLocaleString()],
    ['Total page views', traffic.page_views.toLocaleString()],
    ['Sessions', traffic.sessions.toLocaleString()],
    ['Pages per visit', traffic.pages_per_session],
    ['Avg. session duration', traffic.avg_session_display],
    ['Bounce rate', `${traffic.bounce_rate}%`],
  ]

  return (
    <div className="cf-antraffic">
      <div className="cf-antraffic__split">
        <p className="cf-antraffic__caption">New vs returning</p>
        <div
          className="cf-antraffic__bar"
          role="img"
          aria-label={`${traffic.new_share}% new visitors, ${(100 - traffic.new_share).toFixed(
            1,
          )}% returning`}
        >
          <span className="cf-antraffic__new" style={{ width: `${traffic.new_share}%` }} />
        </div>
        <p className="cf-antraffic__keys">
          <span>
            <i className="cf-antraffic__key cf-antraffic__key--new" aria-hidden="true" /> New{' '}
            {traffic.new_share}%
          </span>
          <span>
            <i className="cf-antraffic__key" aria-hidden="true" /> Returning{' '}
            {(100 - traffic.new_share).toFixed(1)}%
          </span>
        </p>
      </div>

      <dl className="cf-anfacts">
        {rows.map(([label, value]) => (
          <div className="cf-anfacts__row" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/* ==========================================================================
   Top pages
   ========================================================================== */

export function TopPages({ range }) {
  const [page, setPage] = useState(1)
  const state = useAsync(
    (signal) => fetchPages(range, { page, pageSize: 10 }, { signal }),
    [rangeKey(range), page],
  )

  const rows = state.data?.results ?? []

  return (
    <Panel title="Top pages" subtitle="Most visited pages in this period">
      <PanelState
        state={state}
        isEmpty={!state.loading && rows.length === 0}
        emptyTitle="No page views yet"
        emptyBody="Once people start browsing the site, the pages they open appear here."
      >
        <>
          <div className="cf-table__scroll">
            <table className="cf-table cf-table--compact">
              <thead>
                <tr>
                  <th scope="col">Page</th>
                  <th scope="col" className="cf-cell__num">Views</th>
                  <th scope="col" className="cf-cell__num">Visitors</th>
                  <th scope="col" className="cf-cell__num">Avg. time</th>
                  <th scope="col" className="cf-cell__num">Bounce</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.path}>
                    <td>
                      <Link
                        className="cf-link"
                        to={`/control/analytics/page?path=${encodeURIComponent(row.path)}`}
                      >
                        {row.path}
                      </Link>
                    </td>
                    <td className="cf-cell__num">{row.views.toLocaleString()}</td>
                    <td className="cf-cell__num">{row.visitors.toLocaleString()}</td>
                    <td className="cf-cell__num">{formatSeconds(row.avg_seconds)}</td>
                    <td className="cf-cell__num">{row.bounce_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={state.data?.page ?? 1}
            pages={state.data?.pages ?? 1}
            count={state.data?.count ?? 0}
            pageSize={state.data?.page_size ?? 10}
            onPage={setPage}
          />
        </>
      </PanelState>
    </Panel>
  )
}

/* ==========================================================================
   Traffic sources
   ========================================================================== */

export function TrafficSources({ range }) {
  const state = useAsync((signal) => fetchSources(range, { signal }), [rangeKey(range)])
  const channels = state.data?.channels ?? []
  const total = channels.reduce((sum, row) => sum + row.visitors, 0)

  return (
    <Panel title="Traffic sources" subtitle="Where visitors came from">
      <PanelState
        state={state}
        isEmpty={!state.loading && channels.length === 0}
        emptyTitle="No traffic yet"
        emptyBody="Sources appear once the site has visitors."
      >
        <div className="cf-anchart-row">
          <DonutChart
            slices={channels.map((row, index) => ({
              key: row.key,
              label: row.label,
              value: row.visitors,
              color: colorFor(index),
            }))}
            centreValue={compact(total)}
            centreLabel="visitors"
          />
          <div className="cf-anchart-row__table">
            <table className="cf-table cf-table--compact">
              <thead>
                <tr>
                  <th scope="col">Source</th>
                  <th scope="col" className="cf-cell__num">Visitors</th>
                  <th scope="col" className="cf-cell__num">Share</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((row, index) => (
                  <tr key={row.key}>
                    <td>
                      <span
                        className="cf-chart__swatch"
                        style={{ background: colorFor(index) }}
                        aria-hidden="true"
                      />
                      {row.label}
                    </td>
                    <td className="cf-cell__num">{row.visitors.toLocaleString()}</td>
                    <td className="cf-cell__num">{row.percentage}%</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {state.data?.referrers?.length > 0 && (
              <details className="cf-andetails">
                <summary>Referring sites</summary>
                <BarList
                  rows={state.data.referrers.map((row) => ({ label: row.host, ...row }))}
                />
              </details>
            )}
          </div>
        </div>
      </PanelState>
    </Panel>
  )
}

/* ==========================================================================
   Devices, browsers, operating systems
   ========================================================================== */

export function DeviceBreakdown({ range }) {
  const state = useAsync((signal) => fetchDevices(range, { signal }), [rangeKey(range)])
  const devices = state.data?.devices ?? []
  const total = devices.reduce((sum, row) => sum + row.visitors, 0)

  return (
    <Panel title="Devices" subtitle="What visitors are browsing on">
      <PanelState
        state={state}
        isEmpty={!state.loading && devices.length === 0}
        emptyTitle="No device data yet"
        emptyBody="Device information is recorded with the first page view."
      >
        <>
          <div className="cf-anchart-row">
            <DonutChart
              slices={devices.map((row, index) => ({
                key: row.key,
                label: row.label,
                value: row.visitors,
                color: colorFor(index),
              }))}
              centreValue={compact(total)}
              centreLabel="visitors"
            />
            <ul className="cf-anlegend">
              {devices.map((row, index) => (
                <li key={row.key}>
                  <span
                    className="cf-chart__swatch"
                    style={{ background: colorFor(index) }}
                    aria-hidden="true"
                  />
                  <span className="cf-anlegend__label">{row.label}</span>
                  <strong>{row.percentage}%</strong>
                </li>
              ))}
            </ul>
          </div>

          <div className="cf-ansplit">
            <div>
              <h3 className="cf-anpanel__minor">Browsers</h3>
              <BarList rows={state.data?.browsers ?? []} />
            </div>
            <div>
              <h3 className="cf-anpanel__minor">Operating systems</h3>
              <BarList rows={state.data?.operating_systems ?? []} />
            </div>
          </div>
        </>
      </PanelState>
    </Panel>
  )
}

/* ==========================================================================
   Live visitors and recent activity
   ========================================================================== */

/**
 * Polls the realtime endpoint on an interval.
 *
 * `useAsync` reloads when its deps change, so a counter ticking on a timer is
 * what drives the refresh. Polling rather than a socket: this is one cheap
 * indexed query every fifteen seconds for however many staff have the tab open,
 * against a persistent connection, a Redis channel and a deployment story — and
 * "how many people are on the site" does not need sub-second latency.
 */
export function LiveVisitors({ intervalMs = 15000 }) {
  const [tick, setTick] = useState(0)
  const [page, setPage] = useState(1)

  useIntervalTick(setTick, intervalMs)

  const state = useAsync(
    (signal) => fetchRealtime({ page, pageSize: 12 }, { signal }),
    [tick, page],
  )
  const rows = state.data?.results ?? []

  return (
    <Panel
      title="Live visitors"
      subtitle={`Refreshes every ${Math.round(intervalMs / 1000)} seconds`}
      actions={
        <span className="cf-anonline">
          <span className="cf-ancard__pulse" aria-hidden="true" />
          <strong>{state.data?.online ?? 0}</strong> online now
        </span>
      }
    >
      <PanelState
        state={state}
        isEmpty={!state.loading && rows.length === 0}
        emptyTitle="No activity yet"
        emptyBody="Page views appear here as they happen."
      >
        <>
          <div className="cf-table__scroll">
            <table className="cf-table cf-table--compact">
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Page</th>
                  <th scope="col">Device</th>
                  <th scope="col">Source</th>
                  <th scope="col">Location</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className="cf-cell__meta">
                      {row.time}
                      <span className="cf-cell__sub">{row.ago}</span>
                    </td>
                    <td>{row.path}</td>
                    <td>{row.device}</td>
                    <td>{row.channel}</td>
                    <td>{row.location || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={state.data?.page ?? 1}
            pages={state.data?.pages ?? 1}
            count={state.data?.count ?? 0}
            pageSize={state.data?.page_size ?? 12}
            onPage={setPage}
          />
        </>
      </PanelState>
    </Panel>
  )
}

/* ==========================================================================
   Shared
   ========================================================================== */

function useIntervalTick(setTick, intervalMs) {
  useEffect(() => {
    const id = setInterval(() => {
      // Skip while the tab is hidden: a dashboard left open overnight should
      // not spend the night polling, and the first tick after it is looked at
      // again refreshes it anyway.
      if (document.visibilityState === 'visible') setTick((n) => n + 1)
    }, intervalMs)
    return () => clearInterval(id)
  }, [setTick, intervalMs])
}

/** A stable dependency for a range object, so panels refetch exactly when it changes. */
export function rangeKey(range) {
  return range.key === 'custom' ? `custom:${range.start}:${range.end}` : range.key
}

export function formatSeconds(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  if (!total) return '—'
  const minutes = Math.floor(total / 60)
  if (minutes >= 60) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
  return minutes ? `${minutes}m ${total % 60}s` : `${total}s`
}
