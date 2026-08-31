import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useParams, useSearchParams } from 'react-router-dom'

import { bulkAction, fetchList, fetchOptions, fetchSchema, messageFor, updateRecord } from '../api'
import DataTable from '../components/DataTable'
import { EmptyState, ErrorState, PageHeader, Pagination, Spinner } from '../components/ui'
import { useArmed, useAsync, useDebounced } from '../hooks'

/**
 * The list view, for every collection.
 *
 * Search, filters, sort and page all live in the URL rather than in state, so a
 * filtered table is a link someone can bookmark or paste to a colleague, and
 * the browser's back button does what it looks like it should.
 */

const PAGE_SIZE = 25

export default function RecordList({ onNotify }) {
  const { resource } = useParams()
  const [params, setParams] = useSearchParams()

  const search = params.get('search') ?? ''
  const page = Number(params.get('page') ?? 1)
  const ordering = params.get('ordering') ?? ''

  const [searchDraft, setSearchDraft] = useState(search)
  const debouncedSearch = useDebounced(searchDraft)
  const [selected, setSelected] = useState(() => new Set())
  const [busyId, setBusyId] = useState(null)
  const { isArmed, arm, disarm } = useArmed()

  // The schema changes only when the collection does, so it is fetched apart
  // from the rows — switching page must not re-describe the model.
  const schemaState = useAsync((signal) => fetchSchema(resource, { signal }), [resource])

  const filters = useMemo(() => {
    const active = {}
    for (const [key, value] of params.entries()) {
      if (!['search', 'page', 'ordering'].includes(key) && value !== '') active[key] = value
    }
    return active
  }, [params])

  const listState = useAsync(
    (signal) =>
      fetchList(
        resource,
        { search, page, ordering, page_size: PAGE_SIZE, ...filters },
        { signal },
      ),
    [resource, search, page, ordering, JSON.stringify(filters)],
  )

  // Typing updates the URL once the person pauses, and always returns to page 1
  // — page 4 of the old result set is meaningless against a new one.
  useEffect(() => {
    if (debouncedSearch === search) return
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        if (debouncedSearch) next.set('search', debouncedSearch)
        else next.delete('search')
        next.delete('page')
        return next
      },
      { replace: true },
    )
  }, [debouncedSearch, search, setParams])

  // A new collection means a new set of ids; keeping the old selection would
  // let a bulk action fire at rows the person can no longer see.
  useEffect(() => {
    setSelected(new Set())
    setSearchDraft(params.get('search') ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resource])

  const update = useCallback(
    (key, value) => {
      setParams((current) => {
        const next = new URLSearchParams(current)
        if (value === '' || value === null) next.delete(key)
        else next.set(key, value)
        if (key !== 'page') next.delete('page')
        return next
      })
    },
    [setParams],
  )

  const schema = schemaState.data
  const list = listState.data

  const toggle = (id) =>
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const toggleAll = (checked) =>
    setSelected(checked ? new Set(list.results.map((row) => row.id)) : new Set())

  /** Inline edits save immediately — a list with a Save button is a form. */
  async function onInlineChange(id, field, value) {
    setBusyId(id)
    try {
      await updateRecord(resource, id, { [field]: value })
      listState.reload()
    } catch (error) {
      onNotify(messageFor(error), 'error')
    } finally {
      setBusyId(null)
    }
  }

  async function runBulk(action) {
    const ids = [...selected]
    try {
      const result = await bulkAction(resource, action, ids)
      onNotify(result.detail)
      setSelected(new Set())
      disarm()
      listState.reload()
    } catch (error) {
      onNotify(messageFor(error), 'error')
    }
  }

  if (schemaState.loading) return <Spinner label="Loading collection" />
  if (schemaState.error) return <ErrorState message={schemaState.error} onRetry={schemaState.reload} />

  // Site settings is one row. Showing a list of it and asking someone to click
  // through is a worse page than the record itself; the detail route ignores
  // the id and always resolves to that row.
  if (schema.singleton) return <Navigate to={`/control/${resource}/1`} replace />

  return (
    <section className="cf-page">
      <PageHeader eyebrow={schema.group} title={schema.label_plural} count={list?.count}>
        {schema.permissions.create && (
          <Link className="cf-btn cf-btn--primary" to={`/control/${resource}/new`}>
            New {schema.label.toLowerCase()}
          </Link>
        )}
      </PageHeader>

      <div className="cf-toolbar">
        {schema.search_fields.length > 0 && (
          <div className="cf-search">
            <label className="cf-sr" htmlFor="cf-search">
              Search {schema.label_plural.toLowerCase()}
            </label>
            <input
              id="cf-search"
              className="cf-input"
              type="search"
              placeholder={`Search ${schema.label_plural.toLowerCase()}…`}
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
            />
          </div>
        )}

        {schema.filters.map((filter) => (
          <FilterSelect
            key={filter.name}
            filter={filter}
            resource={resource}
            value={params.get(filter.name) ?? ''}
            onChange={(value) => update(filter.name, value)}
          />
        ))}

        {(search || Object.keys(filters).length > 0) && (
          <button type="button" className="cf-btn cf-btn--ghost cf-btn--sm" onClick={() => setParams({})}>
            Clear
          </button>
        )}
      </div>

      {selected.size > 0 && (
        <div className="cf-bulk" role="region" aria-label="Bulk actions">
          <span className="cf-bulk__count">
            {selected.size} selected
          </span>
          {schema.permissions.edit && hasPublishing(schema) && (
            <>
              <button type="button" className="cf-btn cf-btn--sm" onClick={() => runBulk('publish')}>
                Publish
              </button>
              <button type="button" className="cf-btn cf-btn--sm" onClick={() => runBulk('unpublish')}>
                Unpublish
              </button>
            </>
          )}
          {schema.permissions.delete && (
            <button
              type="button"
              className={`cf-btn cf-btn--sm ${isArmed('bulk') ? 'cf-btn--danger' : 'cf-btn--ghost'}`}
              onClick={() => (isArmed('bulk') ? runBulk('delete') : arm('bulk'))}
            >
              {isArmed('bulk') ? `Delete ${selected.size}? Click again` : 'Delete'}
            </button>
          )}
          <button type="button" className="cf-btn cf-btn--ghost cf-btn--sm" onClick={() => setSelected(new Set())}>
            Clear selection
          </button>
        </div>
      )}

      {listState.loading && <Spinner label="Loading records" />}
      {listState.error && <ErrorState message={listState.error} onRetry={listState.reload} />}

      {list && !listState.loading && (
        list.results.length === 0 ? (
          <EmptyState
            title={search || Object.keys(filters).length ? 'Nothing matches those filters' : `No ${schema.label_plural.toLowerCase()} yet`}
            body={
              search || Object.keys(filters).length
                ? 'Try a broader search, or clear the filters.'
                : undefined
            }
            action={
              schema.permissions.create ? (
                <Link className="cf-btn cf-btn--primary" to={`/control/${resource}/new`}>
                  Add the first one
                </Link>
              ) : undefined
            }
          />
        ) : (
          <>
            <DataTable
              schema={schema}
              rows={list.results}
              selected={selected}
              onToggle={toggle}
              onToggleAll={toggleAll}
              ordering={ordering}
              onSort={(value) => update('ordering', value)}
              onInlineChange={onInlineChange}
              busyId={busyId}
            />
            <Pagination
              page={list.page}
              pages={list.pages}
              count={list.count}
              pageSize={list.page_size}
              onPage={(next) => update('page', next)}
            />
          </>
        )
      )}
    </section>
  )
}

