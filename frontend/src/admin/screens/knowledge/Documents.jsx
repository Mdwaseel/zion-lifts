/**
 * Every document, across every knowledge base.
 *
 * The status filter is the reason this screen exists separately from the
 * per-base one: "what is stuck?" is a question about the whole corpus, and
 * answering it by opening each knowledge base in turn is how a failed document
 * goes unnoticed for a week.
 */

import { useState } from 'react'

import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fetchDocuments, fetchKnowledgeBases } from '../../knowledge-api'
import DocumentRows from './DocumentRows'

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'ready', label: 'Ready' },
  { key: 'processing', label: 'Processing' },
  { key: 'failed', label: 'Failed' },
]

export default function Documents({ onNotify }) {
  const [status, setStatus] = useState('')
  const [base, setBase] = useState('')

  const bases = useAsync((signal) => fetchKnowledgeBases({ signal }), [])
  const documents = useAsync(
    (signal) => fetchDocuments({ status, knowledge_base: base }, { signal }),
    [status, base],
  )

  const baseRows = bases.data?.results ?? bases.data ?? []
  const rows = documents.data?.results ?? documents.data ?? []

  return (
    <div className="cf-page">
      <PageHeader
        eyebrow="Knowledge base"
        title="Documents"
        count={documents.loading ? undefined : rows.length}
      />

      <div className="cf-filters">
        <div className="cf-filters__group" role="group" aria-label="Filter by status">
          {FILTERS.map((filter) => (
            <button
              key={filter.key || 'all'}
              type="button"
              className={`cf-chip${status === filter.key ? ' is-active' : ''}`}
              onClick={() => setStatus(filter.key)}
              aria-pressed={status === filter.key}
            >
              {filter.label}
            </button>
          ))}
        </div>

        <label className="cf-filters__select">
          <span className="cf-sr">Filter by knowledge base</span>
          <select
            className="cf-input"
            value={base}
            onChange={(event) => setBase(event.target.value)}
          >
            <option value="">Every knowledge base</option>
            {baseRows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {documents.loading ? (
        <Spinner label="Loading documents" />
      ) : documents.error ? (
        <ErrorState message={documents.error} onRetry={documents.reload} />
      ) : rows.length === 0 ? (
        <EmptyState
          title={status ? `No ${status} documents` : 'No documents yet'}
          body={
            status
              ? 'Nothing matches that filter right now.'
              : 'Open a knowledge base to upload the first document.'
          }
        />
      ) : (
        <DocumentRows documents={rows} onChanged={documents.reload} onNotify={onNotify} />
      )}
    </div>
  )
}
