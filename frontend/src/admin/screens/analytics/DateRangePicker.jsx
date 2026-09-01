/**
 * The date filter.
 *
 * A native `<select>` for the presets rather than a custom dropdown: it is
 * keyboard-accessible, screen-reader-correct and touch-friendly on a phone
 * without any of it being written here, and this control has no requirement a
 * custom menu would satisfy better.
 *
 * "Custom range" reveals two date inputs and applies only when both are filled,
 * so a half-typed range never refetches the whole dashboard against a window
 * the reader has not finished describing.
 */

import { useEffect, useState } from 'react'

export default function DateRangePicker({ range, presets = [], onChange }) {
  const isCustom = range.key === 'custom'
  const [start, setStart] = useState(range.start)
  const [end, setEnd] = useState(range.end)

  // Keep the inputs in step when the range changes from outside — a back
  // button, or a link somebody was sent.
  useEffect(() => {
    setStart(range.start)
    setEnd(range.end)
  }, [range.start, range.end])

  const options = presets.length ? presets : FALLBACK_PRESETS

  const choose = (key) => {
    if (key !== 'custom') return onChange({ key })
    // Open the custom fields on a sensible default rather than empty ones, so
    // choosing "Custom range" shows a working dashboard immediately.
    const today = new Date()
    const weekAgo = new Date(today.getTime() - 6 * 86400000)
    onChange({ key: 'custom', start: start || iso(weekAgo), end: end || iso(today) })
  }

  const applyCustom = (nextStart, nextEnd) => {
    setStart(nextStart)
    setEnd(nextEnd)
    if (nextStart && nextEnd) onChange({ key: 'custom', start: nextStart, end: nextEnd })
  }

  return (
    <div className="cf-anrange">
      <label className="cf-sr" htmlFor="cf-anrange-preset">
        Date range
      </label>
      <select
        id="cf-anrange-preset"
        className="cf-input cf-input--select cf-input--inline"
        value={range.key}
        onChange={(event) => choose(event.target.value)}
      >
        {options.map((preset) => (
          <option key={preset.key} value={preset.key}>
            {preset.label}
          </option>
        ))}
      </select>

      {isCustom && (
        <span className="cf-anrange__custom">
          <label className="cf-sr" htmlFor="cf-anrange-start">
            Start date
          </label>
          <input
            id="cf-anrange-start"
            type="date"
            className="cf-input cf-input--inline"
            value={start}
            max={end || undefined}
            onChange={(event) => applyCustom(event.target.value, end)}
          />
          <span aria-hidden="true">–</span>
          <label className="cf-sr" htmlFor="cf-anrange-end">
            End date
          </label>
          <input
            id="cf-anrange-end"
            type="date"
            className="cf-input cf-input--inline"
            value={end}
            min={start || undefined}
            max={iso(new Date())}
            onChange={(event) => applyCustom(start, event.target.value)}
          />
        </span>
      )}
    </div>
  )
}

/** Used only until the first response arrives, so the control is never empty. */
const FALLBACK_PRESETS = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
  { key: 'this_month', label: 'This month' },
  { key: 'last_month', label: 'Last month' },
  { key: '12m', label: 'Last 12 months' },
  { key: 'custom', label: 'Custom range' },
]

function iso(date) {
  // Local calendar date, not UTC: `toISOString` would roll to the previous day
  // for anyone east of Greenwich before their morning.
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}
