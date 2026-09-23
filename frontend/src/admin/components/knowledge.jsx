/**
 * The pieces the knowledge screens share.
 *
 * A document's status is the one thing an operator reads on every screen, so it
 * is rendered the same way everywhere: same words, same colours, same order.
 * Two different renderings of "failed" is how a panel starts lying to people.
 */

import { useCallback, useRef, useState } from 'react'

import { messageFor } from '../api'
import { uploadDocument } from '../knowledge-api'

// The stages a version walks, in order. Mirrors DocumentState in the backend —
// the two are one vocabulary spoken across a boundary, and a stage this file
// does not know about renders as itself rather than as a blank.
export const STAGES = [
  { key: 'processing', label: 'Queued' },
  { key: 'extracting', label: 'Extracting' },
  { key: 'chunking', label: 'Chunking' },
  { key: 'embedding', label: 'Embedding' },
  { key: 'indexing', label: 'Indexing' },
  { key: 'ready', label: 'Ready' },
]

const TONE = {
  uploaded: 'neutral',
  processing: 'busy',
  extracting: 'busy',
  chunking: 'busy',
  embedding: 'busy',
  indexing: 'busy',
  ready: 'ok',
  failed: 'bad',
  deleting: 'busy',
  deleted: 'neutral',
}

const WORDS = {
  uploaded: 'Uploaded',
  processing: 'Queued',
  extracting: 'Extracting',
  chunking: 'Chunking',
  embedding: 'Embedding',
  indexing: 'Indexing',
  ready: 'Ready',
  failed: 'Failed',
  deleting: 'Deleting',
  deleted: 'Deleted',
}

export function statusLabel(status) {
  return WORDS[status] ?? status
}

export function StatusPill({ status, children }) {
  return (
    <span className={`cf-pill cf-pill--${TONE[status] ?? 'neutral'}`}>
      {children ?? statusLabel(status)}
    </span>
  )
}

/**
 * The stage a version has reached, as a sequence rather than a percentage.
 *
 * A bar at 40% tells an operator nothing they can act on. "Stuck at Embedding
 * for ten minutes" names the dependency to go and look at, which is the whole
 * reason the backend reports stages separately instead of a number.
 */
export function StagePipeline({ status, progress }) {
  const failed = status === 'failed'
  const current = STAGES.findIndex((stage) => stage.key === status)

  return (
    <div className="cf-stages" role="group" aria-label="Ingestion progress">
      {STAGES.map((stage, index) => {
        const done = current > index || status === 'ready'
        const active = current === index && !failed
        const state = failed && current === -1 ? 'failed' : done ? 'done' : active ? 'active' : ''

        return (
          <div key={stage.key} className={`cf-stage${state ? ` is-${state}` : ''}`}>
            <span className="cf-stage__dot" aria-hidden="true" />
            <span className="cf-stage__label">{stage.label}</span>
          </div>
        )
      })}
      {typeof progress === 'number' && (
        <p className="cf-stages__readout">
          {failed ? 'Failed' : `${progress}%`}
        </p>
      )}
    </div>
  )
}

/**
 * Why an ingestion failed, in terms an operator can act on.
 *
 * The stable error code, the stage it reached, and how many attempts it took.
 * Never a traceback and never a provider message verbatim — those carry
 * infrastructure detail that belongs in the logs, not on a screen someone may
 * screenshot into a ticket.
 */
const EXPLANATIONS = {
  DOCUMENT_NOT_FOUND: 'The stored file could not be read. It may have been removed.',
  INVALID_DOCUMENT: 'No text could be extracted — the PDF may be a scan with no text layer.',
  CONTENT_HASH_MISMATCH: 'The stored file no longer matches the version record.',
  PDF_EXTRACTION_FAILED: 'The PDF could not be parsed.',
  EMBEDDING_FAILED: 'The embedding service could not be reached.',
  EMBEDDING_DIMENSION_MISMATCH:
    'The embedding model does not match the one this knowledge base was built with.',
  VECTOR_STORE_UNAVAILABLE: 'The search index was unavailable.',
  INDEXING_FAILED: 'The chunks could not be written to the search index.',
  CALLBACK_FAILED: 'The worker finished but could not report back.',
  INVALID_PAYLOAD: 'The ingestion request was not valid.',
  INVALID_CONFIGURATION: 'The ingestion service is misconfigured.',
  broker_unavailable: 'The job queue was unreachable, so nothing was started.',
}

