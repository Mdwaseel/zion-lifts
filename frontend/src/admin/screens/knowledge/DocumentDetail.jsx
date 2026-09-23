/**
 * One document: what it is, which edition is answering, and what happened to
 * the ones that are not.
 *
 * The version history is the point of the screen. A document that has been
 * replaced three times has three stories — which edition is live, which failed
 * and why, and which is still being indexed — and none of them fits in a status
 * column on a list.
 */

import { Link, useParams } from 'react-router-dom'

import {
  FailureNotice,
  StagePipeline,
  StatusPill,
  Uploader,
  formatBytes,
  formatDate,
} from '../../components/knowledge'
import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui'
import { useAsync, useIngestionStatus } from '../../hooks'
import { fetchDocument, fetchJobs, fetchVersions } from '../../knowledge-api'
import { Actions } from './DocumentRows'

export default function DocumentDetail({ onNotify }) {
  const { id } = useParams()

  const document = useAsync((signal) => fetchDocument(id, { signal }), [id])
  const versions = useAsync((signal) => fetchVersions(id, { signal }), [id])
  const jobs = useAsync((signal) => fetchJobs(id, { signal }), [id])

  const record = document.data
  const processing = Boolean(record?.is_processing)

  // Everything on the screen refreshes together when the run settles: the
  // status, the version list and the job history all changed at that moment.
  const { status: live } = useIngestionStatus(id, {
    enabled: processing,
    onSettled: () => {
      document.reload()
      versions.reload()
      jobs.reload()
    },
  })

  if (document.loading) return <Spinner label="Loading document" />
  if (document.error) return <ErrorState message={document.error} onRetry={document.reload} />

  const state = live?.status ?? record.status
  const job = live?.job ?? record.latest_job
  const inFlight = !['ready', 'failed', 'deleted'].includes(state)

  return (
    <div className="cf-page">
      <PageHeader
        eyebrow={
          <Link className="cf-link" to={`/control/knowledge-bases/${record.knowledge_base}`}>
            {record.knowledge_base_name}
          </Link>
        }
        title={record.name}
      >
        <Actions
          document={record}
          state={state}
          processing={inFlight}
          compact={false}
          onNotify={onNotify}
          onChanged={() => {
            document.reload()
            versions.reload()
            jobs.reload()
          }}
        />
      </PageHeader>

      <dl className="cf-facts">
        <Fact label="Status">
          <StatusPill status={state} />
        </Fact>
        <Fact label="Live version">
          {record.active_version_number ? `Version ${record.active_version_number}` : 'None yet'}
        </Fact>
        <Fact label="File">{record.original_filename}</Fact>
        <Fact label="Size">{formatBytes(record.file_size)}</Fact>
        <Fact label="Pages">{record.page_count ?? '—'}</Fact>
        <Fact label="Chunks">{record.chunk_count ?? '—'}</Fact>
        <Fact label="Added">{formatDate(record.created_at)}</Fact>
        <Fact label="Updated">{formatDate(record.updated_at)}</Fact>
      </dl>

      {inFlight && (
        <section className="cf-section">
          <h2 className="cf-section__title">Processing</h2>
          <StagePipeline status={state} progress={job?.progress} />
          {record.active_version_number && (
            <p className="cf-hint">
              Version {record.active_version_number} keeps answering questions until this one
              finishes.
            </p>
          )}
        </section>
      )}

      {state === 'failed' && (
        <section className="cf-section">
          <FailureNotice job={job} version={versions.data?.[0]} />
        </section>
      )}

      <section className="cf-section">
        <h2 className="cf-section__title">Replace this document</h2>
        <p className="cf-hint">
          Uploading a new file creates a new version. The current one keeps answering questions
          until the new one has been indexed successfully.
        </p>
        <Uploader
          knowledgeBase={record.knowledge_base}
          onNotify={onNotify}
          disabled={inFlight}
          onUploaded={() => {
            document.reload()
            versions.reload()
            jobs.reload()
          }}
        />
      </section>

      <section className="cf-section">
        <h2 className="cf-section__title">Version history</h2>
        {versions.loading ? (
          <Spinner label="Loading versions" />
        ) : versions.error ? (
          <ErrorState message={versions.error} onRetry={versions.reload} />
        ) : (
          <Versions versions={versions.data ?? []} activeId={record.active_version} />
        )}
      </section>

      <section className="cf-section">
        <h2 className="cf-section__title">Ingestion history</h2>
        {jobs.loading ? (
          <Spinner label="Loading jobs" />
        ) : jobs.error ? (
          <ErrorState message={jobs.error} onRetry={jobs.reload} />
        ) : (
          <Jobs jobs={jobs.data ?? []} />
        )}
      </section>
    </div>
  )
}

