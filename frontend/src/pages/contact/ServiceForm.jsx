import { useState } from 'react'

import { Arrow, Check } from '@/components/icons'
import { post } from '@/lib/api'

const KINDS = [
  ['maintenance', 'Maintenance / AMC'],
  ['breakdown', 'Breakdown'],
  ['modernisation', 'Modernisation'],
  ['spares', 'Spare parts'],
]

const URGENCY = [
  ['routine', 'Routine'],
  ['soon', 'Within a few days'],
  ['urgent', 'Urgent — the lift is down'],
]

/**
 * Deliberately separate from the project enquiry: an existing owner needing a
 * technician should never be funnelled into the new-installation sales form.
 */
export default function ServiceForm() {
  const [form, setForm] = useState({
    kind: 'maintenance',
    urgency: 'routine',
    name: '',
    phone: '',
    email: '',
    site_name: '',
    location: '',
    lift_reference: '',
    message: '',
    consent: false,
    website: '',
  })
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState('idle')
  const [note, setNote] = useState('')
  const [result, setResult] = useState(null)

  const set = (k, v) => {
    setForm((f) => ({ ...f, [k]: v }))
    setErrors((e) => (e[k] ? { ...e, [k]: undefined } : e))
  }

  const submit = async (ev) => {
    ev.preventDefault()
    const e = {}
    if (!form.name.trim()) e.name = 'Who should the technician ask for?'
    if (!form.phone.trim()) e.phone = 'We call back on service requests.'
    if (!form.consent) e.consent = 'Please confirm we may contact you.'
    setErrors(e)
    if (Object.keys(e).length) return

    setStatus('sending')
    try {
      const res = await post('service-requests/', form)
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
    }
  }

  if (status === 'done') {
    return (
      <div className="enquiry enquiry--done" role="status">
        <span className="enquiry__tick" aria-hidden="true">
          <Check size={26} />
        </span>
        <h3 className="h3">Logged with the service desk.</h3>
        <p className="body">{result?.message}</p>
        {result?.reference && <p className="enquiry__ref mono">Reference {result.reference}</p>}
      </div>
    )
  }

  return (
    <form className="enquiry enquiry--service" onSubmit={submit} noValidate>
      <div className="field">
        <span className="field__label">What do you need?</span>
        <div className="chips">
          {KINDS.map(([k, label]) => (
            <button
              key={k}
              type="button"
              className={`chip ${form.kind === k ? 'is-on' : ''}`}
              onClick={() => set('kind', k)}
              aria-pressed={form.kind === k}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <span className="field__label">How urgent?</span>
        <div className="chips">
          {URGENCY.map(([k, label]) => (
            <button
              key={k}
              type="button"
              className={`chip ${form.urgency === k ? 'is-on' : ''}`}
              onClick={() => set('urgency', k)}
              aria-pressed={form.urgency === k}
            >
              {label}
            </button>
          ))}
        </div>
        {form.urgency === 'urgent' && (
          <p className="field__hint field__hint--alert">
            If anyone is trapped in the lift, call us now rather than filling this in.
          </p>
        )}
      </div>

      <div className="formgrid formgrid--2">
        <label className={`field ${errors.name ? 'field--error' : ''}`}>
          <span className="field__label">
            Name <span className="req">*</span>
          </span>
          <input type="text" value={form.name} onChange={(e) => set('name', e.target.value)} autoComplete="name" />
          {errors.name && <span className="field__error">{errors.name}</span>}
        </label>
        <label className={`field ${errors.phone ? 'field--error' : ''}`}>
          <span className="field__label">
            Phone <span className="req">*</span>
          </span>
          <input type="tel" value={form.phone} onChange={(e) => set('phone', e.target.value)} autoComplete="tel" />
          {errors.phone && <span className="field__error">{errors.phone}</span>}
        </label>
        <label className="field">
          <span className="field__label">Email</span>
          <input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} autoComplete="email" />
        </label>
        <label className="field">
          <span className="field__label">Building / site name</span>
          <input type="text" value={form.site_name} onChange={(e) => set('site_name', e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Location</span>
          <input type="text" value={form.location} onChange={(e) => set('location', e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Lift reference, if known</span>
          <input
            type="text"
            value={form.lift_reference}
            onChange={(e) => set('lift_reference', e.target.value)}
            placeholder="From the lift operating panel"
          />
        </label>
      </div>

      <label className="field">
        <span className="field__label">What is happening?</span>
        <textarea
          value={form.message}
          onChange={(e) => set('message', e.target.value)}
          placeholder="Noises, doors, levelling, how often it happens…"
        />
      </label>

      <label className={`checkbox ${errors.consent ? 'field--error' : ''}`}>
        <input type="checkbox" checked={form.consent} onChange={(e) => set('consent', e.target.checked)} />
        <span>I&rsquo;m happy for Zion Lifts to contact me about this request.</span>
      </label>
      {errors.consent && <span className="field__error">{errors.consent}</span>}

      <div className="honeypot" aria-hidden="true">
        <label>
          Website
          <input type="text" tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => set('website', e.target.value)} />
        </label>
      </div>

      {status === 'error' && (
        <p className="field__error">
          {note || 'That did not send. Please call the service line instead.'}
        </p>
      )}

      <div className="enquiry__actions">
        <button type="submit" className="btn btn--accent btn--sm" disabled={status === 'sending'}>
          {status === 'sending' ? 'Sending…' : 'Request service'} <Arrow size={14} />
        </button>
      </div>
    </form>
  )
}
