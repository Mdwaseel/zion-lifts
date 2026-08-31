import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  ApiError,
  createRecord,
  deleteRecord,
  fetchRecord,
  fetchSchema,
  messageFor,
  updateRecord,
} from '../api'
import Field from '../components/Field'
import { ErrorState, PageHeader, Spinner } from '../components/ui'
import { useArmed, useAsync } from '../hooks'

/**
 * The edit form, for every collection.
 *
 * Sections and inputs both come from the schema, so this file contains no
 * knowledge of any particular model. The only per-model behaviour is the slug
 * helper, and even that is declared server-side.
 */

export default function RecordForm({ onNotify }) {
  const { resource, id } = useParams()
  const navigate = useNavigate()
  const isNew = id === 'new'

  const schemaState = useAsync((signal) => fetchSchema(resource, { signal }), [resource])
  const recordState = useAsync(
    (signal) => (isNew ? Promise.resolve(null) : fetchRecord(resource, id, { signal })),
    [resource, id, isNew],
  )

  const [values, setValues] = useState({})
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const { isArmed, arm } = useArmed()
  const errorRef = useRef(null)

  const schema = schemaState.data
  const record = recordState.data

  // Seed the form once both halves have arrived. A new record starts from the
  // schema's own defaults so a boolean is false rather than undefined, which
  // would make the input uncontrolled.
  useEffect(() => {
    if (!schema) return
    setValues(record ? { ...record } : blankRecord(schema))
    setDirty(false)
    setErrors({})
    setFormError(null)
  }, [schema, record])

  useEffect(() => {
    if (formError) errorRef.current?.focus()
  }, [formError])

  // Leaving with unsaved edits loses them; the browser's own prompt is the only
  // thing that can interrupt a navigation it owns.
  useEffect(() => {
    if (!dirty) return undefined
    const warn = (event) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const byName = useMemo(
    () => Object.fromEntries((schema?.fields ?? []).map((field) => [field.name, field])),
    [schema],
  )

  function set(name, value) {
    setDirty(true)
    setErrors((current) => (current[name] ? { ...current, [name]: undefined } : current))
    setValues((current) => {
      const next = { ...current, [name]: value }
      // Fill an untouched slug from its source field, the way Django's admin
      // does. Only while the slug is empty: overwriting one that is already
      // published would change a live URL.
      const slug = schema.fields.find((f) => f.slug_source === name)
      if (slug && !current[slug.name]) next[slug.name] = slugify(value)
      return next
    })
  }

  async function onSubmit(event) {
    event.preventDefault()
    if (saving) return

    setSaving(true)
    setFormError(null)
    setErrors({})

    try {
      const body = buildBody(schema, values, { partial: !isNew })
      const saved = isNew
        ? await createRecord(resource, body)
        : await updateRecord(resource, id, body)

      setDirty(false)
      onNotify(isNew ? `${schema.label} created.` : `${schema.label} saved.`)
      if (isNew) navigate(`/control/${resource}/${saved.id}`, { replace: true })
      else recordState.reload()
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        setErrors(fieldErrors(error))
        setFormError('Please check the highlighted fields.')
      } else {
        setFormError(messageFor(error))
      }
    } finally {
      setSaving(false)
    }
  }

  async function onDelete() {
    try {
      await deleteRecord(resource, id)
      setDirty(false)
      onNotify(`${schema.label} deleted.`)
      navigate(`/control/${resource}`)
    } catch (error) {
      onNotify(messageFor(error), 'error')
    }
  }

  if (schemaState.loading || recordState.loading) return <Spinner label="Loading record" />
  if (schemaState.error) return <ErrorState message={schemaState.error} onRetry={schemaState.reload} />
  if (recordState.error) return <ErrorState message={recordState.error} onRetry={recordState.reload} />

  const readOnlyRecord = !schema.permissions.edit
  const title = isNew ? `New ${schema.label.toLowerCase()}` : record?._str || schema.label

  return (
    <section className="cf-page">
      <PageHeader eyebrow={schema.label_plural} title={title}>
        <Link className="cf-btn cf-btn--ghost" to={`/control/${resource}`}>
          Back to list
        </Link>
      </PageHeader>

      <form className="cf-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <div className="cf-form__alert" role="alert" tabIndex={-1} ref={errorRef}>
            {formError}
          </div>
        )}

        {schema.fieldsets.map((section) => (
          <fieldset key={section.title || 'main'} className="cf-fieldset">
            {section.title && <legend className="cf-fieldset__legend">{section.title}</legend>}
            <div className="cf-fieldset__grid">
              {section.fields.map((name) =>
                byName[name] ? (
                  <Field
                    key={name}
                    field={byName[name]}
                    value={values[name]}
                    onChange={(value) => set(name, value)}
                    error={errors[name]}
                    resource={resource}
                    disabled={saving || readOnlyRecord}
                  />
                ) : null,
              )}
            </div>
          </fieldset>
        ))}

        {values.attachments && Array.isArray(values.attachments) && values.attachments.length > 0 && (
          <fieldset className="cf-fieldset">
            <legend className="cf-fieldset__legend">
              Uploaded Attachments & Site Photos ({values.attachments.length})
            </legend>
            <div
              style={{
                display: 'grid',
                gap: '1rem',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                marginTop: '0.75rem',
              }}
            >
              {values.attachments.map((att) => {
                const isImage = /\.(jpg|jpeg|png|webp|gif)$/i.test(att.url || att.original_name)
                return (
                  <div
                    key={att.id}
                    style={{
                      border: '1px solid #cbd5e1',
                      borderRadius: '8px',
                      padding: '12px',
                      background: '#f8fafc',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    {isImage && att.url ? (
                      <a href={att.url} target="_blank" rel="noreferrer">
                        <img
                          src={att.url}
                          alt={att.original_name}
                          style={{
                            width: '100%',
                            height: '140px',
                            objectFit: 'cover',
                            borderRadius: '6px',
                            border: '1px solid #e2e8f0',
                          }}
                        />
                      </a>
                    ) : (
                      <div
                        style={{
                          height: '90px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyIn: 'center',
                          background: '#e2e8f0',
                          borderRadius: '6px',
                          fontSize: '2rem',
                          justifyContent: 'center',
                        }}
                      >
                        📄
                      </div>
                    )}
                    <span
                      style={{
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        wordBreak: 'break-all',
                        color: '#1e293b',
                      }}
                    >
                      {att.original_name}
                    </span>
                    {att.url && (
                      <a
                        href={att.url}
                        target="_blank"
                        rel="noreferrer"
                        className="cf-btn cf-btn--ghost"
                        style={{
                          fontSize: '0.8rem',
                          padding: '6px 10px',
                          textAlign: 'center',
                          textDecoration: 'none',
                          marginTop: 'auto',
                        }}
                      >
                        View / Download
                      </a>
                    )}
                  </div>
                )
              })}
            </div>
          </fieldset>
        )}

        <div className="cf-form__actions">
          {!readOnlyRecord && (
            <button type="submit" className="cf-btn cf-btn--primary" disabled={saving}>
              {saving ? 'Saving…' : isNew ? `Create ${schema.label.toLowerCase()}` : 'Save changes'}
            </button>
          )}
          <Link className="cf-btn cf-btn--ghost" to={`/control/${resource}`}>
            Cancel
          </Link>

          {!isNew && schema.permissions.delete && (
            <button
              type="button"
              className={`cf-btn cf-form__delete ${isArmed('delete') ? 'cf-btn--danger' : 'cf-btn--ghost'}`}
              onClick={() => (isArmed('delete') ? onDelete() : arm('delete'))}
            >
              {isArmed('delete') ? 'Confirm delete' : 'Delete'}
            </button>
          )}
        </div>

        {dirty && (
          <p className="cf-form__dirty" role="status">
            You have unsaved changes.
          </p>
        )}
      </form>
    </section>
  )
}

/** Schema defaults, so every input is controlled from the first render. */
function blankRecord(schema) {
  const blank = {}
  for (const field of schema.fields) {
    if (field.readonly) continue
    if (field.type === 'boolean') blank[field.name] = false
    else if (field.type === 'multi_reference') blank[field.name] = []
    else if (field.type === 'reference') blank[field.name] = null
    else if (field.type === 'integer' || field.type === 'float') blank[field.name] = ''
    else blank[field.name] = ''
  }
  return blank
}

/**
 * Build the request body.
 *
 * Two things matter here. Read-only fields are dropped — the server ignores
 * them anyway, but sending an enquiry's name back on every save is noise in the
 * audit log. And a File anywhere in the payload switches the whole request to
 * multipart, because JSON cannot carry one.
 */
function buildBody(schema, values, { partial }) {
  const writable = schema.fields.filter((field) => !field.readonly)
  const hasFile = writable.some((field) => values[field.name] instanceof File)

  if (!hasFile) {
    const body = {}
    for (const field of writable) {
      const value = values[field.name]
      // On create, an empty optional field is left out so the model's own
      // default applies rather than being overwritten with "".
      if (!partial && (value === '' || value === null) && !field.required) continue
      body[field.name] = value === '' && field.type !== 'string' ? null : value
    }
    return body
  }

  const form = new FormData()
  for (const field of writable) {
    const value = values[field.name]
    if (value === null || value === undefined) continue
    if (value instanceof File) form.append(field.name, value)
    else if (Array.isArray(value)) value.forEach((item) => form.append(field.name, item))
    else if (typeof value === 'object') form.append(field.name, JSON.stringify(value))
    else form.append(field.name, value)
  }
  return form
}

function fieldErrors(error) {
  const fields = error.fields ?? {}
  return Object.fromEntries(
    Object.entries(fields).map(([key, value]) => [key, [].concat(value).join(' ')]),
  )
}

function slugify(value) {
  return String(value ?? '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/[\s_]+/g, '-')
    .slice(0, 50)
}
