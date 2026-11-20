import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeftIcon, ArrowRightIcon, ArrowsClockwiseIcon, FileTextIcon, HandTapIcon, ShuffleSimpleIcon, SignatureIcon, UsersThreeIcon } from '@phosphor-icons/react'
import { bank, BankError, money, textError, type RequestType, type RequestValues, type StaffFile, type StaffSession } from './api'
import { Brand, DeskIcon } from './Brand'
import './request.css'

const empty = { subject: '', context: '', reference: '', requested_date: '', amount: '', currency: '', notes: '' }
type Draft = typeof empty

function minorUnits(value: string) {
  const match = /^(\d{1,12}|\d{1,3}(?:,\d{3}){1,3})(?:\.(\d{1,2}))?$/.exec(value.trim())
  if (!match) return null
  const minor = Number(match[1].replace(/,/g, '')) * 100 + Number((match[2] || '').padEnd(2, '0'))
  return minor > 0 && minor <= 99_999_999_999_999 ? minor : null
}

function exampleDraft(value: RequestValues): Draft {
  const n = value.amount_minor
  return { subject: value.subject, context: value.context, reference: value.reference, notes: value.notes,
    requested_date: value.requested_date, currency: value.currency || '',
    amount: n == null ? '' : Math.floor(n / 100) + '.' + String(n % 100).padStart(2, '0') }
}

type ComposerProps = { session: StaffSession | null; preferred: string; cancel: () => void; created: (session: StaffSession, id: string, runId: string) => void }

