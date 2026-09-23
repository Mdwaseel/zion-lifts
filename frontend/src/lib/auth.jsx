import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import * as authApi from '@/api/auth'

/**
 * Who is signed in, and the three things you can do about it.
 *
 * Everything session-shaped lives here so no component has to know how
 * authentication works. Note what the context does *not* hold: a token. The
 * access and refresh tokens are HttpOnly cookies the browser manages; this
 * provider only ever knows the user object the server chooses to describe.
 */

const AuthContext = createContext(null)

const IDLE = { user: null, status: 'loading', error: null }

export function AuthProvider({ children }) {
  const [state, setState] = useState(IDLE)

  // One session check on mount. A 401 here is the normal answer for a visitor
  // who is not signed in, not an error worth showing.
  useEffect(() => {
    const controller = new AbortController()

    authApi
      .currentUser({ signal: controller.signal })
      .then((user) => setState({ user, status: 'authenticated', error: null }))
      .catch((error) => {
        if (error?.name === 'AbortError') return
        setState({ user: null, status: 'anonymous', error: null })
      })

    return () => controller.abort()
  }, [])

  const signIn = useCallback(async (credentials) => {
    const { user } = await authApi.login(credentials)
    setState({ user, status: 'authenticated', error: null })
    return user
  }, [])

  const signOut = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      // Whatever the server said, this browser is done with the session.
      setState({ user: null, status: 'anonymous', error: null })
    }
  }, [])

  /** Re-read the session — after a refresh, or when returning to a stale tab. */
  const revalidate = useCallback(async () => {
    try {
      const user = await authApi.currentUser()
      setState({ user, status: 'authenticated', error: null })
      return user
    } catch {
      setState({ user: null, status: 'anonymous', error: null })
      return null
    }
  }, [])

  const value = useMemo(
    () => ({
      user: state.user,
      status: state.status,
      isLoading: state.status === 'loading',
      isAuthenticated: state.status === 'authenticated',
      isStaff: Boolean(state.user?.is_staff),
      signIn,
      signOut,
      revalidate,
    }),
    [state, signIn, signOut, revalidate],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside an AuthProvider')
  return context
}