/**
 * One filter dropdown.
 *
 * A choice field carries its options in the schema; a relation cannot, because
 * the options are rows, so those are fetched. The distinction is invisible on
 * screen and that is the point.
 */
function FilterSelect({ filter, resource, value, onChange }) {
  const isRelation = filter.type === 'reference' || filter.type === 'multi_reference'
  const [relationOptions, setRelationOptions] = useState([])

  useEffect(() => {
    if (!isRelation) return undefined
    const controller = new AbortController()
    fetchOptions(resource, filter.name, '', { signal: controller.signal })
      .then((payload) => setRelationOptions(payload[filter.name] ?? []))
      .catch(() => setRelationOptions([]))
    return () => controller.abort()
  }, [isRelation, resource, filter.name])

  const options = isRelation ? relationOptions : staticOptions(filter)
  if (isRelation && options.length === 0) return null // nothing to filter by yet

  const noun = filterNoun(filter)

  return (
    <div className="cf-filter">
      <label className="cf-sr" htmlFor={`filter-${filter.name}`}>
        {noun}
      </label>
      <select
        id={`filter-${filter.name}`}
        className="cf-input cf-input--select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{noun}: any</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function staticOptions(filter) {
  if (filter.type === 'boolean') {
    return [
      { value: 'true', label: 'Yes' },
      { value: 'false', label: 'No' },
    ]
  }
  return filter.choices ?? []
}

/**
 * The noun a filter is about.
 *
 * Boolean fields are named for the question ("Is published"), which makes a
 * dropdown read "All is published". Dropping the "Is " leaves the thing itself,
 * so the control reads "Published: any".
 */
function filterNoun(filter) {
  const label = filter.label ?? filter.name
  return label.replace(/^Is /i, '').replace(/^./, (c) => c.toUpperCase())
}

function hasPublishing(schema) {
  return schema.fields.some((field) => field.name === 'is_published')
}
