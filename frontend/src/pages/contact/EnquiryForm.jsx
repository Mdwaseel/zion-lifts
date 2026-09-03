import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Arrow, Check, Close } from '@/components/icons'
import { post } from '@/lib/api'

const PROPERTY_TYPES = [
  ['villa', 'Villa / house'],
  ['apartment', 'Apartment building'],
  ['office', 'Office / commercial'],
  ['hotel', 'Hotel / hospitality'],
  ['hospital', 'Hospital / healthcare'],
  ['institutional', 'Institutional'],
  ['industrial', 'Industrial'],
  ['retail', 'Retail'],
  ['other', 'Something else'],
]

const STAGES = [
  ['planning', 'Planning or design'],
  ['construction', 'Under construction'],
  ['ready', 'Building is ready'],
  ['replacement', 'Replacing a lift'],
]

const INSTALL_KINDS = [
  ['new', 'New installation'],
  ['replacement', 'Replacement'],
  ['modernisation', 'Modernisation'],
]

const STEPS = ['Project', 'Configuration', 'Brief']
const MAX_FILES = 6
const MAX_BYTES = 10 * 1024 * 1024

/** Live sheet that reads back what has been filled so far. */
export function ProjectSummary({ form, files, lifts }) {
  const lift = lifts.find((l) => String(l.id) === String(form.lift_type))
  const rows = [
    ['Property', PROPERTY_TYPES.find(([k]) => k === form.property_type)?.[1]],
    ['Stage', STAGES.find(([k]) => k === form.project_stage)?.[1]],
    ['Location', form.location],
    ['Floors', form.floors],
    ['System', lift?.name ?? (form.lift_type_note === 'not-sure' ? 'Not sure yet' : null)],
    ['Capacity', form.capacity],
    ['Stops', form.stops],
    ['Scope', INSTALL_KINDS.find(([k]) => k === form.installation_kind)?.[1]],
    ['Attachments', files.length ? `${files.length} drawing${files.length > 1 ? 's' : ''}` : null],
  ].filter(([, v]) => v)

  return (
    <aside className="summary" aria-label="Your project so far">
      <p className="summary__eyebrow mono">Your project</p>
      {rows.length === 0 ? (
        <p className="summary__empty">
          As you fill the form, this becomes a project brief our engineers can read at a glance.
        </p>
      ) : (
        <dl className="summary__list">
          {rows.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      )}
      {form.name && (
        <p className="summary__ready">
          <Check size={14} /> Ready to discuss.
        </p>
      )}
    </aside>
  )
}

export default function EnquiryForm({ lifts = [], onSnapshot }) {
  const [params] = useSearchParams()
  const preLift = params.get('lift')
  const preConfig = params.get('config')

  const initial = useMemo(() => {
    const liftId = lifts.find((l) => l.slug === preLift)?.id ?? ''
    return {
      property_type: '',
      project_stage: '',
      location: '',
      floors: '',
      lift_type: liftId,
      lift_type_note: liftId ? '' : '',
      capacity: '',
      stops: '',
      installation_kind: 'new',
      name: '',
      phone: '',
      email: '',
      organisation: '',
      message: params.get('variant') ? `Interested in variant ${params.get('variant')}.` : '',
      consent: false,
      website: '', // honeypot
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lifts.length, preLift])

  const [form, setForm] = useState(initial)
  const [step, setStep] = useState(0)
  const [files, setFiles] = useState([])
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState('idle') // idle | sending | done | error
  const [note, setNote] = useState('') // why the last send failed, when the API says
  const [result, setResult] = useState(null)
  const fileInput = useRef(null)

  // keep the lift preselected once the catalogue arrives
  const liftId = form.lift_type || initial.lift_type

  // mirror state outward so the page can render a live project summary
  useEffect(() => {
    onSnapshot?.({ form, files })
  }, [form, files, onSnapshot])

  const set = (k, v) => {
    setForm((f) => ({ ...f, [k]: v }))
    setErrors((e) => (e[k] ? { ...e, [k]: undefined } : e))
  }

  const addFiles = (list) => {
    const incoming = [...list]
    const next = [...files]
    const rejected = []
    for (const f of incoming) {
      if (next.length >= MAX_FILES) {
        rejected.push(`${f.name}: only ${MAX_FILES} files allowed`)
        continue
      }
      if (f.size > MAX_BYTES) {
        rejected.push(`${f.name}: larger than 10 MB`)
        continue
      }
      next.push(f)
    }
    setFiles(next)
    setErrors((e) => ({ ...e, uploads: rejected.length ? rejected.join('. ') : undefined }))
  }

  const validate = (which) => {
    const e = {}
    if (which >= 2) {
      if (!form.name.trim()) e.name = 'We need a name to address the reply to.'
      if (!form.phone.trim()) e.phone = 'A phone number gets you a faster answer.'
      if (!form.email.trim()) e.email = 'We send written quotations by email.'
      else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) e.email = 'That address looks incomplete.'
      if (!form.consent) e.consent = 'Please confirm we may contact you about this enquiry.'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const next = () => {
    if (validate(step)) setStep((s) => Math.min(STEPS.length - 1, s + 1))
  }

  const submit = async (ev) => {
    ev.preventDefault()
    if (!validate(2)) return
    setStatus('sending')
    try {
      const body = {
        ...form,
        lift_type: liftId || '',
        lift_type_note: liftId ? '' : 'not-sure',
        source_path: window.location.pathname + window.location.search,
        configuration: preConfig
          ? Object.fromEntries(preConfig.split(',').map((p) => p.split('=')))
          : {},
      }
      delete body.website
      const res = await post('enquiries/', { ...body, website: form.website }, { files })
      setResult(res)
      setStatus('done')
    } catch (err) {
      const fieldErrors = {}
      for (const [k, v] of Object.entries(err.fields ?? {})) {
        fieldErrors[k] = Array.isArray(v) ? v.join(' ') : String(v)
      }
      setErrors(fieldErrors)
      setNote(err.static ? err.message : '')
      setStatus('error')
      // send the user back to the step that holds the first bad field
      if (fieldErrors.name || fieldErrors.email || fieldErrors.phone || fieldErrors.consent) {
        setStep(2)
      }
    }
  }

  if (status === 'done') {
    return (
      <div className="enquiry enquiry--done" role="status">
        <span className="enquiry__tick" aria-hidden="true">
          <Check size={26} />
        </span>
        <h3 className="h3">Received.</h3>
        <p className="body">{result?.message}</p>
        {result?.reference && (
          <p className="enquiry__ref mono">Reference {result.reference}</p>
        )}
        <p className="small">
          If it is urgent, call us rather than waiting — the number is at the top of this page.
        </p>
      </div>
    )
  }

  return (
    <form className="enquiry" onSubmit={submit} noValidate>
      {/* step rail */}
      <ol className="enquiry__steps">
        {STEPS.map((label, i) => (
          <li key={label} className={i === step ? 'is-on' : i < step ? 'is-done' : ''}>
            <button
              type="button"
              onClick={() => (i < step ? setStep(i) : validate(step) && setStep(i))}
              aria-current={i === step ? 'step' : undefined}
            >
              <span className="enquiry__step-n">{String(i + 1).padStart(2, '0')}</span>
              <span className="enquiry__step-label">{label}</span>
            </button>
          </li>
        ))}
      </ol>

      {/* --- step 1: project --- */}
      <fieldset className="enquiry__panel" hidden={step !== 0}>
        <legend className="sr-only">About the project</legend>
        <div className="field">
          <span className="field__label">What kind of building?</span>
          <div className="chips">
            {PROPERTY_TYPES.map(([k, label]) => (
              <button
                key={k}
                type="button"
                className={`chip ${form.property_type === k ? 'is-on' : ''}`}
                onClick={() => set('property_type', k)}
                aria-pressed={form.property_type === k}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <span className="field__label">Where is the project?</span>
          <div className="chips">
            {STAGES.map(([k, label]) => (
              <button
                key={k}
                type="button"
                className={`chip ${form.project_stage === k ? 'is-on' : ''}`}
                onClick={() => set('project_stage', k)}
                aria-pressed={form.project_stage === k}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="formgrid formgrid--2">
          <label className="field">
            <span className="field__label">Location</span>
            <input
              type="text"
              value={form.location}
              onChange={(e) => set('location', e.target.value)}
              placeholder="Area, city"
              autoComplete="address-level2"
            />
          </label>
          <label className="field">
            <span className="field__label">Number of floors</span>
            <input
              type="text"
              value={form.floors}
              onChange={(e) => set('floors', e.target.value)}
              placeholder="e.g. Ground + 3"
            />
          </label>
        </div>
      </fieldset>

      {/* --- step 2: configuration --- */}
      <fieldset className="enquiry__panel" hidden={step !== 1}>
        <legend className="sr-only">Configuration</legend>
        <div className="field">
          <span className="field__label">Which system?</span>
          <div className="chips">
            {lifts.map((l) => (
              <button
                key={l.slug}
                type="button"
                className={`chip ${String(liftId) === String(l.id) ? 'is-on' : ''}`}
                onClick={() => set('lift_type', l.id)}
                aria-pressed={String(liftId) === String(l.id)}
              >
                {l.short_name || l.name}
              </button>
            ))}
            <button
              type="button"
              className={`chip ${!liftId ? 'is-on' : ''}`}
              onClick={() => set('lift_type', '')}
              aria-pressed={!liftId}
            >
              Not sure yet
            </button>
          </div>
          <p className="field__hint">
            Not sure is a perfectly good answer — recommending the right one is our job.
          </p>
        </div>

        <div className="formgrid formgrid--2">
          <label className="field">
            <span className="field__label">Capacity</span>
            <input
              type="text"
              value={form.capacity}
              onChange={(e) => set('capacity', e.target.value)}
              placeholder="e.g. 6 persons / 408 kg"
            />
          </label>
          <label className="field">
            <span className="field__label">Number of stops</span>
            <input
              type="text"
              value={form.stops}
              onChange={(e) => set('stops', e.target.value)}
              placeholder="e.g. 4"
            />
          </label>
        </div>

        <div className="field">
          <span className="field__label">Scope</span>
          <div className="chips">
            {INSTALL_KINDS.map(([k, label]) => (
              <button
                key={k}
                type="button"
                className={`chip ${form.installation_kind === k ? 'is-on' : ''}`}
                onClick={() => set('installation_kind', k)}
                aria-pressed={form.installation_kind === k}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </fieldset>

      {/* --- step 3: brief --- */}
      <fieldset className="enquiry__panel" hidden={step !== 2}>
        <legend className="sr-only">Your details</legend>
        <div className="formgrid formgrid--2">
          <label className={`field ${errors.name ? 'field--error' : ''}`}>
            <span className="field__label">
              Name <span className="req">*</span>
            </span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              autoComplete="name"
              required
            />
            {errors.name && <span className="field__error">{errors.name}</span>}
          </label>
          <label className={`field ${errors.phone ? 'field--error' : ''}`}>
            <span className="field__label">
              Phone <span className="req">*</span>
            </span>
            <input
              type="tel"
              value={form.phone}
              onChange={(e) => set('phone', e.target.value)}
              autoComplete="tel"
              required
            />
            {errors.phone && <span className="field__error">{errors.phone}</span>}
          </label>
          <label className={`field ${errors.email ? 'field--error' : ''}`}>
            <span className="field__label">
              Email <span className="req">*</span>
            </span>
            <input
              type="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              autoComplete="email"
              required
            />
            {errors.email && <span className="field__error">{errors.email}</span>}
          </label>
          <label className="field">
            <span className="field__label">Organisation</span>
            <input
              type="text"
              value={form.organisation}
              onChange={(e) => set('organisation', e.target.value)}
              autoComplete="organization"
            />
          </label>
        </div>

        <label className="field">
          <span className="field__label">Anything else we should know?</span>
          <textarea
            value={form.message}
            onChange={(e) => set('message', e.target.value)}
            placeholder="Constraints, timelines, what the lift has to fit into…"
          />
        </label>

        {/* drawings */}
        <div className={`field ${errors.uploads ? 'field--error' : ''}`}>
          <span className="field__label">Drawings</span>
          <div
            className="dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              addFiles(e.dataTransfer.files)
            }}
          >
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.webp,.dwg,.dxf"
              onChange={(e) => {
                addFiles(e.target.files)
                e.target.value = ''
              }}
              className="sr-only"
              id="enquiry-uploads"
            />
            <label htmlFor="enquiry-uploads" className="dropzone__label">
              <strong>Attach a plan or section</strong>
              <span>PDF, JPG, PNG, WEBP, DWG or DXF — up to {MAX_FILES} files, 10 MB each</span>
            </label>
          </div>
          {files.length > 0 && (
            <ul className="filelist">
              {files.map((f, i) => (
                <li key={`${f.name}-${i}`}>
                  <span>{f.name}</span>
                  <span className="filelist__size">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
                  <button
                    type="button"
                    onClick={() => setFiles(files.filter((_, j) => j !== i))}
                    aria-label={`Remove ${f.name}`}
                  >
                    <Close size={13} />
                  </button>
                </li>
              ))}
            </ul>
          )}
          {errors.uploads && <span className="field__error">{errors.uploads}</span>}
        </div>

        <label className={`checkbox ${errors.consent ? 'field--error' : ''}`}>
          <input
            type="checkbox"
            checked={form.consent}
            onChange={(e) => set('consent', e.target.checked)}
          />
          <span>
            I&rsquo;m happy for Zion Lifts to contact me about this enquiry. We use your details
            only to answer it — see the <a href="/privacy">privacy policy</a>.
          </span>
        </label>
        {errors.consent && <span className="field__error">{errors.consent}</span>}
      </fieldset>

      {/* honeypot — off-screen, never focusable by a person */}
      <div className="honeypot" aria-hidden="true">
        <label>
          Website
          <input
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={form.website}
            onChange={(e) => set('website', e.target.value)}
          />
        </label>
      </div>

      {errors.non_field_errors && <p className="field__error">{errors.non_field_errors}</p>}
      {status === 'error' && !Object.keys(errors).length && (
        <p className="field__error">
          {note || 'Something went wrong sending that. Please call us instead — we would rather not lose it.'}
        </p>
      )}

      <div className="enquiry__actions">
        {step > 0 && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setStep(step - 1)}>
            Back
          </button>
        )}
        {step < STEPS.length - 1 ? (
          <button type="button" className="btn btn--accent btn--sm" onClick={next}>
            Continue <Arrow size={14} />
          </button>
        ) : (
          <button type="submit" className="btn btn--accent btn--sm" disabled={status === 'sending'}>
            {status === 'sending' ? 'Sending…' : 'Send enquiry'} <Arrow size={14} />
          </button>
        )}
      </div>
    </form>
  )
}

export { PROPERTY_TYPES, STAGES, INSTALL_KINDS }
