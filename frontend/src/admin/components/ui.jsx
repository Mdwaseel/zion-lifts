/**
 * The small pieces every screen reuses: status, emptiness, paging, messages.
 *
 * Kept in one file because none of them is more than a few lines and splitting
 * them would be five imports where one will do.
 */

export function Spinner({ label = 'Loading' }) {
  return (
    <div className="cf-spinner" role="status">
      <span className="cf-spinner__ring" aria-hidden="true" />
      <span className="cf-sr">{label}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="cf-state cf-state--error" role="alert">
      <p className="cf-state__title">Something went wrong</p>
      <p className="cf-state__body">{message}</p>
      {onRetry && (
        <button type="button" className="cf-btn cf-btn--ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, body, action }) {
  return (
    <div className="cf-state">
      <p className="cf-state__title">{title}</p>
      {body && <p className="cf-state__body">{body}</p>}
      {action}
    </div>
  )
}

/**
 * Page controls.
 *
 * Deliberately first/prev/next/last plus a readout rather than numbered pages:
 * a filtered table can be one page or forty, and a row of forty numbers is
 * noise. The readout is what people actually read.
 */
export function Pagination({ page, pages, count, pageSize, onPage }) {
  if (pages <= 1) {
    return (
      <p className="cf-pager__count">
        {count} {count === 1 ? 'record' : 'records'}
      </p>
    )
  }

  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, count)

  return (
    <nav className="cf-pager" aria-label="Pagination">
      <p className="cf-pager__count">
        {first}–{last} of {count}
      </p>
      <div className="cf-pager__controls">
        <button type="button" className="cf-btn cf-btn--ghost cf-btn--sm" disabled={page <= 1} onClick={() => onPage(1)}>
          First
        </button>
        <button type="button" className="cf-btn cf-btn--ghost cf-btn--sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <span className="cf-pager__page" aria-current="page">
          Page {page} of {pages}
        </span>
        <button type="button" className="cf-btn cf-btn--ghost cf-btn--sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
        <button type="button" className="cf-btn cf-btn--ghost cf-btn--sm" disabled={page >= pages} onClick={() => onPage(pages)}>
          Last
        </button>
      </div>
    </nav>
  )
}

/**
 * Transient confirmations, bottom right.
 *
 * `aria-live="polite"` so a save is announced without interrupting whatever the
 * reader is on; an error is `assertive` because it changes what to do next.
 */
export function Toasts({ toasts, onDismiss }) {
  return (
    <div className="cf-toasts" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`cf-toast cf-toast--${toast.tone}`}
          role={toast.tone === 'error' ? 'alert' : 'status'}
        >
          <span>{toast.message}</span>
          <button
            type="button"
            className="cf-toast__close"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

/** Page heading with an optional trailing action. */
export function PageHeader({ eyebrow, title, count, children }) {
  return (
    <header className="cf-page__header">
      <div>
        {eyebrow && <p className="cf-page__eyebrow">{eyebrow}</p>}
        <h1 className="cf-page__title">
          {title}
          {count !== undefined && <span className="cf-page__count">{count}</span>}
        </h1>
      </div>
      {children && <div className="cf-page__actions">{children}</div>}
    </header>
  )
}