function Fact({ label, children }) {
  return (
    <div className="cf-fact">
      <dt className="cf-fact__label">{label}</dt>
      <dd className="cf-fact__value">{children}</dd>
    </div>
  )
}

/**
 * Every edition, newest first.
 *
 * The live one is marked rather than merely sorted to the top: an operator
 * looking at three READY versions needs to know which one is actually
 * answering, and "the newest" is not always the answer — a failed replacement
 * leaves an older edition live.
 */
function Versions({ versions, activeId }) {
  if (!versions.length) {
    return <EmptyState title="No versions" body="Nothing has been stored for this document yet." />
  }

  return (
    <div className="cf-table__scroll">
      <table className="cf-table">
        <thead>
          <tr>
            <th scope="col">Version</th>
            <th scope="col">Status</th>
            <th scope="col">Pages</th>
            <th scope="col">Chunks</th>
            <th scope="col">Embedding</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {versions.map((version) => (
            <tr key={version.id} className={version.id === activeId ? 'is-active' : undefined}>
              <td>
                <strong>Version {version.version_number}</strong>
                {version.id === activeId && <span className="cf-tag">Live</span>}
              </td>
              <td>
                <StatusPill status={version.status} />
                {version.error_code && (
                  <code className="cf-cell__code">{version.error_code}</code>
                )}
              </td>
              <td className="cf-cell__num">{version.page_count ?? '—'}</td>
              <td className="cf-cell__num">{version.chunk_count ?? '—'}</td>
              <td className="cf-cell__meta">
                {version.embedding_model ? (
                  <>
                    {version.embedding_model}
                    {version.embedding_dimension ? ` · ${version.embedding_dimension}d` : ''}
                  </>
                ) : (
                  '—'
                )}
              </td>
              <td className="cf-cell__meta">{formatDate(version.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * What has been attempted.
 *
 * Kept in full rather than collapsed to the latest: three failures and one
 * failure are different problems, and only the history tells them apart.
 */
function Jobs({ jobs }) {
  if (!jobs.length) {
    return <EmptyState title="No ingestion jobs" body="Nothing has been queued for this document." />
  }

  return (
    <div className="cf-table__scroll">
      <table className="cf-table">
        <thead>
          <tr>
            <th scope="col">Operation</th>
            <th scope="col">Status</th>
            <th scope="col">Stage</th>
            <th scope="col">Attempt</th>
            <th scope="col">Error</th>
            <th scope="col">Started</th>
            <th scope="col">Duration</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className={job.status === 'failed' ? 'is-failed' : undefined}>
              <td className="cf-cell__meta">{job.job_type}</td>
              <td>
                <span className={`cf-pill cf-pill--${jobTone(job.status)}`}>{job.status}</span>
              </td>
              <td className="cf-cell__meta">{job.current_stage || '—'}</td>
              <td className="cf-cell__num">{job.attempt_count}</td>
              <td className="cf-cell__meta">
                {job.error_code ? <code className="cf-cell__code">{job.error_code}</code> : '—'}
              </td>
              <td className="cf-cell__meta">{formatDate(job.started_at)}</td>
              <td className="cf-cell__num">
                {job.duration_seconds != null ? `${job.duration_seconds.toFixed(1)}s` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function jobTone(status) {
  if (status === 'succeeded') return 'ok'
  if (status === 'failed') return 'bad'
  if (status === 'running') return 'busy'
  return 'neutral'
}
