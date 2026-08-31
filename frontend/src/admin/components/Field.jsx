import { useEffect, useMemo, useState } from 'react'

import { fetchOptions } from '../api'

/**
 * One form input, chosen by the field's type from the server's schema.
 *
 * This component is the reason there is one form screen rather than thirty:
 * every editable field in the project is one of these types, so a model gains a
 * field and the form grows a row without anyone writing React.
 *
 * Read-only fields render as text rather than disabled inputs — an enquiry is
 * almost entirely read-only, and a page of greyed-out boxes reads as broken.
 */

export default function Field({ field, value, onChange, error, resource, disabled }) {
  const id = `field-${field.name}`
  const describedBy = [error && `${id}-error`, field.help_text && `${id}-help`]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={`cf-field cf-field--${field.type}${error ? ' cf-field--error' : ''}`}>
      <label className="cf-field__label" htmlFor={id}>
        {field.label}
        {field.required && !field.readonly && (
          <span className="cf-field__req" aria-hidden="true">
            {' '}
            *
          </span>
        )}
      </label>

      {field.readonly ? (
        <ReadOnly field={field} value={value} />
      ) : (
        <Input
          id={id}
          field={field}
          value={value}
          onChange={onChange}
          resource={resource}
          disabled={disabled}
          describedBy={describedBy || undefined}
          invalid={Boolean(error)}
        />
      )}

      {field.help_text && (
        <p className="cf-field__help" id={`${id}-help`}>
          {field.help_text}
        </p>
      )}
      {error && (
        <p className="cf-field__error" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

/** What the customer sent, or what the system set. Shown, never edited. */
function ReadOnly({ field, value }) {
  if (value === null || value === undefined || value === '') {
    return <p className="cf-readonly cf-readonly--empty">—</p>
  }
  if (field.type === 'boolean') return <p className="cf-readonly">{value ? 'Yes' : 'No'}</p>
  if (field.type === 'datetime' || field.type === 'date') {
    return <p className="cf-readonly">{formatDate(value)}</p>
  }
  if (field.type === 'json') {
    return <pre className="cf-readonly cf-readonly--json">{JSON.stringify(value, null, 2)}</pre>
  }
  return <p className="cf-readonly">{String(value)}</p>
}

function Input({ id, field, value, onChange, resource, disabled, describedBy, invalid }) {
  const common = {
    id,
    name: field.name,
    disabled,
    'aria-describedby': describedBy,
    'aria-invalid': invalid ? 'true' : undefined,
  }

  switch (field.type) {
    case 'text':
      return (
        <textarea
          {...common}
          className="cf-input cf-input--area"
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
          rows={6}
        />
      )

    case 'boolean':
      return (
        <label className="cf-switch">
          <input
            {...common}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span className="cf-switch__track" aria-hidden="true" />
          <span className="cf-switch__text">{value ? 'Yes' : 'No'}</span>
        </label>
      )

    case 'integer':
    case 'float':
      return (
        <input
          {...common}
          className="cf-input"
          type="number"
          step={field.type === 'float' ? 'any' : 1}
          value={value ?? ''}
          // '' rather than 0 for an emptied box, so clearing a field does not
          // silently write a zero.
          onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
        />
      )

    case 'date':
      return (
        <input
          {...common}
          className="cf-input"
          type="date"
          value={(value ?? '').slice(0, 10)}
          onChange={(e) => onChange(e.target.value)}
        />
      )

    case 'datetime':
      return (
        <input
          {...common}
          className="cf-input"
          type="datetime-local"
          // The input wants "YYYY-MM-DDTHH:MM"; the API sends ISO with seconds
          // and a zone.
          value={(value ?? '').slice(0, 16)}
          onChange={(e) => onChange(e.target.value)}
        />
      )

    case 'choice':
      return (
        <select
          {...common}
          className="cf-input cf-input--select"
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">—</option>
          {field.choices?.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
      )

    case 'color':
      return <ColorInput {...common} value={value} onChange={onChange} />

    case 'reference':
      return (
        <ReferenceInput {...common} field={field} value={value} onChange={onChange} resource={resource} />
      )

    case 'multi_reference':
      return (
        <MultiReferenceInput
          {...common}
          field={field}
          value={value}
          onChange={onChange}
          resource={resource}
        />
      )

    case 'image':
    case 'file':
      return <FileInput {...common} field={field} value={value} onChange={onChange} />

    case 'json':
      return <JsonInput {...common} value={value} onChange={onChange} />

    default:
      return (
        <input
          {...common}
          className="cf-input"
          type={inputTypeFor(field.type)}
          value={value ?? ''}
          maxLength={field.max_length}
          onChange={(e) => onChange(e.target.value)}
        />
      )
  }
}

function inputTypeFor(type) {
  if (type === 'email') return 'email'
  if (type === 'url') return 'url'
  return 'text'
}

/** A swatch and the hex beside it: the picker is fast, the text is precise. */
function ColorInput({ value, onChange, ...rest }) {
  const hex = /^#[0-9a-f]{6}$/i.test(value ?? '') ? value : '#000000'
  return (
    <div className="cf-color">
      <input
        type="color"
        className="cf-color__swatch"
        value={hex}
        onChange={(e) => onChange(e.target.value)}
        aria-hidden="true"
        tabIndex={-1}
        disabled={rest.disabled}
      />
      <input
        {...rest}
        className="cf-input cf-color__hex"
        type="text"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder="#000000"
        spellCheck="false"
      />
    </div>
  )
}

/**
 * Options are fetched per field rather than shipped in the schema: they grow
 * with the data, and a form with six relations should not carry every row of
 * six tables.
 */
function useRelationOptions(resource, field) {
  const [options, setOptions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    fetchOptions(resource, field.name, '', { signal: controller.signal })
      .then((payload) => setOptions(payload[field.name] ?? []))
      .catch(() => setOptions([]))
      .finally(() => !controller.signal.aborted && setLoading(false))
    return () => controller.abort()
  }, [resource, field.name])

  return { options, loading }
}

function ReferenceInput({ field, value, onChange, resource, ...rest }) {
  const { options, loading } = useRelationOptions(resource, field)

  return (
    <select
      {...rest}
      className="cf-input cf-input--select"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
      disabled={rest.disabled || loading}
    >
      <option value="">{loading ? 'Loading…' : '—'}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

/**
 * A checkbox list rather than a multi-select: a native multi-select needs
 * ctrl-click to add a second item, which people reliably do not discover.
 */
function MultiReferenceInput({ field, value, onChange, resource, ...rest }) {
  const { options, loading } = useRelationOptions(resource, field)
  const selected = useMemo(() => new Set((value ?? []).map(Number)), [value])

  const toggle = (id) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChange([...next])
  }

  if (loading) return <p className="cf-field__help">Loading options…</p>
  if (!options.length) return <p className="cf-field__help">Nothing to choose from yet.</p>

  return (
    <div className="cf-checks" role="group" aria-labelledby={`field-${field.name}`}>
      {options.map((option) => (
        <label key={option.value} className="cf-check">
          <input
            type="checkbox"
            checked={selected.has(option.value)}
            onChange={() => toggle(option.value)}
            disabled={rest.disabled}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  )
}

function FileInput({ field, value, onChange, ...rest }) {
  const existing = typeof value === 'string' && value ? value : null
  const picked = value instanceof File ? value : null

  return (
    <div className="cf-file">
      {existing && field.type === 'image' && (
        <img className="cf-file__preview" src={existing} alt="" width="120" />
      )}
      {existing && field.type !== 'image' && (
        <a className="cf-file__link" href={existing} target="_blank" rel="noreferrer">
          Current file
        </a>
      )}
      <input
        {...rest}
        className="cf-input cf-input--file"
        type="file"
        accept={field.type === 'image' ? 'image/*' : undefined}
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      {picked && <p className="cf-field__help">Selected: {picked.name}</p>}
    </div>
  )
}

/**
 * JSON is edited as text and parsed on the way out, so a half-typed object does
 * not throw on every keystroke. The error is shown but does not block typing.
 */
function JsonInput({ value, onChange, ...rest }) {
  const [text, setText] = useState(() => (value ? JSON.stringify(value, null, 2) : ''))
  const [invalid, setInvalid] = useState(false)

  const handle = (next) => {
    setText(next)
    if (next.trim() === '') {
      setInvalid(false)
      onChange(null)
      return
    }
    try {
      onChange(JSON.parse(next))
      setInvalid(false)
    } catch {
      setInvalid(true)
    }
  }

  return (
    <>
      <textarea
        {...rest}
        className="cf-input cf-input--area cf-input--mono"
        value={text}
        onChange={(e) => handle(e.target.value)}
        rows={8}
        spellCheck="false"
      />
      {invalid && <p className="cf-field__error">Not valid JSON yet — the last valid value is kept.</p>}
    </>
  )
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
