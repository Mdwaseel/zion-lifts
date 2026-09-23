/**
 * The charts the analytics dashboard draws, as inline SVG.
 *
 * No charting library, on purpose. The three shapes this dashboard needs — a
 * two-series area chart, a doughnut and a labelled bar list — are a few hundred
 * lines of SVG between them, against 50–150 kB gzipped for Chart.js or Recharts
 * plus a second way of doing layout, theming and accessibility that would agree
 * with none of the panel's existing CSS. The rest of this codebase draws its own
 * SVG (see the home page's schematic and ascent sections); this follows it.
 *
 * All three take the same shape of data the API returns and are responsive by
 * construction: the SVG scales with a `viewBox`, so there is no resize observer
 * and no reflow-on-resize path to get wrong.
 *
 * Accessibility: every chart is `role="img"` with a summary label, and the
 * numbers behind it are always also present as a table or list next to it. A
 * chart is a second way to read the data here, never the only one.
 */

import { useId, useMemo, useState } from 'react'

/* ==========================================================================
   Area + line chart — "Visitors & Page Views"
   ========================================================================== */

const PAD = { top: 16, right: 12, bottom: 26, left: 44 }

/**
 * Two series over time, as filled areas with a hover readout.
 *
 * The viewBox is a fixed 720×260 and the element is width:100% — so the chart
 * scales to its container without JavaScript measuring anything. The cost is
 * that stroke widths and text scale too, which at the range of widths a
 * dashboard panel actually takes is a feature rather than a problem.
 *
 * Hover is one transparent rect per bucket rather than a mousemove listener
 * doing inverse-scale maths: it is less code, it gives keyboard focus targets
 * for free, and it cannot drift out of step with the plotted geometry.
 */
export function AreaChart({
  points = [],
  series = [],
  height = 260,
  emptyLabel = 'No data in this period',
}) {
  const uid = useId()
  const [active, setActive] = useState(null)

  const width = 720
  const plot = {
    width: width - PAD.left - PAD.right,
    height: height - PAD.top - PAD.bottom,
  }

  const max = useMemo(() => {
    const highest = Math.max(
      0,
      ...points.flatMap((point) => series.map((s) => Number(point[s.key]) || 0)),
    )
    // Never zero: a flat-zero chart still needs a scale, or every point lands
    // on a division by zero and the path becomes NaN.
    return highest > 0 ? niceCeiling(highest) : 1
  }, [points, series])

  if (!points.length) {
    return <p className="cf-chart__empty">{emptyLabel}</p>
  }

  const x = (index) =>
    PAD.left + (points.length === 1 ? plot.width / 2 : (index / (points.length - 1)) * plot.width)
  const y = (value) => PAD.top + plot.height - ((Number(value) || 0) / max) * plot.height

  const ticks = axisTicks(max)
  const labelEvery = Math.ceil(points.length / 8)
  const point = active === null ? null : points[active]

  return (
    <div className="cf-chart">
      <svg
        className="cf-chart__svg"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${series.map((s) => s.label).join(' and ')} over time`}
      >
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key} id={`${uid}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity="0.28" />
              <stop offset="100%" stopColor={s.color} stopOpacity="0.02" />
            </linearGradient>
          ))}
        </defs>

        {/* horizontal rules, behind everything */}
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              className="cf-chart__grid"
              x1={PAD.left}
              x2={width - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text className="cf-chart__tick" x={PAD.left - 8} y={y(tick) + 4} textAnchor="end">
              {compact(tick)}
            </text>
          </g>
        ))}

        {series.map((s) => (
          <g key={s.key}>
            <path
              d={areaPath(points, s.key, x, y, PAD.top + plot.height)}
              fill={`url(#${uid}-${s.key})`}
            />
            <path
              d={linePath(points, s.key, x, y)}
              fill="none"
              stroke={s.color}
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </g>
        ))}

        {/* the marker follows the hovered bucket */}
        {point &&
          series.map((s) => (
            <circle
              key={s.key}
              cx={x(active)}
              cy={y(point[s.key])}
              r="4"
              fill="var(--cf-surface)"
              stroke={s.color}
              strokeWidth="2"
            />
          ))}
        {point && (
          <line
            className="cf-chart__cursor"
            x1={x(active)}
            x2={x(active)}
            y1={PAD.top}
            y2={PAD.top + plot.height}
          />
        )}

        {/* x labels, thinned so they never collide */}
        {points.map((p, index) =>
          index % labelEvery === 0 ? (
            <text
              key={p.bucket ?? index}
              className="cf-chart__tick"
              x={x(index)}
              y={height - 8}
              textAnchor="middle"
            >
              {p.label}
            </text>
          ) : null,
        )}

        {/* one hit area per bucket: hoverable, focusable, always in step */}
        {points.map((p, index) => (
          <rect
            key={`hit-${p.bucket ?? index}`}
            x={x(index) - plot.width / points.length / 2}
            y={PAD.top}
            width={Math.max(1, plot.width / points.length)}
            height={plot.height}
            fill="transparent"
            tabIndex={0}
            role="button"
            aria-label={`${p.full_label ?? p.label}: ${series
              .map((s) => `${p[s.key]} ${s.label.toLowerCase()}`)
              .join(', ')}`}
            onMouseEnter={() => setActive(index)}
            onFocus={() => setActive(index)}
            onMouseLeave={() => setActive(null)}
            onBlur={() => setActive(null)}
          />
        ))}
      </svg>

      {point && (
        <div
          className="cf-chart__tip"
          // Clamped away from both edges so the tooltip never hangs off the
          // panel at the first or last bucket.
          style={{ left: `${clamp((x(active) / width) * 100, 12, 88)}%` }}
          role="status"
        >
          <p className="cf-chart__tip-when">{point.full_label ?? point.label}</p>
          {series.map((s) => (
            <p key={s.key} className="cf-chart__tip-row">
              <span className="cf-chart__swatch" style={{ background: s.color }} aria-hidden="true" />
              {s.label}
              <strong>{Number(point[s.key] ?? 0).toLocaleString()}</strong>
            </p>
          ))}
        </div>
      )}

      <ul className="cf-chart__legend">
        {series.map((s) => (
          <li key={s.key}>
            <span className="cf-chart__swatch" style={{ background: s.color }} aria-hidden="true" />
            {s.label}
          </li>
        ))}
      </ul>
    </div>
  )
}

