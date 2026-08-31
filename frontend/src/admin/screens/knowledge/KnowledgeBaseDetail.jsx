/**
 * One knowledge base: what is in it, and how to add to it.
 *
 * The upload panel and the document list are on one screen deliberately. Adding
 * a document and watching it become answerable is a single task, and splitting
 * it across two screens means an operator uploads a file and then has to go
 * looking for what happened to it.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Uploader } from '../../components/knowledge'
import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fetchDocuments, fetchKnowledgeBase } from '../../knowledge-api'
import { KnowledgeBaseForm } from './KnowledgeBases'
import DocumentRows from './DocumentRows'

export default function KnowledgeBaseDetail({ onNotify }) {
  const { id } = useParams()
  const [editing, setEditing] = useState(false)

  const base = useAsync((signal) => fetchKnowledgeBase(id, { signal }), [id])
  const documents = useAsync(
    (signal) => fetchDocuments({ knowledge_base: id }, { signal }),
    [id],
  )

  if (base.loading) return <Spinner label="Loading knowledge base" />
  if (base.error) return <ErrorState message={base.error} onRetry={base.reload} />

  const rows = documents.data?.results ?? documents.data ?? []
  const counts = summarise(rows)

  return (
    <div className="cf-page">
      <PageHeader eyebrow={<Link className="cf-link" to="/control/knowledge-bases">Knowledge bases</Link>}
                  title={base.data.name}>
        <button
          type="button"
          className="cf-btn cf-btn--ghost"
          onClick={() => setEditing((open) => !open)}
        >
          {editing ? 'Cancel' : 'Edit'}
        </button>
      </PageHeader>

      {editing ? (
        <KnowledgeBaseForm
          base={base.data}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            onNotify?.('Knowledge base updated.')
            base.reload()
          }}
        />
      ) : (
        base.data.description && <p className="cf-page__lead">{base.data.description}</p>
      )}

      <div className="cf-stats">
        <Stat label="Documents" value={rows.length} />
        <Stat label="Answerable" value={counts.ready} tone={counts.ready < rows.length ? 'warn' : undefined} />
        <Stat label="Processing" value={counts.processing} />
        <Stat label="Failed" value={counts.failed} tone={counts.failed ? 'bad' : undefined} />
      </div>

      {!base.data.is_active && (
        <p className="cf-notice" role="status">
          This knowledge base is inactive. Its documents are kept, but nothing in it is
          searched.
        </p>
      )}

      <section className="cf-section">
        <h2 className="cf-section__title">Add a document</h2>
        <Uploader
          knowledgeBase={id}
          disabled={!base.data.is_active}
          onNotify={onNotify}
          onUploaded={() => documents.reload()}
        />
        {!base.data.is_active && (
          <p className="cf-hint">Activate the knowledge base to add documents to it.</p>
        )}
      </section>

      <section className="cf-section">
        <h2 className="cf-section__title">Documents</h2>

        {documents.loading ? (
          <Spinner label="Loading documents" />
        ) : documents.error ? (
          <ErrorState message={documents.error} onRetry={documents.reload} />
        ) : rows.length === 0 ? (
          <EmptyState
            title="Nothing in this knowledge base yet"
            body="Upload a PDF above. It will be extracted, chunked, embedded and indexed in the background — you can watch it here."
          />
        ) : (
          <DocumentRows
            documents={rows}
            onChanged={documents.reload}
            onNotify={onNotify}
            showKnowledgeBase={false}
          />
        )}
      </section>
    </div>
  )
}

function summarise(rows) {
  return rows.reduce(
    (totals, document) => {
      if (document.status === 'ready') totals.ready += 1
      else if (document.status === 'failed') totals.failed += 1
      else if (document.is_processing) totals.processing += 1
      return totals
    },
    { ready: 0, failed: 0, processing: 0 },
  )
}

function Stat({ label, value, tone }) {
  return (
    <div className={`cf-stat${tone ? ` cf-stat--${tone}` : ''}`}>
      <p className="cf-stat__value">{value}</p>
      <p className="cf-stat__label">{label}</p>
    </div>
  )
}