export function FailureNotice({ job, version }) {
  const code = job?.error_code || version?.error_code
  if (!code) return null

  return (
    <div className="cf-failure" role="alert">
      <p className="cf-failure__title">
        Ingestion failed
        <code className="cf-failure__code">{code}</code>
      </p>
      <p className="cf-failure__body">
        {EXPLANATIONS[code] ?? 'The ingestion could not be completed.'}
      </p>
      <dl className="cf-failure__meta">
        {job?.current_stage && (
          <>
            <dt>Stage</dt>
            <dd>{statusLabel(job.current_stage)}</dd>
          </>
        )}
        {job?.attempt_count != null && (
          <>
            <dt>Attempts</dt>
            <dd>{job.attempt_count}</dd>
          </>
        )}
        {job?.finished_at && (
          <>
            <dt>Failed</dt>
            <dd>{formatDate(job.finished_at)}</dd>
          </>
        )}
      </dl>
    </div>
  )
}

/* --- upload ------------------------------------------------------------- */

const MAX_BYTES = 25 * 1024 * 1024

export function formatBytes(bytes) {
  if (!bytes) return '—'
  const mb = bytes / 1024 / 1024
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/**
 * Drag-and-drop PDF upload.
 *
 * The checks here are for the person, not for the server: they turn a wrong
 * file into an immediate sentence instead of a round trip and a 400. The
 * authoritative validation reads the file's first bytes and lives in
 * `apps/knowledge/validators.py` — a name ending in .pdf is not evidence, and
 * this component is in no position to know better.
 */
export function Uploader({ knowledgeBase, onUploaded, onNotify, disabled }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const activeUpload = useRef(null)

  const choose = useCallback((candidate) => {
    setError(null)
    if (!candidate) return

    if (!candidate.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files can be uploaded.')
      return
    }
    if (candidate.size === 0) {
      setError('That file is empty.')
      return
    }
    if (candidate.size > MAX_BYTES) {
      setError(`That file is ${formatBytes(candidate.size)}; the limit is 25 MB.`)
      return
    }
    setFile(candidate)
  }, [])

  const onDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    if (disabled) return
    choose(event.dataTransfer.files?.[0])
  }

  const reset = () => {
    setFile(null)
    setProgress(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const start = async () => {
    if (!file || progress !== null) return
    setProgress(0)
    setError(null)

    const upload = uploadDocument({
      knowledgeBase,
      file,
      onProgress: setProgress,
    })
    activeUpload.current = upload

    try {
      const result = await upload.promise
      onNotify?.(`${file.name} uploaded. Processing has started.`)
      reset()
      onUploaded?.(result)
    } catch (caught) {
      if (caught?.name === 'AbortError') {
        reset()
        return
      }
      setError(messageFor(caught, 'The upload failed.'))
      setProgress(null)
    } finally {
      activeUpload.current = null
    }
  }

  const uploading = progress !== null

  return (
    <div className="cf-upload">
      <div
        className={`cf-drop${dragging ? ' is-dragging' : ''}${disabled ? ' is-disabled' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          id="cf-upload-input"
          className="cf-drop__input"
          disabled={disabled || uploading}
          onChange={(event) => choose(event.target.files?.[0])}
        />
        <label htmlFor="cf-upload-input" className="cf-drop__label">
          {file ? (
            <>
              <strong className="cf-drop__name">{file.name}</strong>
              <span className="cf-drop__size">{formatBytes(file.size)}</span>
            </>
          ) : (
            <>
              <strong className="cf-drop__name">Drop a PDF here</strong>
              <span className="cf-drop__size">or choose a file — 25 MB maximum</span>
            </>
          )}
        </label>
      </div>

      {uploading && (
        <div className="cf-progress" role="progressbar" aria-valuenow={progress}
             aria-valuemin={0} aria-valuemax={100}>
          <div className="cf-progress__bar" style={{ width: `${progress}%` }} />
          <span className="cf-progress__text">
            {progress < 100 ? `Uploading ${progress}%` : 'Handing over to the worker…'}
          </span>
        </div>
      )}

      {error && (
        <p className="cf-upload__error" role="alert">
          {error}
        </p>
      )}

      <div className="cf-upload__actions">
        <button
          type="button"
          className="cf-btn cf-btn--primary"
          onClick={start}
          disabled={!file || uploading || disabled}
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
        {file && !uploading && (
          <button type="button" className="cf-btn cf-btn--ghost" onClick={reset}>
            Clear
          </button>
        )}
        {uploading && (
          <button
            type="button"
            className="cf-btn cf-btn--ghost"
            onClick={() => activeUpload.current?.abort()}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  )
}
