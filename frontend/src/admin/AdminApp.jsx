import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from '@/lib/auth'

import { fetchNavigation } from './api'
import { ErrorState, Spinner, Toasts } from './components/ui'
import { useAsync, useToasts } from './hooks'
import Shell from './layout/Shell'
import Analytics from './screens/analytics/Analytics'
import PageAnalytics from './screens/analytics/PageDetail'
import Dashboard from './screens/Dashboard'
import DocumentDetail from './screens/knowledge/DocumentDetail'
import KnowledgeBase from './screens/knowledge/KnowledgeBase'
import RecordForm from './screens/RecordForm'
import RecordList from './screens/RecordList'

import './admin.css'
import './knowledge.css'

/**
 * The control room.
 *
 * Two gates before anything renders: the session has to exist, and the account
 * has to be staff. Both are re-checked by the server on every request — this is
 * what the person sees, not what protects the data.
 */

export default function AdminApp() {
  const { user, isLoading, isAuthenticated, isStaff } = useAuth()

  if (isLoading) return <FullPage label="Checking your session" />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isStaff) return <NoAccess email={user?.email} />

  return <Panel />
}

/**
 * Loaded once, above the routes: the sidebar is the same on every screen, and
 * re-fetching it on each navigation would make the whole frame flicker.
 */
function Panel() {
  const navigation = useAsync((signal) => fetchNavigation({ signal }), [])
  const { toasts, push, dismiss } = useToasts()

  if (navigation.loading) return <FullPage label="Loading the control room" />
  if (navigation.error) {
    return (
      <div className="cf-fullpage">
        <ErrorState message={navigation.error} onRetry={navigation.reload} />
      </div>
    )
  }

  return (
    <Shell navigation={navigation.data}>
      <Routes>
        <Route index element={<Dashboard />} />

        {/* The knowledge base is not a collection of rows to edit — it is a
            pipeline to operate. Uploading, retrying and reindexing have no
            expression in the generic form, so it gets a screen of its own, and
            one document gets a second for its versions and ingestion jobs.
            Static segments match before `:resource`, so the sidebar link the
            registry produces for `knowledge-bases` lands here rather than on
            the generic list. */}
        <Route path="knowledge-bases" element={<KnowledgeBase onNotify={push} />} />
        <Route path="knowledge-documents/:id" element={<DocumentDetail onNotify={push} />} />

        {/* Website analytics. Also a static segment, and also not a registered
            collection: these are reports over the visit tables, not rows to
            edit. The page drill-in takes its path as a query parameter — a page
            path contains slashes, which no route segment survives cleanly. */}
        <Route path="analytics" element={<Analytics />} />
        <Route path="analytics/page" element={<PageAnalytics />} />

        <Route path=":resource" element={<RecordList onNotify={push} />} />
        <Route path=":resource/:id" element={<RecordForm onNotify={push} />} />
        <Route path="*" element={<Navigate to="/control" replace />} />
      </Routes>
      <Toasts toasts={toasts} onDismiss={dismiss} />
    </Shell>
  )
}

function FullPage({ label }) {
  return (
    <div className="cf-fullpage">
      <Spinner label={label} />
      <p className="cf-fullpage__text">{label}…</p>
    </div>
  )
}

/** Signed in, but not cleared for the control room. */
function NoAccess({ email }) {
  return (
    <div className="cf-fullpage">
      <div className="cf-state">
        <p className="cf-state__title">Not authorised</p>
        <p className="cf-state__body">
          You are signed in as <strong>{email}</strong>, but this account does not have control
          room access. Ask an administrator to grant staff access.
        </p>
        <a className="cf-btn cf-btn--ghost" href="/">
          Return to zionlifts.com
        </a>
      </div>
    </div>
  )
}
