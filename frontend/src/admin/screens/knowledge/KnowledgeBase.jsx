/**
 * Adding data to the assistant's knowledge base — the whole job, on one screen.
 *
 * This replaced four sidebar entries: knowledge bases, documents, document
 * versions and ingestion jobs. They were four ways of looking at the same
 * upload, and an operator whose actual task is "add this PDF" had to know which
 * one to open, then navigate between them to find out whether it had worked.
 *
 * So the screen is organised around the task rather than around the tables.
 * Pick the corpus, drop the file in, watch it become answerable — in that
 * order, top to bottom, without a navigation in the middle. The cross-base view
 * ("what is stuck anywhere?") is a chip on the same picker, because it is the
 * one question that genuinely spans corpora and it should not cost a screen.
 *
 * Versions and jobs are still there. They are diagnostics for one document, so
 * they live on that document's page, reached by clicking its name.
 */

import { useEffect, useState } from 'react'

import { messageFor } from '../../api'
import { Uploader } from '../../components/knowledge'
import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fetchDocuments, fetchKnowledgeBases, updateKnowledgeBase } from '../../knowledge-api'
import DocumentRows from './DocumentRows'
import { KnowledgeBaseForm } from './KnowledgeBaseForm'

// The cross-base view. A sentinel rather than `null` so the picker has one kind
// of value throughout and "nothing selected yet" stays distinguishable from it.
const ALL = '__all__'

const STATUS_FILTERS = [
  { key: '', label: 'All' },
  { key: 'ready', label: 'Ready' },
  { key: 'processing', label: 'Processing' },
  { key: 'failed', label: 'Failed' },
]

