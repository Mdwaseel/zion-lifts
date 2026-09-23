import { Link } from 'react-router-dom'

import { fetchDashboard } from '../api'
import { formatDate } from '../components/Field'
import { ErrorState, PageHeader, Spinner } from '../components/ui'
import { useAsync } from '../hooks'

/**
 * The landing screen: what needs attention, and what changed.
 *
 * Every number here links to the filtered list that explains it — a count you
 * cannot click is a count you have to go and find.
 */

export default function Dashboard() {
  const { data, error, loading, reload } = useAsync((signal) => fetchDashboard({ signal }), [])

  if (loading) return <Spinner label="Loading dashboard" />
  if (error) return <ErrorState message={error} onRetry={reload} />

  const { inbox, urgent, recent_enquiries: recent, collections, activity, window_days: days } = data

  return (
    <section className="cf-page cf-dash">
      <PageHeader eyebrow="Control room" title="Overview" />

      <div className="cf-dash__stats">
        <StatCard
          label="Open enquiries"
          value={inbox.enquiries.unhandled}
          total={inbox.enquiries.total}
          note={`${inbox.enquiries.recent} in the last ${days} days`}
          to="/control/enquiries?status=new"
          tone={inbox.enquiries.unhandled > 0 ? 'attention' : 'calm'}
        />
        <StatCard
          label="Open service requests"
          value={inbox.service_requests.unhandled}
          total={inbox.service_requests.total}
          note={`${inbox.service_requests.recent} in the last ${days} days`}
          to="/control/service-requests?status=new"
          tone={inbox.service_requests.unhandled > 0 ? 'attention' : 'calm'}
        />
        <StatCard
          label="Urgent on site"
          value={urgent.length}
          note={urgent.length ? 'Needs a call today' : 'Nothing outstanding'}
          to="/control/service-requests"
          tone={urgent.length ? 'urgent' : 'calm'}
        />
        <StatCard
          label="Unpublished"
          value={collections.reduce((sum, c) => sum + (c.unpublished ?? 0), 0)}
          note="Across every collection"
          tone="calm"
        />
      </div>

      <div className="cf-dash__cols">
        <div className="cf-dash__main">
          <Funnel
            title="Enquiry pipeline"
            resource="enquiries"
            statuses={inbox.enquiries.statuses}
          />
          <Funnel
            title="Service pipeline"
            resource="service-requests"
            statuses={inbox.service_requests.statuses}
          />

          {urgent.length > 0 && (
            <Panel title="Urgent service requests" to="/control/service-requests">
              <PanelTable>
                <table className="cf-table cf-table--compact">
                  <thead>
                    <tr>
                      <th scope="col">Site</th>
                      <th scope="col">Kind</th>
                      <th scope="col">Urgency</th>
                      <th scope="col">Raised</th>
                    </tr>
                  </thead>
                  <tbody>
                    {urgent.map((row) => (
                      <tr key={row.id}>
                        <td>
                          <Link className="cf-link" to={`/control/service-requests/${row.id}`}>
                            {row.site}
                          </Link>
                          <span className="cf-cell__sub">{row.name}</span>
                        </td>
                        <td>{row.kind}</td>
                        <td>
                          <span className="cf-pill cf-pill--urgent">{row.urgency}</span>
                        </td>
                        <td>{formatDate(row.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </PanelTable>
            </Panel>
          )}

          <Panel title="Latest enquiries" to="/control/enquiries">
            {recent.length === 0 ? (
              <p className="cf-dash__empty">No enquiries yet.</p>
            ) : (
              <PanelTable>
                <table className="cf-table cf-table--compact">
                  <thead>
                    <tr>
                      <th scope="col">Name</th>
                      <th scope="col">Location</th>
                      <th scope="col">System</th>
                      <th scope="col">Status</th>
                      <th scope="col">Received</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((row) => (
                      <tr key={row.id}>
                        <td>
                          <Link className="cf-link" to={`/control/enquiries/${row.id}`}>
                            {row.name}
                          </Link>
                        </td>
                        <td>{row.location}</td>
                        <td>{row.lift_type}</td>
                        <td>
                          <span className="cf-pill">{row.status}</span>
                        </td>
                        <td>{formatDate(row.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </PanelTable>
            )}
          </Panel>
        </div>

        <aside className="cf-dash__side">
          <Panel title="Recent activity">
            {activity.length === 0 ? (
              <p className="cf-dash__empty">Nothing has been changed yet.</p>
            ) : (
              <ul className="cf-activity">
                {activity.map((entry) => (
                  <li key={entry.id} className="cf-activity__row">
                    <span
                      className={`cf-activity__dot cf-activity__dot--${entry.action}`}
                      aria-hidden="true"
                    />
                    <div>
                      <p className="cf-activity__what">
                        <strong>{entry.user}</strong> {entry.action}{' '}
                        {entry.resource && entry.object_id ? (
                          <Link
                            className="cf-link"
                            to={`/control/${entry.resource}/${entry.object_id}`}
                          >
                            {entry.object_repr}
                          </Link>
                        ) : (
                          <span>{entry.object_repr}</span>
                        )}
                      </p>
                      <p className="cf-activity__when">{formatDate(entry.at)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Content">
            <ul className="cf-counts">
              {collections
                .filter((c) => c.group !== 'Inbox')
                .map((collection) => (
                  <li key={collection.key}>
                    <Link className="cf-counts__row" to={`/control/${collection.key}`}>
                      <span>{collection.label}</span>
                      <span className="cf-counts__n">
                        {collection.count}
                        {collection.unpublished > 0 && (
                          <em className="cf-counts__draft" title="Unpublished">
                            {collection.unpublished} draft
                          </em>
                        )}
                      </span>
                    </Link>
                  </li>
                ))}
            </ul>
          </Panel>
        </aside>
      </div>
    </section>
  )
}

function StatCard({ label, value, total, note, to, tone }) {
  const body = (
    <>
      <p className="cf-stat__label">{label}</p>
      <p className="cf-stat__value">
        {value}
        {total !== undefined && <span className="cf-stat__total">of {total}</span>}
      </p>
      <p className="cf-stat__note">{note}</p>
    </>
  )
  const className = `cf-stat cf-stat--${tone}`
  return to ? (
    <Link className={className} to={to}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  )
}

/**
 * A pipeline as proportional bars.
 *
 * The widths are shares of the largest bucket rather than of the total, so a
 * stage holding two records out of four hundred is still visible.
 */
function Funnel({ title, resource, statuses }) {
  const peak = Math.max(1, ...statuses.map((s) => s.count))
  return (
    <Panel title={title}>
      <ul className="cf-funnel">
        {statuses.map((status) => (
          <li key={status.value}>
            <Link className="cf-funnel__row" to={`/control/${resource}?status=${status.value}`}>
              <span className="cf-funnel__label">{status.label}</span>
              <span className="cf-funnel__bar" aria-hidden="true">
                <span style={{ width: `${(status.count / peak) * 100}%` }} />
              </span>
              <span className="cf-funnel__n">{status.count}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

/** A table inside a panel still has to scroll on a narrow screen. */
function PanelTable({ children }) {
  return <div className="cf-panel__scroll">{children}</div>
}

function Panel({ title, to, children }) {
  return (
    <section className="cf-panel">
      <header className="cf-panel__header">
        <h2 className="cf-panel__title">{title}</h2>
        {to && (
          <Link className="cf-link" to={to}>
            View all
          </Link>
        )}
      </header>
      {children}
    </section>
  )
}