function linePath(points, key, x, y) {
  return points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p[key])}`).join(' ')
}

function areaPath(points, key, x, y, baseline) {
  if (!points.length) return ''
  const line = linePath(points, key, x, y)
  return `${line} L${x(points.length - 1)},${baseline} L${x(0)},${baseline} Z`
}

/**
 * A round number at or above `value`, for the top of the axis.
 *
 * Without this the axis maxes at whatever the tallest bar happens to be, and
 * the gridlines read 137, 91.3, 45.7 — numbers nobody can compare at a glance.
 */
function niceCeiling(value) {
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const normalised = value / magnitude
  const step = normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10
  return step * magnitude
}

function axisTicks(max, count = 4) {
  return Array.from({ length: count + 1 }, (_, i) => (max / count) * i)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

/* ==========================================================================
   Doughnut — traffic sources, devices
   ========================================================================== */

/**
 * A doughnut, drawn as stroked arcs on one circle.
 *
 * `stroke-dasharray` on a circle rather than a wedge path per slice: an arc is
 * one number instead of two trigonometric endpoints, there is no large-arc flag
 * to get wrong past 180°, and a slice of exactly 100% renders correctly — which
 * the path version famously does not.
 */
export function DonutChart({ slices = [], size = 168, thickness = 22, centreLabel, centreValue }) {
  const total = slices.reduce((sum, slice) => sum + (Number(slice.value) || 0), 0)
  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius

  if (!total) {
    return (
      <div className="cf-donut cf-donut--empty" style={{ width: size, height: size }}>
        <span>No data</span>
      </div>
    )
  }

  let offset = 0
  return (
    <div className="cf-donut" style={{ width: size, height: size }}>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={slices
          .map((s) => `${s.label}: ${Math.round(((s.value || 0) / total) * 100)}%`)
          .join(', ')}
      >
        {/* -90° so the first slice starts at twelve o'clock, where a reader
            expects a pie to begin. */}
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {slices.map((slice) => {
            const fraction = (Number(slice.value) || 0) / total
            const length = fraction * circumference
            const arc = (
              <circle
                key={slice.key ?? slice.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={thickness}
                strokeDasharray={`${length} ${circumference - length}`}
                strokeDashoffset={-offset}
              />
            )
            offset += length
            return arc
          })}
        </g>
      </svg>
      {(centreValue !== undefined || centreLabel) && (
        <div className="cf-donut__centre">
          {centreValue !== undefined && <p className="cf-donut__value">{centreValue}</p>}
          {centreLabel && <p className="cf-donut__label">{centreLabel}</p>}
        </div>
      )}
    </div>
  )
}

/* ==========================================================================
   Bar list — browsers, operating systems, countries
   ========================================================================== */

/**
 * A labelled row with a proportional bar behind it.
 *
 * The bar is a background element rather than a chart: the number is the thing
 * being read, and the bar exists to make the ranking scannable without moving
 * the reader's eye to a separate axis.
 */
export function BarList({ rows = [], emptyLabel = 'No data', valueKey = 'visitors', format }) {
  if (!rows.length) return <p className="cf-chart__empty">{emptyLabel}</p>

  const max = Math.max(...rows.map((row) => Number(row[valueKey]) || 0), 1)

  return (
    <ul className="cf-bars">
      {rows.map((row) => {
        const value = Number(row[valueKey]) || 0
        return (
          <li className="cf-bars__row" key={row.key ?? row.label ?? row.name}>
            <span
              className="cf-bars__fill"
              style={{ width: `${(value / max) * 100}%` }}
              aria-hidden="true"
            />
            <span className="cf-bars__label">{row.label ?? row.name}</span>
            <span className="cf-bars__value">
              {format ? format(row) : value.toLocaleString()}
              {row.percentage !== undefined && (
                <span className="cf-bars__pct">{row.percentage}%</span>
              )}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

/* ==========================================================================
   Shared
   ========================================================================== */

/** Palette for the charts. Ordered so adjacent slices stay distinguishable. */
export const SERIES_COLORS = [
  'var(--cf-accent)',
  '#7c9cbf',
  '#c2a25a',
  '#7fa87f',
  '#b58585',
  '#8f83b5',
  '#5f9ea0',
  '#a89078',
]

export function colorFor(index) {
  return SERIES_COLORS[index % SERIES_COLORS.length]
}

/** 12.4k, 1.2M — the axis and card form for a number that would otherwise wrap. */
export function compact(value) {
  const n = Number(value) || 0
  if (Math.abs(n) >= 1_000_000) return `${trim(n / 1_000_000)}M`
  if (Math.abs(n) >= 10_000) return `${trim(n / 1000)}k`
  return Math.round(n).toLocaleString()
}

function trim(n) {
  return n.toFixed(1).replace(/\.0$/, '')
}
