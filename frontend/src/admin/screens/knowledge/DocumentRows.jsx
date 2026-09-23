/**
 * The document table, shared by the knowledge-base screen and the all-documents
 * list.
 *
 * Two things make it more than a table. A row that is still processing follows
 * its own status until it settles, so an operator who uploads a file watches it
 * become answerable without touching anything. And the row's actions are
 * disabled by the same rules the server enforces — a disabled button is a
 * courtesy, and `apps/knowledge/services` is what actually refuses.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'

import { messageFor } from '../../api'
import { StatusPill, formatBytes, formatDate } from '../../components/knowledge'
import { useArmed, useIngestionStatus } from '../../hooks'
import { deleteDocument, reindexDocument, retryDocument } from '../../knowledge-api'

export default function DocumentRows({
  documents,
  onChanged,
  onNotify,
  showKnowledgeBase = true,
}) {
  return (
    <div className="cf-table__scroll">
      <table className="cf-table">
        <thead>
          <tr>
            <th scope="col">Document</th>
            {showKnowledgeBase && <th scope="col">Knowledge base</th>}
            <th scope="col">Version</th>
            <th scope="col">Status</th>
            <th scope="col">Pages</th>
            <th scope="col">Chunks</th>
            <th scope="col">Updated</th>
            <th scope="col">
              <span className="cf-sr">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <Row
              key={document.id}
              document={document}
              onChanged={onChanged}
              onNotify={onNotify}
              showKnowledgeBase={showKnowledgeBase}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Row({ document, onChanged, onNotify, showKnowledgeBase }) {
  // Only in-flight rows are watched. Polling a table of fifty finished
  // documents would be fifty requests a second for information that cannot
  // change.
  const { status } = useIngestionStatus(document.id, {
    enabled: Boolean(document.is_processing),
    onSettled: () => onChanged?.(),
  })

  const live = status ?? document
  const state = live.status ?? document.status
  const job = live.job ?? document.latest_job
  const processing = !['ready', 'failed', 'deleted'].includes(state)

  return (
    <tr className={state === 'failed' ? 'is-failed' : undefined}>
      <td>
        <Link className="cf-link" to={`/control/knowledge-documents/${document.id}`}>
          {document.name}
        </Link>
        <p className="cf-cell__sub">
          {document.original_filename} · {formatBytes(document.file_size)}
        </p>
      </td>

      {showKnowledgeBase && <td>{document.knowledge_base_name}</td>}

      <td className="cf-cell__num">
        {live.active_version ?? document.active_version_number ?? '—'}
      </td>

      <td>
        <StatusPill status={state} />
        {processing && job?.progress != null && (
          <span className="cf-cell__progress">{job.progress}%</span>
        )}
      </td>

      <td className="cf-cell__num">{document.page_count ?? '—'}</td>
      <td className="cf-cell__num">{document.chunk_count ?? '—'}</td>
      <td className="cf-cell__meta">{formatDate(document.updated_at)}</td>

      <td className="cf-cell__actions">
        <Actions
          document={document}
          state={state}
          processing={processing}
          onChanged={onChanged}
          onNotify={onNotify}
        />
      </td>
    </tr>
  )
}

/**
 * Reindex, retry and delete.
 *
 * Which of them is offered depends on the document's state, and the rules match
 * the backend's: retry only makes sense for a failed document, reindex only for
 * one that has something stored, and nothing at all while work is in flight —
 * queuing a second worker on the same version is exactly what
 * `job_service.queue` refuses to do.
 */
export function Actions({ document, state, processing, onChanged, onNotify, compact = true }) {
  const [busy, setBusy] = useState(null)
  const { isArmed, arm, disarm } = useArmed()

  const run = async (label, action, verb) => {
    setBusy(label)
    try {
      await action(document.id)
      onNotify?.(verb)
      onChanged?.()
    } catch (error) {
      onNotify?.(messageFor(error), 'error')
    } finally {
      setBusy(null)
      disarm()
    }
  }

  const size = compact ? ' cf-btn--sm' : ''
  const disabled = processing || busy !== null

  return (
    <div className="cf-actions">
      {state === 'failed' && (
        <button
          type="button"
          className={`cf-btn cf-btn--ghost${size}`}
          disabled={disabled}
          onClick={() => run('retry', retryDocument, 'Retrying — the document has been requeued.')}
        >
          {busy === 'retry' ? 'Retrying…' : 'Retry'}
        </button>
      )}

      {state === 'ready' && (
        <button
          type="button"
          className={`cf-btn cf-btn--ghost${size}`}
          disabled={disabled}
          // Deliberate wording: this rebuilds the search index for the edition
          // already stored. It does not create a new version, and implying it
          // did would be a lie an operator acts on.
          title="Rebuild the search index for the current version. No new version is created."
          onClick={() =>
            run('reindex', reindexDocument, 'Reindexing — the search index is being rebuilt.')
          }
        >
          {busy === 'reindex' ? 'Reindexing…' : 'Reindex'}
        </button>
      )}

      {state !== 'deleted' &&
        (isArmed(document.id) ? (
          <button
            type="button"
            className={`cf-btn cf-btn--danger${size}`}
            disabled={busy !== null}
            onClick={() =>
              run(
                'delete',
                deleteDocument,
                'Deleting — the document is being removed from the search index.',
              )
            }
          >
            {busy === 'delete' ? 'Deleting…' : 'Confirm delete'}
          </button>
        ) : (
          <button
            type="button"
            className={`cf-btn cf-btn--ghost${size}`}
            disabled={disabled}
            onClick={() => arm(document.id)}
          >
            Delete
          </button>
        ))}
    </div>
  )
}
