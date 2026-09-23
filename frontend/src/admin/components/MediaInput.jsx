/**
 * Putting a picture or a film into a record, from the operator's own computer.
 *
 * This replaces a text box that wanted a path like `/media/frames/foo.jpg`.
 * That box asked the person filling in a form to already know what was on the
 * server, gave them no way to check, and had no answer at all for somebody
 * holding a photograph on their laptop. There is no URL input here on purpose:
 * choose a file, see it, replace it, remove it.
 *
 * The field still *stores* a URL — the upload lands first and what goes into
 * the record is where it landed — so nothing downstream of the form changed.
 * That is also why a picture set before any of this existed still shows: the
 * preview renders whatever string is in the field, wherever it points.
 *
 * Uploading happens on selection rather than on save. A form that holds a 40 MB
 * film in memory until you press Save is a form that loses it when the tab is
 * closed, and it makes the save itself slow and failable for a reason unrelated
 * to the record.
 */

import { useEffect, useRef, useState } from 'react'

import { messageFor } from '../api'
import { ACCEPT, SIZE_LIMIT_MB, uploadMedia } from '../media-api'

export default function MediaInput({
  value,
  onChange,
  field,
  disabled,
  id,
  'aria-describedby': describedBy,
}) {
  const kind = field?.media_kind === 'video' ? 'video' : 'image'
  const folder = field?.upload_folder ?? 'content'

  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)
  const active = useRef(null)

  // An upload still running when the form navigates away is bytes going
  // nowhere. Cancel it rather than letting it finish into a component that no
  // longer exists.
  useEffect(() => () => active.current?.abort(), [])

  const busy = progress !== null
  const current = typeof value === 'string' ? value.trim() : ''

  const send = (file) => {
    if (!file || disabled || busy) return
    setError(null)

    const limit = SIZE_LIMIT_MB[kind]
    if (file.size > limit * 1024 * 1024) {
      // Checked here as well as on the server so a file that cannot possibly be
      // accepted is refused before it spends anyone's upload bandwidth.
      setError(`That file is ${(file.size / 1024 / 1024).toFixed(1)} MB; the limit is ${limit} MB.`)
      return
    }

    setProgress(0)
    const upload = uploadMedia({ file, folder, onProgress: setProgress })
    active.current = upload

    upload.promise
      .then((stored) => onChange(stored.url))
      .catch((caught) => {
        if (caught?.name === 'AbortError') return
        setError(messageFor(caught, 'That file could not be uploaded.'))
      })
      .finally(() => {
        active.current = null
        setProgress(null)
        if (inputRef.current) inputRef.current.value = ''
      })
  }

  const onDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    send(event.dataTransfer.files?.[0])
  }

  return (
    <div className="cf-media">
      {current ? (
        <figure className="cf-media__current">
          {kind === 'video' ? (
            // `preload="metadata"` so opening a form with four films does not
            // start downloading four films.
            <video className="cf-media__preview" src={current} controls preload="metadata" />
          ) : (
            <img className="cf-media__preview" src={current} alt="" loading="lazy" />
          )}
          <figcaption className="cf-media__meta">
            <span className="cf-media__path" title={current}>
              {filenameOf(current)}
            </span>
            <span className="cf-media__actions">
              <button
                type="button"
                className="cf-btn cf-btn--ghost cf-btn--sm"
                onClick={() => inputRef.current?.click()}
                disabled={disabled || busy}
              >
                Replace
              </button>
              <button
                type="button"
                className="cf-btn cf-btn--ghost cf-btn--sm"
                onClick={() => {
                  setError(null)
                  onChange('')
                }}
                disabled={disabled || busy}
              >
                Remove
              </button>
            </span>
          </figcaption>
        </figure>
      ) : (
        <div
          className={`cf-media__drop${dragging ? ' is-dragging' : ''}${disabled ? ' is-disabled' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            if (!disabled && !busy) setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <button
            type="button"
            className="cf-btn cf-btn--ghost cf-btn--sm"
            onClick={() => inputRef.current?.click()}
            disabled={disabled || busy}
          >
            Choose {kind === 'video' ? 'a video' : 'an image'}
          </button>
          <p className="cf-media__hint">
            or drop {kind === 'video' ? 'a video' : 'an image'} here —{' '}
            {kind === 'video' ? 'MP4, WebM or MOV' : 'JPG, PNG, WebP, GIF or AVIF'}, up to{' '}
            {SIZE_LIMIT_MB[kind]} MB
          </p>
        </div>
      )}

      {busy && (
        <div className="cf-media__progress">
          <div className="cf-media__bar">
            <span style={{ width: `${progress}%` }} />
          </div>
          <span className="cf-media__pct">{progress}%</span>
          <button
            type="button"
            className="cf-btn cf-btn--ghost cf-btn--sm"
            onClick={() => active.current?.abort()}
          >
            Cancel
          </button>
        </div>
      )}

      {error && (
        <p className="cf-field__error" role="alert">
          {error}
        </p>
      )}

      <input
        ref={inputRef}
        id={id}
        aria-describedby={describedBy}
        className="cf-sr"
        type="file"
        accept={ACCEPT[kind]}
        disabled={disabled || busy}
        onChange={(event) => send(event.target.files?.[0])}
      />
    </div>
  )
}

/** The last path segment, which is the only part worth showing in a caption. */
export function filenameOf(url) {
  try {
    return decodeURIComponent(String(url).split('?')[0].split('/').filter(Boolean).pop() ?? url)
  } catch {
    return url
  }
}
