import { useId, useState } from 'react'
import { label, money, roles, type CaseFile, type DeskRequest, type Staff, type Submit } from './api'

type Controls = { file: CaseFile; staff: Staff; busy: boolean; submit: Submit }
const reasonProps = { required: true, minLength: 10, maxLength: 2000, rows: 3 }
const complianceQuestions = [
  'Please supply the supplier invoice for this instrument.',
  'Please confirm the current case evidence for Compliance review.',
]
const complianceReply = 'Compliance has reviewed the request. See the current desk disposition.'
const signed = (file: CaseFile) => ({ revision: file.revision, packet_hash: file.packet_hash })

export function ReasonField({ label, value, change, example, busy }: {
  label: string; value: string; change: (value: string) => void; example?: string; busy: boolean
}) {
  const id = useId()
  return <div className="sign-reason"><div><label htmlFor={id}>{label}</label>
    {example && <button type="button" disabled={busy} onClick={() => change(example)}>Use demo reason</button>}</div>
    <textarea {...reasonProps} id={id} disabled={busy} value={value} onChange={e => change(e.target.value)} aria-describedby={id + '-hint'} />
    <small id={id + '-hint'}>Enter at least 10 characters.</small></div>
}

export function ReviewForm({ file, staff, busy, submit }: Controls) {
  const current = file.reviews.find(item => item.desk === staff.role)
  const ownHolds = file.holds.filter(hold => hold.desk === staff.role)
  const requiresInvoice = ownHolds.some(hold => hold.reason_code === 'DOCUMENT_REQUIRED')
  const missingInvoice = file.human_approval?.evidence_action === 'attach_invoice'
  const blocked = file.clearance_issue || (requiresInvoice && missingInvoice ? 'Coverage must attach the requested invoice to release your hold.' : '')
  const [choice, setChoice] = useState(blocked ? 'hold' : 'clear')
  const [reason, setReason] = useState('')
  const [code, setCode] = useState(missingInvoice ? 'DOCUMENT_REQUIRED' : 'MANUAL_REVIEW')
  const [resolved, setResolved] = useState<string[]>([])
  const [source, setSource] = useState('')
  const needsEvidence = choice === 'clear' && ownHolds.length > 0
  const references = requiresInvoice ? (file.invoice_ref ? [file.invoice_ref] : []) : file.sources.map(item => item.ref)

  const example = choice === 'hold' ? 'Further checks are required before my desk can clear this revision.'
    : 'I reviewed the ' + label(staff.role) + ' evidence and cleared revision ' + file.revision + '.'
  const canSign = choice === 'hold' ? !ownHolds.length : !blocked && (!needsEvidence || (resolved.length === ownHolds.length && !!source))
  if (blocked && ownHolds.length) return <p className="inline-note">Your hold is recorded. {blocked}</p>
  return <form className="action-form" onSubmit={async event => {
    event.preventDefault()
    if (busy || !canSign || reason.trim().length < 10) return
    const body = {
      ...signed(file), disposition: choice, reason: reason.trim(),
      reason_code: choice === 'clear' ? 'CHECKS_COMPLETE' : code,
      expected_review_event_id: current?.event_id ?? null,
      ...(needsEvidence && { resolves_hold_ids: resolved, evidence_ref: source }),
      ...(choice === 'hold' && code === 'DOCUMENT_REQUIRED' && { request_to: 'coverage', required_evidence: 'supplier_invoice' }),
    }
    await submit('/reviews/' + staff.role, body, 'Your desk finding was recorded.')
  }}>
    {blocked && <p className="inline-note">{blocked}</p>}
    <fieldset disabled={busy}><legend>Disposition</legend>
      <div className="options">
        {['clear', 'hold'].map(value => <label key={value}><input type="radio" name="finding" value={value} required
          disabled={value === 'clear' ? !!blocked : ownHolds.length > 0} checked={choice === value} onChange={() => { setChoice(value); setReason('') }} />{value === 'clear' ? 'Clear' : 'Hold'}</label>)}
      </div>
    </fieldset>
    {choice === 'hold' && !ownHolds.length && <label>Reason code<select value={code} onChange={e => setCode(e.target.value)}>
      {['DOCUMENT_REQUIRED', 'MANUAL_REVIEW', 'FACILITY_EXCEPTION'].map(value => <option key={value} value={value}>{label(value)}</option>)}
    </select></label>}
    {choice === 'hold' && !ownHolds.length && code === 'DOCUMENT_REQUIRED' && <p className="inline-note">Coverage will receive a request for the supplier invoice.</p>}
    {needsEvidence && <fieldset><legend>Resolve your open holds</legend>
      {ownHolds.map(hold => <label className="check" key={hold.hold_id}><input type="checkbox" required checked={resolved.includes(hold.hold_id)} onChange={e => setResolved(e.target.checked ? [...resolved, hold.hold_id] : resolved.filter(id => id !== hold.hold_id))} />{label(hold.reason_code)} <code>{hold.hold_id}</code></label>)}
      <label>Reviewed evidence<select required value={source} onChange={e => setSource(e.target.value)}>
        <option value="">Choose a source</option>{references.map(ref => <option key={ref}>{ref}</option>)}
      </select></label>
      {!references.length && <p className="inline-note">Coverage must attach the requested invoice first.</p>}
    </fieldset>}
    <ReasonField label="Reason for this finding" value={reason} change={setReason} example={staff.desk_picker ? example : undefined} busy={busy} />
    <button type="submit" className="primary" disabled={busy || !canSign || reason.trim().length < 10}>{needsEvidence ? 'Release hold and sign' : choice === 'hold' ? 'Sign hold finding' : 'Sign desk finding'}</button>
  </form>
}

