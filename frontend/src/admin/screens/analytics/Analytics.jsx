/**
 * The analytics dashboard.
 *
 * This component owns two things and delegates everything else: the selected
 * date range, and the summary row at the top. Every other section is a panel
 * that fetches for itself (see `panels.jsx`), so a slow query in one place does
 * not hold up the rest of the screen and a failure in one panel does not blank
 * the others.
 *
 * The range lives in the URL rather than in component state, which is what
 * makes "last month's numbers" a link somebody can send to a colleague, and
 * what makes the browser's back button behave the way a reader expects after
 * changing the filter three times.
 */

import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import { AreaChart } from '../../components/charts'
import { ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { exportUrl, fetchOverview, fetchVisitors } from '../../analytics-api'
import DateRangePicker from './DateRangePicker'
import {
  DeviceBreakdown,
  Geography,
  LiveVisitors,
  Panel,
  PanelState,
  StatCard,
  TopPages,
  TrafficOverview,
  TrafficSources,
  rangeKey,
} from './panels'

import '../../analytics.css'

export default function Analytics() {
  const [params, setParams] = useSearchParams()

  const range = useMemo(
    () => ({
      key: params.get('range') || '7d',
      start: params.get('start') || '',
      end: params.get('end') || '',
    }),
    [params],
  )

  const setRange = (next) => {
    const query = { range: next.key }
    if (next.key === 'custom') {
      query.start = next.start
      query.end = next.end
    }
    // `replace` so changing the filter repeatedly does not bury the page the
    // reader arrived from under a dozen history entries.
    setParams(query, { replace: true })
  }

  const overview = useAsync((signal) => fetchOverview(range, { signal }), [rangeKey(range)])

  if (overview.loading && !overview.data) return <Spinner label="Loading analytics" />
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.reload} />

  const { cards = [], traffic, has_data: hasData } = overview.data ?? {}

  return (
    <div className="cf-page cf-analytics">
      <PageHeader eyebrow="Website" title="Analytics">
        <DateRangePicker
          range={range}
          presets={overview.data?.range?.presets ?? []}
          onChange={setRange}
        />
        {/* A link, not a fetch: the browser handles the download, the progress
            and the cancel, and the session cookie travels with it. */}
        <a className="cf-btn cf-btn--ghost" href={exportUrl(range)}>
          Export report
        </a>
      </PageHeader>

      {/* Every number below is counted from real page views. When there are
          none, the cards read zero and this explains why — the one thing a
          dashboard must never do is fill an empty table with a plausible
          number, because there is then no way to tell the two apart. */}
      {!hasData && (
        <p className="cf-notice" role="status">
          <strong>No visitor data yet.</strong> Analytics will appear when visitors visit your
          website. Tracking is already running on every public page.
        </p>
      )}

      <div className="cf-ancards">
        {cards.map((card) => (
          <StatCard key={card.key} card={card} />
        ))}
      </div>

      <VisitorsChart range={range} />

      {traffic && (
        <div className="cf-angrid cf-angrid--wide">
          <Panel title="Website traffic" subtitle="How this period behaved">
            <TrafficOverview
              traffic={{
                ...traffic,
                avg_session_display:
                  cards.find((card) => card.key === 'avg_session')?.display ?? '—',
              }}
            />
          </Panel>
          <LiveVisitors />
        </div>
      )}

      <div className="cf-angrid">
        <TrafficSources range={range} />
        <DeviceBreakdown range={range} />
      </div>

      <TopPages range={range} />

      <Geography range={range} />
    </div>
  )
}

/**
 * The main chart.
 *
 * Its own component so that changing the range refetches the series without
 * re-running the summary query, and so the chart can show its own spinner in
 * place rather than replacing the whole screen.
 */
function VisitorsChart({ range }) {
  const state = useAsync((signal) => fetchVisitors(range, { signal }), [rangeKey(range)])
  const series = state.data?.series ?? []
  const empty = !state.loading && series.every((point) => !point.visitors && !point.page_views)

  return (
    <Panel
      title="Visitors & page views"
      subtitle={GRANULARITY_NOTE[state.data?.granularity] ?? ''}
      className="cf-anpanel--chart"
    >
      <PanelState
        state={state}
        isEmpty={empty}
        emptyTitle="Nothing in this period"
        emptyBody="Try a wider date range, or check back once the site has had visitors."
      >
        <AreaChart
          points={series}
          series={[
            { key: 'visitors', label: 'Unique visitors', color: 'var(--cf-accent)' },
            { key: 'page_views', label: 'Page views', color: '#7c9cbf' },
          ]}
        />
      </PanelState>
    </Panel>
  )
}

const GRANULARITY_NOTE = {
  hour: 'By hour',
  day: 'By day',
  month: 'By month',
}
