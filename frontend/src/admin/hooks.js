/**
 * Data-fetching hooks for the panel.
 *
 * Small on purpose: the project has no query library, and the panel's needs are
 * "fetch this, tell me if it failed, let me refetch". Everything here cancels
 * on unmount so a fast click through the sidebar cannot land a stale response
 * on the wrong screen.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { messageFor } from './api'
import { fetchDocumentStatus } from './knowledge-api'

/**
 * Runs `loader(signal)` whenever `deps` change.
 *
 * `loader` is called with an AbortSignal and must pass it to the API, which is
 * what makes the cancellation real rather than just ignoring a late result.
 */
export function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [nonce, setNonce] = useState(0)

  // The loader is usually an inline arrow, so it is a new function every
  // render; depending on `deps` rather than on the loader itself is what stops
  // that from looping.
  const run = useCallback(loader, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const controller = new AbortController()
    setState((current) => ({ ...current, loading: true, error: null }))

    run(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ data, error: null, loading: false })
      })
      .catch((error) => {
        if (controller.signal.aborted || error?.name === 'AbortError') return
        setState({ data: null, error: messageFor(error), loading: false })
      })

    return () => controller.abort()
  }, [run, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { ...state, reload }
}

/** Debounces a value — used so typing in the search box is not one request per key. */
export function useDebounced(value, delay = 300) {
  const [settled, setSettled] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return settled
}

/**
 * Transient status messages.
 *
 * A save is the one action with no other visible confirmation — the form looks
 * the same afterwards — so it needs one.
 */
export function useToasts() {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(1)

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const push = useCallback(
    (message, tone = 'success') => {
      const id = nextId.current++
      setToasts((current) => [...current, { id, message, tone }])
      setTimeout(() => dismiss(id), 4500)
      return id
    },
    [dismiss],
  )

  return useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss])
}

/**
 * Two-step confirmation for a destructive button.
 *
 * The first click arms it, the second performs it, and it disarms itself after
 * a few seconds or when anything else is clicked. Deliberately not
 * `window.confirm`: that blocks the whole tab, cannot be styled, and is
 * invisible to anything driving the page.
 */
export function useArmed(timeout = 4000) {
  const [armedKey, setArmedKey] = useState(null)
  const timer = useRef(null)

  const disarm = useCallback(() => {
    clearTimeout(timer.current)
    setArmedKey(null)
  }, [])

  const arm = useCallback(
    (key) => {
      clearTimeout(timer.current)
      setArmedKey(key)
      timer.current = setTimeout(() => setArmedKey(null), timeout)
    },
    [timeout],
  )

  useEffect(() => () => clearTimeout(timer.current), [])

  return { armedKey, arm, disarm, isArmed: (key) => armedKey === key }
}

/**
 * Follows one document's ingestion until it settles.
 *
 * Polling, not a timer-driven illusion: every value shown comes from the
 * backend's own state. The three rules that keep it from becoming a nuisance
 * are all here rather than at the call site, because forgetting any one of them
 * produces a page that quietly hammers the server.
 *
 *   1. It stops. READY, FAILED and DELETED are terminal, and there is nothing
 *      further to learn by asking again.
 *   2. It backs off. A document takes minutes, not milliseconds; the interval
 *      grows from a second towards `maxInterval` so a long ingestion costs a
 *      handful of requests rather than hundreds.
 *   3. It stops when the tab is hidden, and catches up when it comes back.
 *      Nobody is watching a background tab, and a laptop left open overnight
 *      should not spend the night polling.
 *
 * Unmounting aborts the request in flight — see the cleanup below.
 */
const TERMINAL = new Set(['ready', 'failed', 'deleted'])

export function useIngestionStatus(documentId, { enabled = true, onSettled } = {}) {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const settledRef = useRef(false)
  const onSettledRef = useRef(onSettled)
  onSettledRef.current = onSettled

  useEffect(() => {
    if (!documentId || !enabled) return

    let cancelled = false
    let timer = null
    let interval = 1000
    const controller = new AbortController()
    settledRef.current = false

    const schedule = () => {
      // Grows towards the ceiling rather than staying at one second: an
      // ingestion is minutes of work, and a fixed fast poll is mostly noise.
      interval = Math.min(Math.round(interval * 1.5), 10000)
      timer = setTimeout(tick, interval)
    }

    const tick = async () => {
      if (cancelled) return
      if (document.hidden) {
        // Nobody is looking. Check back when the tab is visible again.
        timer = setTimeout(tick, 5000)
        return
      }

      try {
        const next = await fetchDocumentStatus(documentId, { signal: controller.signal })
        if (cancelled) return
        setStatus(next)
        setError(null)

        if (TERMINAL.has(next.status)) {
          settledRef.current = true
          onSettledRef.current?.(next)
          return
        }
      } catch (caught) {
        if (cancelled || caught?.name === 'AbortError') return
        // A blip should not stop the watch — the document is still processing
        // whether or not this one request landed.
        setError(messageFor(caught))
      }
      schedule()
    }

    tick()

    return () => {
      cancelled = true
      clearTimeout(timer)
      controller.abort()
    }
  }, [documentId, enabled])

  return { status, error, isSettled: settledRef.current }
}
