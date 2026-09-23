/**
 * One page's analytics, reached by clicking a row in Top Pages.
 *
 * The path arrives as a query parameter rather than a route segment, because a
 * page path contains slashes of its own: nesting `/lifts/home-elevator` under a
 * route segment is ambiguous to any router, and encoding it means decoding it
 * back out at every use. `?path=` sidesteps the whole problem.
 */

import { Link, useSearchParams } from 'react-router-dom'
import { useMemo } from 'react'

import { AreaChart, BarList, colorFor } from '../../components/charts'
import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fetchPageDetail } from '../../analytics-api'
import DateRangePicker from './DateRangePicker'
import { Panel, formatSeconds, rangeKey } from './panels'

import '../../analytics.css'

export default function PageDetail() {
  const [params, setParams] = useSearchParams()
  const path = params.get('path') || ''

  const range = useMemo(
    () => ({
      key: params.get('range') || '7d',
      start: params.get('start') || '',
      end: params.get('end') || '',
    }),
    [params],
  )

  const setRange = (next) => {
    const query = { path, range: next.key }
    if (next.key === 'custom') {
      query.start = next.start
      query.end = next.end
    }
    setParams(query, { replace: true })
  }

  const state = useAsync(
    (signal) => (path ? fetchPageDetail(range, path, { signal }) : Promise.resolve(null)),
    [path, rangeKey(range)],
  )

  if (!path) {
    return (
      <div className="cf-page">
        <EmptyState
          title="No page selected"
          body="Open a row from Top Pages to see its detail."
          action={
            <Link className="cf-btn cf-btn--ghost" to="/control/analytics">
              Back to analytics
            </Link>
          }
        />
      </div>
    )
  }

  if (state.loading && !state.data) return <Spinner label="Loading page analytics" />
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />

  const detail = state.data?.detail
  const series = detail?.series ?? []

  return (
    <div className="cf-page cf-analytics">
      <PageHeader
        eyebrow={
          <Link className="cf-link" to="/control/analytics">
            Analytics
          </Link>
        }
        title={path}
      >
        <DateRangePicker
          range={range}
          presets={state.data?.range?.presets ?? []}
          onChange={setRange}
        />
      </PageHeader>

      {!detail || detail.views === 0 ? (
        <EmptyState
          title="No views in this period"
          body="Nobody opened this page in the selected range. Try a wider one."
        />
      ) : (
        <>
          <div className="cf-ancards">
            <Fact label="Page views" value={detail.views.toLocaleString()} />
            <Fact label="Unique visitors" value={detail.visitors.toLocaleString()} />
            <Fact label="Avg. time on page" value={formatSeconds(detail.avg_seconds)} />
            <Fact
              label="Landings"
              value={detail.landings.toLocaleString()}
              note="Visits that started here"
            />
            <Fact
              label="Bounce rate"
              value={`${detail.bounce_rate}%`}
              note="Landed here and left"
            />
          </div>

          <Panel title="Views over time" className="cf-anpanel--chart">
            <AreaChart
              points={series}
              series={[
                { key: 'visitors', label: 'Unique visitors', color: 'var(--cf-accent)' },
                { key: 'page_views', label: 'Page views', color: '#7c9cbf' },
              ]}
            />
          </Panel>

          <div className="cf-angrid">
            <Panel title="Where they went next" subtitle="Other pages in the same visit">
              <BarList
                rows={(detail.next_pages ?? []).map((row) => ({ label: row.path, ...row }))}
                valueKey="views"
                emptyLabel="No onward journeys recorded."
              />
            </Panel>

            <Panel title="How they arrived" subtitle="Across the whole site in this period">
              <BarList
                rows={(detail.channels ?? []).map((row, index) => ({
                  ...row,
                  color: colorFor(index),
                }))}
              />
            </Panel>
          </div>
        </>
      )}
    </div>
  )
}

function Fact({ label, value, note }) {
  return (
    <article className="cf-ancard">
      <header className="cf-ancard__head">
        <p className="cf-ancard__label">{label}</p>
      </header>
      <p className="cf-ancard__value">{value}</p>
      {note && (
        <footer className="cf-ancard__foot">
          <span className="cf-ancard__note">{note}</span>
        </footer>
      )}
    </article>
  )
}
