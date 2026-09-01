/**
 * Create or rename a knowledge base.
 *
 * Lives on its own because both the create and the rename path on the knowledge
 * screen mount it, and it is the only form in that corner of the panel that is
 * a form at all — everything else there is an operation.
 */

import { useState } from 'react'

import { messageFor } from '../../api'
import { createKnowledgeBase, updateKnowledgeBase } from '../../knowledge-api'

/**
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
