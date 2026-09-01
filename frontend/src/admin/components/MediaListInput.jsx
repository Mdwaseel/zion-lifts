/**
 * A project's photographs, a lift's images — as a list of pictures, not JSON.
 *
 * This is the field the operator was most obviously not meant to see raw. A
 * project's `images` is a JSON array of objects, and editing it meant typing
 *
 *     [{"stage": "interior", "src": "/media/frames/lekha-cabin.jpg", ...}]
 *
 * into a textarea — where a missing brace loses the lot and a mistyped path
 * fails silently on the public site weeks later. Same data, same column: this
 * just gives each photograph a row, an uploader and its own text fields.
 *
 * The row shape comes from the server (`field.fields`), so a new key on the
 * model's JSON appears here without this component knowing anything about
 * lifts or projects.
 *
 * Order is meaningful — it is the order the site renders them in — so rows move
 * up and down rather than being sorted. Buttons rather than drag-and-drop:
 * dragging needs a pointer, and this has to work for somebody on a laptop
 * trackpad with one hand, on a phone, and via a keyboard.
 */

import { useRef, useState } from 'react'

import { messageFor } from '../api'
import { ACCEPT, SIZE_LIMIT_MB, uploadMedia } from '../media-api'
import { filenameOf } from './MediaInput'

export default function MediaListInput({ value, onChange, field, disabled, id }) {
  const rows = Array.isArray(value) ? value : []
  const srcKey = field?.src_key ?? 'src'
  const itemFields = field?.fields ?? []
  const folder = field?.upload_folder ?? 'content'

  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(0) // how many uploads are in flight
  const inputRef = useRef(null)

  const replaceAt = (index, next) =>
    onChange(rows.map((row, i) => (i === index ? next : row)))

  const move = (index, by) => {
    const target = index + by
    if (target < 0 || target >= rows.length) return
    const next = [...rows]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  /**
   * Add every chosen file, in the order they were chosen.
   *
   * Uploaded in parallel but appended in order: the operator picked twelve
   * photographs meaning a sequence, and finishing order on a flaky connection
   * is not that sequence.
   */
  const addFiles = async (files) => {
    const chosen = Array.from(files ?? [])
    if (!chosen.length || disabled) return
    setError(null)

    const limit = SIZE_LIMIT_MB.image
    const tooBig = chosen.find((file) => file.size > limit * 1024 * 1024)
    if (tooBig) {
      setError(`${tooBig.name} is larger than ${limit} MB.`)
      return
    }

    setBusy((n) => n + chosen.length)
    const results = await Promise.all(
      chosen.map((file) =>
        uploadMedia({ file, folder })
          .promise.then((stored) => ({ ok: true, stored, file }))
          .catch((caught) => ({ ok: false, caught, file })),
      ),
    )
    setBusy((n) => Math.max(0, n - chosen.length))
    if (inputRef.current) inputRef.current.value = ''

    const added = results
      .filter((result) => result.ok)
      .map((result) => ({ ...blankRow(itemFields), [srcKey]: result.stored.url }))

    if (added.length) onChange([...rows, ...added])

    const failed = results.filter((result) => !result.ok)
    if (failed.length) {
      setError(
        failed.length === 1
          ? `${failed[0].file.name}: ${messageFor(failed[0].caught, 'upload failed')}`
          : `${failed.length} files could not be uploaded.`,
      )
    }
  }

  return (
    <div className="cf-medialist">
      {rows.length > 0 && (
        <ol className="cf-medialist__rows">
          {rows.map((row, index) => (
            <li className="cf-medialist__row" key={`${row?.[srcKey] ?? 'row'}-${index}`}>
              <div className="cf-medialist__thumb">
                {row?.[srcKey] ? (
                  <img src={row[srcKey]} alt="" loading="lazy" />
                ) : (
                  <span className="cf-medialist__missing">No image</span>
                )}
              </div>

              <div className="cf-medialist__fields">
                <p className="cf-medialist__name" title={row?.[srcKey] ?? ''}>
                  {row?.[srcKey] ? filenameOf(row[srcKey]) : '—'}
                </p>

                {itemFields.map((item) => (
                  <label className="cf-medialist__field" key={item.name}>
                    <span>{item.label}</span>
                    {item.type === 'choice' ? (
                      <select
                        className="cf-input cf-input--select cf-input--inline"
                        value={row?.[item.name] ?? ''}
                        disabled={disabled}
                        onChange={(event) =>
                          replaceAt(index, { ...row, [item.name]: event.target.value })
                        }
                      >
                        <option value="">—</option>
                        {item.choices?.map((choice) => (
                          <option key={choice.value} value={choice.value}>
                            {choice.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        className="cf-input cf-input--inline"
                        type="text"
                        value={row?.[item.name] ?? ''}
                        disabled={disabled}
                        placeholder={item.help_text ? '' : item.label}
                        onChange={(event) =>
                          replaceAt(index, { ...row, [item.name]: event.target.value })
                        }
                      />
                    )}
                  </label>
                ))}
              </div>

              <div className="cf-medialist__controls">
                <button
                  type="button"
                  className="cf-btn cf-btn--ghost cf-btn--sm"
                  onClick={() => move(index, -1)}
                  disabled={disabled || index === 0}
                  aria-label={`Move ${index + 1} earlier`}
                  title="Move earlier"
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="cf-btn cf-btn--ghost cf-btn--sm"
                  onClick={() => move(index, 1)}
                  disabled={disabled || index === rows.length - 1}
                  aria-label={`Move ${index + 1} later`}
                  title="Move later"
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="cf-btn cf-btn--ghost cf-btn--sm"
                  onClick={() => onChange(rows.filter((_, i) => i !== index))}
                  disabled={disabled}
                  aria-label={`Remove image ${index + 1}`}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      <div className="cf-medialist__add">
        <button
          type="button"
          className="cf-btn cf-btn--ghost cf-btn--sm"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || busy > 0}
        >
          {busy > 0 ? `Uploading ${busy}…` : 'Add images'}
        </button>
        <span className="cf-media__hint">
          {rows.length} image{rows.length === 1 ? '' : 's'} — they appear on the site in this
          order. You can select several at once.
        </span>
      </div>

      {error && (
        <p className="cf-field__error" role="alert">
          {error}
        </p>
      )}

      <input
        ref={inputRef}
        id={id}
        className="cf-sr"
        type="file"
        multiple
        accept={ACCEPT.image}
        disabled={disabled || busy > 0}
        onChange={(event) => addFiles(event.target.files)}
      />
    </div>
  )
}

/** A new row with every declared key present, so the shape stays consistent. */
function blankRow(itemFields) {
  return Object.fromEntries(itemFields.map((item) => [item.name, '']))
}
