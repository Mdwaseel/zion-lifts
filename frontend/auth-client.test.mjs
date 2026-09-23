/**
 * Tests for the authenticated API client's refresh behaviour.
 *
 *   node --test auth-client.test.mjs
 *
 * The interceptor is the one piece of the auth layer that cannot be covered by
 * the Django suite, and the failure modes it guards against — an infinite
 * refresh loop, or five parallel 401s firing five refreshes and rotating each
 * other's tokens away — are exactly the kind that only show up in production.
 *
 * `fetch`, `document` and `import.meta.env` are stubbed, so this runs in plain
 * Node with no browser and no server.
 */

import assert from 'node:assert/strict'
import { mock, test } from 'node:test'

globalThis.document = { cookie: 'csrftoken=test-csrf-token' }

// The module reads import.meta.env at load time; Node has no such thing.
process.env.VITE_API_BASE = '/api'

/** Loads a fresh copy of the client, so module-level refresh state is reset. */
async function loadClient() {
  const url = new URL('./src/api/client.js', import.meta.url)
  return import(`${url.href}?bust=${Math.random()}`)
}

function response(status, body = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

/** Records every call so the test can assert on order and headers. */
function stubFetch(handler) {
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init })
    return handler(url, init, calls.length)
  }
  return calls
}

test('a 200 is returned as parsed JSON', async () => {
  const { api } = await loadClient()
  stubFetch(() => response(200, { detail: 'ok' }))

  assert.deepEqual(await api.get('accounts/me/'), { detail: 'ok' })
})

test('unsafe methods carry the CSRF header, safe ones do not', async () => {
  const { api } = await loadClient()
  const calls = stubFetch(() => response(200, {}))

  await api.get('accounts/me/')
  await api.post('accounts/logout/', {})

  assert.equal(calls[0].init.headers['X-CSRFToken'], undefined)
  assert.equal(calls[1].init.headers['X-CSRFToken'], 'test-csrf-token')
})

test('every request sends cookies', async () => {
  const { api } = await loadClient()
  const calls = stubFetch(() => response(200, {}))

  await api.get('accounts/me/')
  assert.equal(calls[0].init.credentials, 'include')
})

test('a GET never sends a body', async () => {
  const { api } = await loadClient()
  const calls = stubFetch(() => response(200, {}))

  await api.get('accounts/me/')
  assert.equal('body' in calls[0].init, false)
})

test('a 401 refreshes once and retries the original request', async () => {
  const { api } = await loadClient()
  const calls = stubFetch((url, init, n) => {
    if (n === 1) return response(401, { detail: 'expired' })
    if (url.includes('refresh')) return response(200, { detail: 'Token refreshed.' })
    return response(200, { email: 'admin@example.com' })
  })

  const user = await api.get('accounts/me/')

  assert.deepEqual(user, { email: 'admin@example.com' })
  assert.deepEqual(
    calls.map((c) => c.url),
    ['/api/accounts/me/', '/api/accounts/refresh/', '/api/accounts/me/'],
  )
})

test('a retry that 401s again does not loop', async () => {
  const { api } = await loadClient()
  const calls = stubFetch((url) =>
    url.includes('refresh') ? response(200, {}) : response(401, { detail: 'nope' }),
  )

  await assert.rejects(api.get('accounts/me/'), (error) => error.status === 401)

  // me, refresh, me — and then it stops.
  assert.equal(calls.length, 3)
})

test('a failing refresh surfaces the 401 rather than retrying', async () => {
  const { api } = await loadClient()
  const calls = stubFetch((url) =>
    url.includes('refresh') ? response(401, { code: 'refresh_invalid' }) : response(401, {}),
  )

  await assert.rejects(api.get('accounts/me/'), (error) => error.status === 401)
  assert.equal(calls.length, 2)
})

test('the login and refresh endpoints never trigger a refresh of their own', async () => {
  const { api } = await loadClient()

  for (const path of ['accounts/login/', 'accounts/refresh/', 'accounts/logout/']) {
    const calls = stubFetch(() => response(401, { detail: 'no' }))
    await assert.rejects(api.post(path, {}))
    assert.equal(calls.length, 1, `${path} should not have been retried`)
  }
})

test('concurrent 401s share a single refresh', async () => {
  const { api } = await loadClient()
  let refreshes = 0
  stubFetch(async (url) => {
    if (url.includes('refresh')) {
      refreshes += 1
      await new Promise((r) => setTimeout(r, 20)) // the rotation round trip
      return response(200, {})
    }
    return refreshes === 0 ? response(401, {}) : response(200, { ok: true })
  })

  const results = await Promise.all([
    api.get('accounts/me/'),
    api.get('site/'),
    api.get('lifts/'),
    api.get('projects/'),
  ])

  // One refresh for four failures. Five would rotate four tokens into oblivion.
  assert.equal(refreshes, 1)
  assert.deepEqual(results, [{ ok: true }, { ok: true }, { ok: true }, { ok: true }])
})

test('a network failure becomes an ApiError rather than a raw TypeError', async () => {
  const { api, ApiError } = await loadClient()
  globalThis.fetch = async () => {
    throw new TypeError('Failed to fetch')
  }

  await assert.rejects(api.get('accounts/me/'), (error) => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.status, 0)
    assert.equal(error.code, 'network')
    return true
  })
})

test('an abort is passed through untouched', async () => {
  const { api } = await loadClient()
  globalThis.fetch = async () => {
    const error = new Error('aborted')
    error.name = 'AbortError'
    throw error
  }

  await assert.rejects(api.get('accounts/me/'), (error) => error.name === 'AbortError')
})

test('field errors are separated from detail and code', async () => {
  const { api } = await loadClient()
  stubFetch(() =>
    response(400, { detail: 'bad', code: 'x', email: ['Enter a valid email address.'] }),
  )

  await assert.rejects(api.post('accounts/login/', {}), (error) => {
    assert.deepEqual(error.fields, { email: ['Enter a valid email address.'] })
    assert.equal(error.code, 'x')
    return true
  })
})

mock.reset()
