import { Link, useNavigate } from 'react-router-dom'

import { formatDate } from './Field'

/**
 * The list view's table, for every collection.
 *
 * Columns come from the schema's `list_display`; a cell prefers the server's
 * `_labels` entry over the raw value, which is what turns a foreign key into a
 * lift's name and a choice value into its wording without a second request.
 */

export default function DataTable({
  schema,
  rows,
  selected,
  onToggle,
  onToggleAll,
  ordering,
  onSort,
  onInlineChange,
  busyId,
}) {
  const navigate = useNavigate()
  const columns = schema.list_display
  const byName = Object.fromEntries(schema.fields.map((f) => [f.name, f]))
  const editable = new Set(schema.list_editable)
  const allChecked = rows.length > 0 && rows.every((row) => selected.has(row.id))

  const handleRowClick = (event, rowId) => {
    // Ignore clicks on checkboxes, inline selects, buttons or links
    if (
      event.target.tagName === 'INPUT' ||
      event.target.tagName === 'SELECT' ||
      event.target.tagName === 'BUTTON' ||
      event.target.tagName === 'A' ||
      event.target.closest('.cf-table__check') ||
      event.target.closest('.cf-toggle')
    ) {
      return
    }
    navigate(`/control/${schema.key}/${rowId}`)
  }

  return (
    <div className="cf-table__scroll">
      <table className="cf-table">
        <thead>
          <tr>
            <th className="cf-table__check">
              <input
                type="checkbox"
                checked={allChecked}
                onChange={(e) => onToggleAll(e.target.checked)}
                aria-label={allChecked ? 'Clear selection' : 'Select every row on this page'}
              />
            </th>
            {columns.map((name) => (
              <HeaderCell
                key={name}
                name={name}
                field={byName[name]}
                sortable={schema.ordering_fields.includes(name)}
                ordering={ordering}
                onSort={onSort}
              />
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className={selected.has(row.id) ? 'is-selected' : undefined}
              onClick={(e) => handleRowClick(e, row.id)}
              style={{ cursor: 'pointer' }}
            >
              <td className="cf-table__check">
                <input
                  type="checkbox"
                  checked={selected.has(row.id)}
                  onChange={() => onToggle(row.id)}
                  aria-label={`Select ${row._str}`}
                />
              </td>

              {columns.map((name, index) => (
                <td key={name} data-column={name}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <Cell
                      row={row}
                      name={name}
                      field={byName[name]}
                      resource={schema.key}
                      editable={editable.has(name)}
                      onInlineChange={onInlineChange}
                      busy={busyId === row.id}
                    />
                    {index === 0 && row.attachments && Array.isArray(row.attachments) && row.attachments.length > 0 && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          background: '#e0f2fe',
                          color: '#0369a1',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontWeight: 600,
                        }}
                        title={`${row.attachments.length} attachment(s)`}
                      >
                        📎 {row.attachments.length}
                      </span>
                    )}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function HeaderCell({ name, field, sortable, ordering, onSort }) {
  const label = field?.label ?? (name === '__str__' ? 'Name' : humanise(name))
  if (!sortable) return <th scope="col">{label}</th>

  const active = ordering === name || ordering === `-${name}`
  const descending = ordering === `-${name}`
  return (
    <th scope="col" aria-sort={active ? (descending ? 'descending' : 'ascending') : 'none'}>
      <button
        type="button"
        className={`cf-sort${active ? ' is-active' : ''}`}
        onClick={() => onSort(descending ? name : `-${name}`)}
      >
        {label}
        <span className="cf-sort__mark" aria-hidden="true">
          {active ? (descending ? '↓' : '↑') : '↕'}
        </span>
      </button>
    </th>
  )
}

function Cell({ row, name, field, resource, editable, onInlineChange, busy }) {
  if (name === '__str__') return <strong className="cf-cell__title">{row._str}</strong>

  const value = row[name]
  const label = row._labels?.[name]

  // Publishing toggles and ordering are what a list is actually used to change;
  // making them inline saves opening thirty records to hide one.
  if (editable && field?.type === 'boolean') {
    return (
      <label className="cf-toggle">
        <input
          type="checkbox"
          checked={Boolean(value)}
          disabled={busy}
          onChange={(e) => onInlineChange(row.id, name, e.target.checked)}
        />
        <span className="cf-toggle__track" aria-hidden="true" />
        <span className="cf-sr">{field.label}</span>
      </label>
    )
  }

  if (editable && field?.type === 'choice') {
    return (
      <select
        className="cf-input cf-input--inline"
        value={value ?? ''}
        disabled={busy}
        aria-label={field.label}
        onChange={(e) => onInlineChange(row.id, name, e.target.value)}
      >
        {field.choices?.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    )
  }

  if (editable && (field?.type === 'integer' || field?.type === 'float')) {
    return (
      <input
        className="cf-input cf-input--inline cf-input--number"
        type="number"
        value={value ?? 0}
        disabled={busy}
        aria-label={field.label}
        onChange={(e) => onInlineChange(row.id, name, Number(e.target.value))}
      />
    )
  }

  return <ReadCell field={field} value={value} label={label} resource={resource} />
}

function ReadCell({ field, value, label }) {
  if (value === null || value === undefined || value === '') {
    return <span className="cf-cell__empty">—</span>
  }

  switch (field?.type) {
    case 'boolean':
      return (
        <span className={`cf-pill cf-pill--${value ? 'on' : 'off'}`}>{value ? 'Yes' : 'No'}</span>
      )
    case 'choice':
      return <span className={`cf-pill cf-pill--${slug(value)}`}>{label ?? value}</span>
    case 'color':
      return (
        <span className="cf-swatch">
          <span className="cf-swatch__chip" style={{ background: value }} aria-hidden="true" />
          <code>{value}</code>
        </span>
      )
    case 'datetime':
    case 'date':
      return <time dateTime={value}>{formatDate(value)}</time>
    case 'image':
      return <img className="cf-cell__thumb" src={value} alt="" width="48" height="32" />
    case 'reference':
    case 'multi_reference':
      return <span>{label ?? value}</span>
    case 'text':
      return <span className="cf-cell__clip">{String(value)}</span>
    default:
      return <span>{label ?? String(value)}</span>
  }
}

const humanise = (name) => name.replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase())
const slug = (value) => String(value).replaceAll('_', '-').toLowerCase()
