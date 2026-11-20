import { useState } from 'react'
import { label, money, roles, type CaseFile, type DeskRequest, type Staff, type Submit } from './api'

type Controls = { file: CaseFile; staff: Staff; busy: boolean; submit: Submit }
const reasonProps = { required: true, minLength: 10, maxLength: 2000, rows: 3 }
const complianceQuestions = [
  'Please supply the supplier invoice for this instrument.',
  'Please confirm the current case evidence for Compliance review.',
]
const complianceReply = 'Compliance has reviewed the request. See the current desk disposition.'
const signed = (file: CaseFile) => ({ revision: file.revision, packet_hash: file.packet_hash })

function ReviewForm({ file, staff, busy, submit }: Controls) {
  const [choice, setChoice] = useState('')
  const [reason, setReason] = useState('')
  const [code, setCode] = useState('DOCUMENT_REQUIRED')
  const [resolved, setResolved] = useState<string[]>([])
  const [source, setSource] = useState('')
  const current = file.reviews.find(item => item.desk === staff.role)
  const ownHolds = file.holds.filter(hold => hold.desk === staff.role)
  const needsEvidence = choice === 'clear' && ownHolds.length > 0
  const requiresInvoice = ownHolds.some(hold => hold.reason_code === 'DOCUMENT_REQUIRED')
  const references = requiresInvoice ? (file.invoice_ref ? [file.invoice_ref] : []) : file.sources.map(item => item.ref)

  return <form id="approval-action" tabIndex={-1} className="action-form" onSubmit={async event => {
    event.preventDefault()
    if (!choice) return
    const body = {
      ...signed(file), disposition: choice, reason: reason.trim(),
      reason_code: choice === 'clear' ? 'CHECKS_COMPLETE' : code,
      expected_review_event_id: current?.event_id ?? null,
      ...(needsEvidence && { resolves_hold_ids: resolved, evidence_ref: source }),
      ...(choice === 'hold' && code === 'DOCUMENT_REQUIRED' && { request_to: 'coverage', required_evidence: 'supplier_invoice' }),
    }
    await submit('/reviews/' + staff.role, body, 'Your desk finding was recorded.')
  }}>
    <h2>Your desk finding</h2>
    <p className="muted">{staff.name} · {label(staff.role)} · Revision {file.revision}</p>
    <fieldset disabled={busy}><legend>Disposition</legend>
      <div className="options">
        {['clear', 'hold'].map(value => <label key={value}><input type="radio" name="finding" value={value} required checked={choice === value} onChange={() => setChoice(value)} />{value === 'clear' ? 'Clear' : 'Hold'}</label>)}
      </div>
    </fieldset>
    {choice === 'hold' && <label>Reason code<select value={code} onChange={e => setCode(e.target.value)}>
      {['DOCUMENT_REQUIRED', 'MANUAL_REVIEW', 'FACILITY_EXCEPTION'].map(value => <option key={value} value={value}>{label(value)}</option>)}
    </select></label>}
    {choice === 'hold' && code === 'DOCUMENT_REQUIRED' && <p className="inline-note">Coverage will receive a request for the supplier invoice.</p>}
    {needsEvidence && <fieldset><legend>Resolve your open holds</legend>
      {ownHolds.map(hold => <label className="check" key={hold.hold_id}><input type="checkbox" required checked={resolved.includes(hold.hold_id)} onChange={e => setResolved(e.target.checked ? [...resolved, hold.hold_id] : resolved.filter(id => id !== hold.hold_id))} />{label(hold.reason_code)} <code>{hold.hold_id}</code></label>)}
      <label>Reviewed evidence<select required value={source} onChange={e => setSource(e.target.value)}>
        <option value="">Choose a source</option>{references.map(ref => <option key={ref}>{ref}</option>)}
      </select></label>
      {!references.length && <p className="inline-note">Coverage must attach the requested invoice first.</p>}
    </fieldset>}
    <label>Reason for this finding<textarea {...reasonProps} value={reason} onChange={e => setReason(e.target.value)} /></label>
    <button className="primary" disabled={busy || !choice || reason.trim().length < 10 || (needsEvidence && (resolved.length !== ownHolds.length || !source))}>Sign desk finding</button>
  </form>
}

function DecisionForm({ file, staff, busy, submit }: Controls) {
  const [decision, setDecision] = useState('')
  const [reason, setReason] = useState('')
  const overLimit = !file.within_mandate
  return <form id="approval-action" tabIndex={-1} className="action-form" onSubmit={async e => {
    e.preventDefault()
    await submit('/decision', { ...signed(file), decision, reason: reason.trim() }, 'Final decision recorded.')
  }}>
    <h2>Final decision</h2>
    <p className="muted">{staff.name} · Mandate {money(file.mandate_minor, file.mandate_currency)}</p>
    <label>Decision<select required value={decision} onChange={e => setDecision(e.target.value)}>
      <option value="">Choose a decision</option>
      {(overLimit ? ['refer'] : ['approve', 'decline', 'refer']).map(value => <option key={value} value={value}>{label(value)}</option>)}
    </select></label>
    <label>Decision reason<textarea {...reasonProps} value={reason} onChange={e => setReason(e.target.value)} /></label>
    <button className="primary" disabled={busy || !decision || reason.trim().length < 10}>Record final decision</button>
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

function InvoiceForm({ file, staff, busy, submit }: Controls) {
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
    <h2>Attach supplier invoice</h2>
    <p className="muted">Synthetic document <code>{file.invoice_document_id}</code></p>
    {requests.length > 0 && <label>Related request<select required value={request} onChange={e => setRequest(e.target.value)}>
      <option value="">Choose a request</option>{requests.map(item => <option key={item.request_id} value={item.request_id}>{label(item.from_desk)} · {item.question}</option>)}
    </select></label>}
    <label>Evidence note<textarea {...reasonProps} value={note} onChange={e => setNote(e.target.value)} /></label>
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
    {allowed('review') && <section className="card"><ReviewForm {...props} /></section>}
    {allowed('attach_invoice') && <section className="card"><InvoiceForm {...props} /></section>}
    {allowed('decide') && <section className="card"><DecisionForm {...props} /></section>}
    {allowed('issue') && !file.receipt && <section className="card action-form">
      <h2>Operations instruction</h2>
      <p>Record simulated issuance of {money(file.amount_minor, file.currency)} against approved revision {file.revision}.</p>
      <button className="primary" disabled={busy} onClick={() => submit('/issuance', signed(file), 'Simulated issuance recorded.')}>Simulate issuance</button>
    </section>}
  </>
}