export default function KnowledgeBase({ onNotify }) {
  const bases = useAsync((signal) => fetchKnowledgeBases({ signal }), [])
  const [selected, setSelected] = useState(null)
  const [status, setStatus] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState(false)

  const baseRows = rowsOf(bases.data)

  // Land on the first base rather than on an empty picker: with one knowledge
  // base — which is the common case — choosing it is not a decision anyone
  // wants to be asked to make before they can upload anything.
  //
  // Keyed on `bases.data`, not on `baseRows`: the latter is a fresh array every
  // render, which would re-run this on every keystroke elsewhere on the screen.
  useEffect(() => {
    const rows = rowsOf(bases.data)
    if (selected === null && rows.length) setSelected(rows[0].id)
  }, [selected, bases.data])

  const viewingAll = selected === ALL
  const base = viewingAll ? null : baseRows.find((row) => row.id === selected)

  const documents = useAsync(
    (signal) =>
      selected === null
        ? Promise.resolve([])
        : fetchDocuments({ status, knowledge_base: viewingAll ? '' : selected }, { signal }),
    [selected, status],
  )

  if (bases.loading) return <Spinner label="Loading the knowledge base" />
  if (bases.error) return <ErrorState message={bases.error} onRetry={bases.reload} />

  const docRows = rowsOf(documents.data)
  const counts = summarise(docRows)

  const toggleActive = async () => {
    try {
      await updateKnowledgeBase(base.id, { is_active: !base.is_active })
      onNotify?.(`${base.name} ${base.is_active ? 'deactivated' : 'activated'}.`)
      bases.reload()
    } catch (error) {
      onNotify?.(messageFor(error), 'error')
    }
  }

  return (
    <div className="cf-page">
      <PageHeader
        eyebrow="Assistant"
        title="Knowledge base"
        count={documents.loading ? undefined : docRows.length}
      >
        <button
          type="button"
          className={`cf-btn ${creating ? 'cf-btn--ghost' : 'cf-btn--primary'}`}
          onClick={() => {
            setCreating((open) => !open)
            setEditing(false)
          }}
        >
          {creating ? 'Cancel' : 'New knowledge base'}
        </button>
      </PageHeader>

      {creating && (
        <KnowledgeBaseForm
          onCancel={() => setCreating(false)}
          onSaved={(saved) => {
            setCreating(false)
            setSelected(saved.id) // drop the operator straight into what they just made
            onNotify?.(`${saved.name} created.`)
            bases.reload()
          }}
        />
      )}

      {baseRows.length === 0 ? (
        <EmptyState
          title="No knowledge base yet"
          body="A knowledge base is a corpus the assistant searches as a unit. Create one, then upload the documents it should answer from."
          action={
            !creating && (
              <button
                type="button"
                className="cf-btn cf-btn--primary"
                onClick={() => setCreating(true)}
              >
                Create the first one
              </button>
            )
          }
        />
      ) : (
        <>
          <div className="cf-filters">
            <div className="cf-filters__group" role="group" aria-label="Knowledge base">
              {baseRows.map((row) => (
                <button
                  key={row.id}
                  type="button"
                  className={`cf-chip${selected === row.id ? ' is-active' : ''}`}
                  onClick={() => setSelected(row.id)}
                  aria-pressed={selected === row.id}
                >
                  {row.name}
                  {!row.is_active && <span className="cf-chip__note"> · inactive</span>}
                </button>
              ))}
              {baseRows.length > 1 && (
                <button
                  type="button"
                  className={`cf-chip${viewingAll ? ' is-active' : ''}`}
                  onClick={() => setSelected(ALL)}
                  aria-pressed={viewingAll}
                >
                  Everything
                </button>
              )}
            </div>

            {base && (
              <div className="cf-actions">
                <button
                  type="button"
                  className="cf-btn cf-btn--ghost cf-btn--sm"
                  onClick={() => {
                    setEditing((open) => !open)
                    setCreating(false)
                  }}
                >
                  {editing ? 'Cancel' : 'Rename'}
                </button>
                <button
                  type="button"
                  className="cf-btn cf-btn--ghost cf-btn--sm"
                  onClick={toggleActive}
                >
                  {base.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </div>
            )}
          </div>

          {editing && base && (
            <KnowledgeBaseForm
              base={base}
              onCancel={() => setEditing(false)}
              onSaved={() => {
                setEditing(false)
                onNotify?.('Knowledge base updated.')
                bases.reload()
              }}
            />
          )}

          {base?.description && !editing && <p className="cf-page__lead">{base.description}</p>}

          {base && !base.is_active && (
            <p className="cf-notice" role="status">
              This knowledge base is inactive. Its documents are kept, but nothing in it is
              searched.
            </p>
          )}

          {/* Adding data is what this screen is for, so it comes before the
              inventory rather than after it. */}
          {base && (
            <section className="cf-section">
              <h2 className="cf-section__title">Add a document</h2>
              <Uploader
                knowledgeBase={base.id}
                disabled={!base.is_active}
                onNotify={onNotify}
                onUploaded={() => documents.reload()}
              />
              {!base.is_active && (
                <p className="cf-hint">Activate the knowledge base to add documents to it.</p>
              )}
            </section>
          )}

          <section className="cf-section">
            <h2 className="cf-section__title">
              {viewingAll ? 'Every document' : 'Documents'}
            </h2>

            {/* Two counts, not one, and they answer different questions: how
                much has been uploaded, and how much of it can actually answer
                anything. A gap between them is the case worth noticing. */}
            <div className="cf-stats">
              <Stat label="Documents" value={docRows.length} />
              <Stat
                label="Answerable"
                value={counts.ready}
                tone={counts.ready < docRows.length ? 'warn' : undefined}
              />
              <Stat label="Processing" value={counts.processing} />
              <Stat label="Failed" value={counts.failed} tone={counts.failed ? 'bad' : undefined} />
            </div>

            <div className="cf-filters">
              <div className="cf-filters__group" role="group" aria-label="Filter by status">
                {STATUS_FILTERS.map((filter) => (
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
            </div>

            {documents.loading ? (
              <Spinner label="Loading documents" />
            ) : documents.error ? (
              <ErrorState message={documents.error} onRetry={documents.reload} />
            ) : docRows.length === 0 ? (
              <EmptyState
                title={status ? `No ${status} documents` : 'Nothing here yet'}
                body={
                  status
                    ? 'Nothing matches that filter right now.'
                    : 'Upload a PDF above. It will be extracted, chunked, embedded and indexed in the background — you can watch it happen here.'
                }
              />
            ) : (
              <DocumentRows
                documents={docRows}
                onChanged={documents.reload}
                onNotify={onNotify}
                showKnowledgeBase={viewingAll}
              />
            )}
          </section>
        </>
      )}
    </div>
  )
}

/** The API pages some collections and not others; both arrive here. */
function rowsOf(data) {
  return data?.results ?? data ?? []
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