export default function RequestComposer({ session, preferred, cancel, created }: ComposerProps) {
  const [types, setTypes] = useState<RequestType[] | null>(null)
  const [selected, setSelected] = useState('')
  const [draft, setDraft] = useState<Draft>(empty)
  const [filled, setFilled] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const inFlight = useRef(false)
  const drafts = useRef(new Map<string, { draft: Draft; filled: number }>())
  const attempt = useRef({ input: '', key: '' })
  const demo = !session || session.staff.desk_picker
  const type = types?.find(item => item.id === selected)

  useEffect(() => {
    let active = true
    window.scrollTo(0, 0)
    setError('')
    bank<RequestType[]>(demo ? null : session!.token, '/request-types').then(items => {
      if (!active) return
      const first = items.find(item => item.id === preferred) || items[0]
      setTypes(items); setSelected(first?.id || ''); setDraft({ ...empty, currency: first?.currencies[0] || '' })
    }).catch(err => { if (active) setError(textError(err)) })
    return () => { active = false }
  }, [demo, session, preferred, retry])

  function choose(id: string) {
    const next = types?.find(item => item.id === id)
    drafts.current.set(selected, { draft, filled })
    const remembered = drafts.current.get(id)
    setSelected(id); setDraft(remembered?.draft || { ...empty, currency: next?.currencies[0] || '' })
    setFilled(remembered?.filled || 0); setError('')
  }
  function update(field: keyof Draft, value: string) {
    setDraft(previous => ({ ...previous, [field]: value })); setError('')
  }
  function fill() {
    if (!type) return
    const index = filled % type.examples.length
    setDraft(exampleDraft(type.examples[index])); setFilled(index + 1); setError('')
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!type || inFlight.current) return
    const amount = type.amount_label ? minorUnits(draft.amount) : null
    if (type.amount_label && amount === null) { setError('Enter a positive amount with up to two decimal places.'); return }
    const body: RequestValues & { workflow_id: string } = { workflow_id: type.id, subject: draft.subject.trim(),
      context: draft.context.trim(), reference: draft.reference.trim(), requested_date: draft.requested_date,
      notes: draft.notes.trim(), amount_minor: amount, currency: type.amount_label ? draft.currency : null }
    if (body.subject.length < 3 || body.context.length < 2) { setError('Enter a subject and complete the request details.'); return }
    inFlight.current = true; setBusy(true); setError('')
    const input = JSON.stringify(body)
    if (attempt.current.input !== input) attempt.current = { input, key: crypto.randomUUID() }
    try {
      const owner = demo && session?.staff.id !== type.desk_id
        ? await bank<StaffSession>(null, '/demo-session', { desk_id: type.desk_id }) : session
      if (!owner) throw Error('The originating desk is unavailable.')
      const receipt = await bank<{ case_id: string; run: { run_id: string } }>(owner.token, '/intake', body, attempt.current.key)
      created(owner, receipt.case_id, receipt.run.run_id)
    } catch (err) {
      if (err instanceof BankError && err.status > 0 && err.status < 500) attempt.current = { input: '', key: '' }
      setError(textError(err))
    } finally { inFlight.current = false; setBusy(false) }
  }
  const groups = [...new Set(types?.map(item => item.group))]
  return <main className="compose-page"><header className="entry-header"><div className="entry-mast"><Brand /><span className="mast-unit">Corporate banking</span></div>
    <button className="compose-back" type="button" disabled={busy} onClick={cancel}><ArrowLeftIcon size={16} /> {session ? 'Back to desk' : 'Desk directory'}</button></header>
    <div className="compose-body"><div className="compose-intro"><h1>New request</h1><p>Submit the details to get an agent recommendation before you send the case for desk review.</p></div>
      {!types ? <div className="card" role={error ? 'alert' : 'status'}>{error || 'Loading request types…'} {error && <button onClick={() => setRetry(n => n + 1)}>Try again</button>}</div>
      : !type ? <p className="card">Your desk reviews existing requests. Open your desk to see the assigned files.</p>
      : <div className="compose-layout"><form className="compose-form" onSubmit={submit}><fieldset disabled={busy}>
        <label className="type-picker">Request type<select value={selected} onChange={e => choose(e.target.value)}>{groups.map(group => <optgroup key={group} label={group}>
          {types.filter(item => item.group === group).map(item => <option key={item.id} value={item.id}>{item.title} · {item.desk}</option>)}
        </optgroup>)}</select></label>
        <div className="compose-fields"><div className="compose-section"><h2>Request details</h2><button type="button" className="fill-demo" onClick={fill}><ShuffleSimpleIcon size={16} />{filled ? 'Next demo example' : 'Fill demo example'}</button></div>
          {filled > 0 && <p className="fill-feedback" role="status">Example {filled} of {type.examples.length} loaded with {type.examples[filled - 1].reference ? 'a supporting reference' : 'a missing reference'}. You can edit every field.</p>}
          <label>Subject<input required minLength={3} maxLength={120} value={draft.subject} onChange={e => update('subject', e.target.value)} placeholder={type.examples[0].subject} /></label>
          <label>{type.context_label}<input required minLength={2} maxLength={160} value={draft.context} onChange={e => update('context', e.target.value)} placeholder={type.examples[0].context} /></label>
          {type.amount_label && <div className="compose-row amount-row"><label>{type.amount_label}<input required inputMode="decimal" maxLength={18} placeholder="0.00" value={draft.amount} onChange={e => update('amount', e.target.value)} /></label>
            <label>Currency<select value={draft.currency} onChange={e => update('currency', e.target.value)}>{type.currencies.map(c => <option key={c}>{c}</option>)}</select></label></div>}
          <div className="compose-row"><label>{type.date_label}<input type="date" required min={type.min_date} value={draft.requested_date} onChange={e => update('requested_date', e.target.value)} /></label>
          <label>{type.source_label} reference <span className="optional">Optional</span><input maxLength={80} value={draft.reference} onChange={e => update('reference', e.target.value)} placeholder="Record reference" /></label></div>
          <label>Notes for the desk <span className="optional">Optional</span><textarea rows={2} maxLength={1200} value={draft.notes} onChange={e => update('notes', e.target.value)} /></label>
        </div>{error && <p className="compose-error" role="alert">{error}</p>}
        <div className="compose-submit"><button className="primary" type="submit">{busy ? 'Submitting…' : 'Submit request'} <ArrowRightIcon size={17} /></button></div>
      </fieldset></form><aside className="compose-route"><div className="compose-desk-icon"><DeskIcon role={type.owner_role} size={32} /></div>
        <h2>{type.desk}</h2><p>{type.title}</p><ol>
          <li><FileTextIcon /><div><small>Originating desk</small><strong>{type.desk}</strong></div></li>
          <li><ArrowsClockwiseIcon /><div><small>Organizer sends to</small><strong>{type.code === 'LC' ? 'Trade Finance, Credit Risk and Compliance' : 'Evidence, policy and handover agents'}</strong></div></li>
          <li><UsersThreeIcon /><div><small>Desk reviewers</small><strong>{type.reviewers?.map(person => person.name).join(' · ')}</strong></div></li>
          <li><SignatureIcon /><div><small>Final human approval</small><strong>{type.final?.name} · {type.decision_desk}</strong></div></li></ol>
      </aside></div>}
    </div></main>
}

export function SubmittedDetails({ file }: { file: StaffFile }) {
  const v = file.request_input
  if (!v) return null
  return <section className="card submitted-details"><div className="track-heading"><HandTapIcon size={18} /><h2>Submitted request</h2></div>
    <h3>{v.subject}</h3><dl>{[['Request detail', v.context], [file.department_case ? 'Review by' : 'Credit expiry', v.requested_date],
      ['Amount', v.currency && money(v.amount_minor, v.currency)], ['Supporting reference', v.reference || 'Awaiting evidence'], ['Desk notes', v.notes]].map(([k, value]) => value && <div key={k}><dt>{k}</dt><dd>{value}</dd></div>)}</dl>
  </section>
}