export function DecisionForm({ file, staff, busy, submit }: Controls) {
  const overLimit = !file.within_mandate
  const [decision, setDecision] = useState(overLimit ? 'refer' : 'approve')
  const [reason, setReason] = useState('')
  const examples: Record<string, string> = { approve: 'I reviewed all signed findings and approve this revision within my mandate.',
    decline: 'I reviewed the signed findings and decline this request.', refer: 'I refer this request to the higher credit authority for a decision.' }
  return <form className="action-form" onSubmit={async e => {
    e.preventDefault()
    if (busy || reason.trim().length < 10) return
    await submit('/decision', { ...signed(file), decision, reason: reason.trim() }, 'Final decision recorded.')
  }}>
    <p className="muted">{overLimit ? 'The request exceeds your mandate. Refer it to the higher credit authority.' : 'Your approval mandate is ' + money(file.mandate_minor, file.mandate_currency) + '.'}</p>
    <label>Decision<select required value={decision} disabled={busy} onChange={e => { setDecision(e.target.value); setReason('') }}>
      {(overLimit ? ['refer'] : ['approve', 'decline', 'refer']).map(value => <option key={value} value={value}>{label(value)}</option>)}
    </select></label>
    <ReasonField label="Decision reason" value={reason} change={setReason} example={staff.desk_picker ? examples[decision] : undefined} busy={busy} />
    <button type="submit" className="primary" disabled={busy || reason.trim().length < 10}>{decision === 'approve' ? 'Final approve' : decision === 'refer' ? 'Record referral' : 'Record decline'}</button>
  </form>
}

function QuestionForm({ file, staff, busy, submit }: Controls) {
  const [recipient, setRecipient] = useState('')
  const [question, setQuestion] = useState('')
  return <form className="action-form sub-form" onSubmit={async e => {
    e.preventDefault()
    await submit('/requests', { revision: file.revision, to_desk: recipient, question: question.trim() }, 'Question sent to the assigned desk.')
  }}>
    <h3>Ask another desk</h3>
    <label>Recipient<select required value={recipient} onChange={e => setRecipient(e.target.value)}><option value="">Choose a desk</option>
      {roles.filter(role => role !== staff.role).map(role => <option key={role} value={role}>{label(role)}</option>)}
    </select></label>
    <label>Question{staff.role === 'compliance'
      ? <select required value={question} onChange={e => setQuestion(e.target.value)}><option value="">Choose an approved question</option>{complianceQuestions.map(text => <option key={text}>{text}</option>)}</select>
      : <textarea {...reasonProps} value={question} onChange={e => setQuestion(e.target.value)} />}</label>
    <button disabled={busy || !recipient || question.trim().length < 10}>Send question</button>
  </form>
}

