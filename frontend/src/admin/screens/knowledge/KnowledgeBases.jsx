/**
 * The knowledge bases, and what is in each of them.
 *
 * Two counts per row rather than one, because they answer different questions:
 * how much has been uploaded, and how much of it can actually answer a
 * question. A base where those diverge is a base with a problem, and that is
 * the whole reason to look at this screen.
 *
 * Both numbers are annotated by the backend in one query — see
 * `selectors/knowledge_bases.with_counts`. Counting them here would mean
 * fetching every document in every base to display a list of bases.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { messageFor } from '../../api'
import { createKnowledgeBase, fetchKnowledgeBases, updateKnowledgeBase } from '../../knowledge-api'

export default function KnowledgeBases({ onNotify }) {
  const bases = useAsync((signal) => fetchKnowledgeBases({ signal }), [])
  const [creating, setCreating] = useState(false)

  if (bases.loading) return <Spinner label="Loading knowledge bases" />
  if (bases.error) return <ErrorState message={bases.error} onRetry={bases.reload} />

  const rows = bases.data?.results ?? bases.data ?? []

  return (
    <div className="cf-page">
      <PageHeader eyebrow="Knowledge base" title="Knowledge bases" count={rows.length}>
        <button
          type="button"
          className="cf-btn cf-btn--primary"
          onClick={() => setCreating((open) => !open)}
        >
          {creating ? 'Cancel' : 'New knowledge base'}
        </button>
      </PageHeader>

      {creating && (
        <KnowledgeBaseForm
          onCancel={() => setCreating(false)}
          onSaved={(base) => {
            setCreating(false)
            onNotify?.(`${base.name} created.`)
            bases.reload()
          }}
        />
      )}

      {rows.length === 0 && !creating ? (
        <EmptyState
          title="No knowledge bases yet"
          body="A knowledge base is a corpus the assistant searches as a unit. Create one, then upload the documents it should answer from."
          action={
            <button
              type="button"
              className="cf-btn cf-btn--primary"
              onClick={() => setCreating(true)}
            >
              Create the first one
            </button>
          }
        />
      ) : (
        <div className="cf-table__scroll">
          <table className="cf-table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Documents</th>
                <th scope="col">Answerable</th>
                <th scope="col">Status</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((base) => (
                <BaseRow key={base.id} base={base} onChanged={bases.reload} onNotify={onNotify} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function BaseRow({ base, onChanged, onNotify }) {
  const [busy, setBusy] = useState(false)

  const toggle = async () => {
    setBusy(true)
    try {
      await updateKnowledgeBase(base.id, { is_active: !base.is_active })
      onNotify?.(`${base.name} ${base.is_active ? 'deactivated' : 'activated'}.`)
      onChanged()
    } catch (error) {
      onNotify?.(messageFor(error), 'error')
    } finally {
      setBusy(false)
    }
  }

  // A base with documents that cannot answer is the case worth noticing.
  const lagging = base.document_count > 0 && base.ready_count < base.document_count

  return (
    <tr>
      <td>
        <Link className="cf-link" to={`/control/knowledge-bases/${base.id}`}>
          {base.name}
        </Link>
        {base.description && <p className="cf-cell__sub">{base.description}</p>}
      </td>
      <td className="cf-cell__num">{base.document_count}</td>
      <td className="cf-cell__num">
        <span className={lagging ? 'cf-cell__warn' : undefined}>{base.ready_count}</span>
      </td>
      <td>
        <span className={`cf-pill cf-pill--${base.is_active ? 'ok' : 'neutral'}`}>
          {base.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td className="cf-cell__meta">
        <button
          type="button"
          className="cf-btn cf-btn--ghost cf-btn--sm"
          onClick={toggle}
          disabled={busy}
        >
          {base.is_active ? 'Deactivate' : 'Activate'}
        </button>
      </td>
    </tr>
  )
}

/**
 * Create or rename a base.
 *
 * The slug is suggested from the name and stays editable: it is part of no URL
 * the public sees, but it is what an operator will recognise in a collection
 * name, so it is worth being able to choose.
 *
 * Every rule here is duplicated on the server, which is the one that counts —
 * this only saves a round trip.
 */
export function KnowledgeBaseForm({ base, onSaved, onCancel }) {
  const [name, setName] = useState(base?.name ?? '')
  const [slug, setSlug] = useState(base?.slug ?? '')
  const [description, setDescription] = useState(base?.description ?? '')
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const slugify = (value) =>
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 60)

  const submit = async (event) => {
    event.preventDefault()
    setErrors({})

    if (!name.trim()) {
      setErrors({ name: 'A name is required.' })
      return
    }

    setSaving(true)
    try {
      const body = { name: name.trim(), slug: slug || slugify(name), description }
      const saved = base
        ? await updateKnowledgeBase(base.id, body)
        : await createKnowledgeBase(body)
      onSaved?.(saved)
    } catch (error) {
      // DRF returns field errors as { field: [messages] }; anything else is a
      // message for the top of the form.
      const fields = error?.fields ?? {}
      const flattened = Object.fromEntries(
        Object.entries(fields)
          .filter(([key]) => key !== 'detail')
          .map(([key, value]) => [key, Array.isArray(value) ? value[0] : String(value)]),
      )
      setErrors(
        Object.keys(flattened).length ? flattened : { __all__: messageFor(error) },
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="cf-card cf-form" onSubmit={submit}>
      {errors.__all__ && (
        <p className="cf-form__error" role="alert">
          {errors.__all__}
        </p>
      )}

      <div className="cf-field">
        <label className="cf-field__label" htmlFor="kb-name">
          Name
        </label>
        <input
          id="kb-name"
          className="cf-input"
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (!base && !slug) setSlug('')
          }}
          onBlur={() => !slug && setSlug(slugify(name))}
          aria-invalid={Boolean(errors.name)}
        />
        {errors.name && <p className="cf-field__error">{errors.name}</p>}
      </div>

      <div className="cf-field">
        <label className="cf-field__label" htmlFor="kb-slug">
          Slug
        </label>
        <input
          id="kb-slug"
          className="cf-input"
          value={slug}
          placeholder={slugify(name) || 'product-manuals'}
          onChange={(event) => setSlug(slugify(event.target.value))}
          aria-invalid={Boolean(errors.slug)}
        />
        {errors.slug && <p className="cf-field__error">{errors.slug}</p>}
      </div>

      <div className="cf-field">
        <label className="cf-field__label" htmlFor="kb-description">
          Description
        </label>
        <textarea
          id="kb-description"
          className="cf-input cf-input--area"
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </div>

      <div className="cf-form__actions">
        <button type="submit" className="cf-btn cf-btn--primary" disabled={saving}>
          {saving ? 'Saving…' : base ? 'Save' : 'Create'}
        </button>
        {onCancel && (
          <button type="button" className="cf-btn cf-btn--ghost" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