function Reply({ file, item, busy, submit, staff }: Controls & { item: DeskRequest }) {
  const [reply, setReply] = useState('')
  return <form className="action-form" onSubmit={async e => {
    e.preventDefault()
    await submit('/requests/' + encodeURIComponent(item.request_id) + '/replies', { revision: file.revision, reply: reply.trim() }, 'Reply sent to the requesting desk.')
  }}>
    <label>Reply to {label(item.from_desk)}{staff.role === 'compliance'
      ? <select required value={reply} onChange={e => setReply(e.target.value)}><option value="">Choose an approved reply</option><option>{complianceReply}</option></select>
      : <textarea {...reasonProps} value={reply} onChange={e => setReply(e.target.value)} />}</label>
    <button disabled={busy || reply.trim().length < 10}>Send reply</button>
  </form>
}

export function InvoiceForm({ file, staff, busy, submit }: Controls) {
  const [request, setRequest] = useState('')
  const [note, setNote] = useState('')
  const requests = file.requests.filter(item => item.to_desk === staff.role && item.blocking && !['resolved','closed'].includes(item.status))
  return <form className="action-form" onSubmit={async e => {
    e.preventDefault()
    await submit('/evidence', {
      expected_revision: file.revision, fixture_document_id: file.invoice_document_id,
      ...(request && { request_id: request }), note: note.trim(),
    }, 'Supplier invoice attached. The amended file requires a new packet and fresh desk signatures.')
  }}>
    <p className="muted">Synthetic document <code>{file.invoice_document_id}</code></p>
    {requests.length > 0 && <label>Related request<select required value={request} onChange={e => setRequest(e.target.value)}>
      <option value="">Choose a request</option>{requests.map(item => <option key={item.request_id} value={item.request_id}>{label(item.from_desk)} · {item.question}</option>)}
    </select></label>}
    <ReasonField label="Evidence note" value={note} change={setNote} busy={busy} example={staff.desk_picker ? 'I attached the supplier invoice for the current amount and currency.' : undefined} />
    <button className="primary" disabled={busy || note.trim().length < 10 || (requests.length > 0 && !request)}>Attach invoice and revise file</button>
  </form>
}

export function Inbox(props: Controls) {
  const { file, staff } = props
  return <section className="card"><h2>Desk correspondence</h2>
    {!file.requests.length && <p className="muted">No correspondence visible to your desk.</p>}
    {file.requests.map(item => <article className="request" key={item.request_id}>
      <div className="flex"><strong>{label(item.from_desk)} → {label(item.to_desk)}</strong><span className="pill">{label(item.status)}</span></div>
      <p>{item.question}</p>{item.evidence_ref && <code>{item.evidence_ref}</code>}
      {item.reply && <p className="reply"><strong>Reply</strong> · {item.reply}</p>}
      {file.permitted_actions.includes('reply') && item.to_desk === staff.role && item.status === 'open' && <Reply {...props} item={item} />}
    </article>)}
    {file.permitted_actions.includes('request') && <details className="ask"><summary>New question</summary><QuestionForm {...props} /></details>}
  </section>
}

export function ActionPanel(props: Controls) {
  const { file, busy, submit } = props
  const mode = file.configured_mode
  const allowed = (value: string) => file.permitted_actions.includes(value)
  return <>
    {allowed('run') && <section className="card action-form">
      <h2>Prepare review packets</h2>
      <p className="muted">{mode === 'live' ? 'Live · BRANE' : 'Fixture · synthetic analysis'}</p>
      {!file.analysis_available && <p className="inline-note">The configured analysis service is unavailable.</p>}
      <button className="primary" disabled={busy} onClick={() => submit('/runs', { revision: file.revision, mode }, 'Run recorded. Check the current analysis result.')}>Run analysis</button>
    </section>}
    {allowed('attach_invoice') && !file.human_approval?.evidence_action && <section className="card"><h2>Attach supplier invoice</h2><InvoiceForm {...props} /></section>}
    {allowed('issue') && !file.receipt && <section className="card action-form">
      <h2>Operations instruction</h2>
      <p>Record simulated issuance of {money(file.amount_minor, file.currency)} against approved revision {file.revision}.</p>
      <button className="primary" disabled={busy} onClick={() => submit('/issuance', signed(file), 'Simulated issuance recorded.')}>Simulate issuance</button>
    </section>}
  </>
}
