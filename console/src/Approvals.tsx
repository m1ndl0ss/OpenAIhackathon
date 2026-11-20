import { useEffect, useRef } from 'react'
import { ArrowRightIcon, CheckCircleIcon, FileTextIcon, LockSimpleIcon, PaperPlaneTiltIcon, SignatureIcon, TrayIcon, UserCircleIcon, XIcon } from '@phosphor-icons/react'
import { DecisionForm, InvoiceForm, ReviewForm } from './Actions'
import { DepartmentSignature, VerifyRecord } from './DepartmentWorkspace'
import PacketList from './PacketList'
import { caseLabel, deskName, type ApprovalRecipient, type Staff, type StaffContact, type StaffFile, type Submit, type Summary } from './api'
import './approvals.css'

export type ApprovalTask = 'review' | 'decision' | 'evidence'
export type ApprovalEditor = { caseId: string; revision: number; task: ApprovalTask }

const names = new Intl.ListFormat('en', { style: 'long', type: 'conjunction' })
const statusText: Record<ApprovalRecipient['status'], string> = {
  not_sent: 'Ready to send', awaiting: 'In approval inbox', signed: 'Signed', hold: 'On hold',
  waiting: 'After desk sign-off', approve: 'Approved', decline: 'Declined', refer: 'Referred',
}
type Controls = { file: StaffFile; staff: Staff; busy: boolean; submit: Submit }
type Open = (person: StaffContact, task: ApprovalTask) => void

function Recipient({ person, file, staff, busy, open, editing, final = false }: Omit<Controls, 'submit'> & {
  person: ApprovalRecipient; open: Open; editing: boolean; final?: boolean
}) {
  const mine = staff.id === person.id
  const canOpenDesk = mine || staff.desk_picker
  const current = file.mode === file.configured_mode && !file.decision
  const outstanding = person.status === 'awaiting' || person.status === 'hold'
  const canAmend = !final && mine && person.status === 'signed'
  const active = current && !!person.sent_at && (outstanding || canAmend)
  const referralOnly = !file.department_case && !file.within_mandate
  const Icon = person.status === 'signed' || person.status === 'approve' ? CheckCircleIcon : final ? SignatureIcon : UserCircleIcon
  let action = mine ? 'Review finding' : 'Review as ' + person.name
  if (canAmend) action = 'Amend finding'
  if (final) action = referralOnly ? 'Refer case' : 'Final approve'
  return <li className={'approval-person ' + (final ? 'final-person' : '')}>
    <span className="person-icon"><Icon size={21} weight="duotone" /></span>
    <div className="person-name"><strong>{person.name}</strong><small>{deskName(file, person.role)}</small></div>
    <span className={'person-status ' + person.status}>{statusText[person.status]}</span>
    {canOpenDesk && current && (active || final) && !editing &&
      <button type="button" className={final && active ? 'primary' : ''} disabled={busy || !active} onClick={() => open(person, final ? 'decision' : 'review')}>
        {final && !active ? <LockSimpleIcon size={13} /> : <SignatureIcon size={14} />}{action}</button>}
  </li>
}

function SigningForm({ file, staff, busy, submit, task, close }: Controls & { task: ApprovalTask; close: () => void }) {
  const anchor = useRef<HTMLDivElement>(null)
  useEffect(() => {
    anchor.current?.focus({ preventScroll: true })
    anchor.current?.scrollIntoView({ block: 'nearest' })
  }, [])
  const save: Submit = async (...args) => {
    const ok = await submit(...args)
    if (ok) close()
    return ok
  }
  const controls = { staff, busy, submit: save }
  let form
  if (task === 'evidence') form = file.department_case ? <VerifyRecord file={file} {...controls} /> : <InvoiceForm file={file} {...controls} />
  else if (file.department_case) form = <DepartmentSignature file={file} {...controls} />
  else form = task === 'decision' ? <DecisionForm file={file} {...controls} /> : <ReviewForm file={file} {...controls} />
  const title = task === 'review' ? 'Desk finding' : task === 'decision' ? 'Final decision' : file.department_case ? 'Verify supporting record' : 'Attach supplier invoice'
  return <div className="sign-editor" ref={anchor} tabIndex={-1} role="region" aria-label={title}>
    <div className="sign-editor-heading"><div><h3>{title}</h3><p><strong>{staff.name}</strong> · {deskName(file, staff.role)} · Revision {file.revision}</p></div>
      <button type="button" disabled={busy} onClick={close} aria-label="Close action"><XIcon size={17} /></button></div>
    {task !== 'evidence' && <details className="sign-packets"><summary>Inspect the current evidence</summary>
      <PacketList packets={file.packets} sources={file.sources} currency={file.currency || ''} mode={file.department_case?.local_only ? 'bank_local' : file.mode} /></details>}
    {form}
  </div>
}

export function ApprovalPanel({ file, staff, busy, submit, open, task, close }: Controls & {
  open: Open; task: ApprovalTask | null; close: () => void
}) {
  const panel = useRef<HTMLElement>(null)
  const plan = file.human_approval
  if (!plan || plan.stage === 'preparing' || plan.stage === 'other_mode') return null
  const reviewers = names.format(plan.reviewers.map(person => person.name))
  const waiting = plan.reviewers.filter(p => p.status === 'awaiting' || p.status === 'hold')
  const signed = plan.reviewers.filter(p => p.status === 'signed').length
  const final = plan.final.name
  const allowed = file.permitted_actions
  const myReview = plan.reviewers.find(p => p.id === staff.id)
  const canEdit = !file.decision && (
    (task === 'decision' && plan.final.id === staff.id && plan.stage === 'decision' && (allowed.includes('decide') || allowed.includes('complete'))) ||
    (task === 'review' && !!myReview?.sent_at && (myReview.status === 'hold' || allowed.some(action => ['review', 'sign', 'hold'].includes(action)))) ||
    (task === 'evidence' && plan.owner.id === staff.id && !!plan.evidence_action && allowed.includes(plan.evidence_action)))
  let message: string
  if (plan.stage === 'closed') message = 'Decision recorded for ' + caseLabel(file.case_id) + ' · Revision ' + file.revision + '.'
  else if (plan.stage === 'decision') message = 'All desk findings are signed. ' + final + ' can now record the final decision.'
  else if (plan.stage === 'review') message = waiting.length
    ? 'Waiting for ' + names.format(waiting.map(p => p.name)) + ' to sign. ' + final + ' receives the request when all checks clear.'
    : 'The findings are signed. The remaining case checks must clear before final approval.'
  else message = 'Send this packet to ' + reviewers + '. After desk sign-off and required checks, ' + final + ' receives it for final approval.'
  const heading = plan.stage === 'closed' ? statusText[plan.final.status] + ' by ' + final : 'Human approval'
  const evidenceLabel = plan.evidence_action === 'attach_invoice' ? 'Attach supplier invoice' : 'Verify supporting record'
  function finish() {
    close()
    panel.current?.focus({ preventScroll: true })
    panel.current?.scrollIntoView({ block: 'nearest' })
  }
  return <section ref={panel} tabIndex={-1} className={'approval-panel ' + (plan.stage === 'closed' ? 'approval-' + plan.final.status : '')} aria-label="Human approval">
    <div className="approval-heading"><div><h2>{plan.final.status === 'approve' && <CheckCircleIcon size={23} weight="duotone" />}{heading}</h2><p role="status">{message}</p></div>
      {plan.can_send && <button className="primary" type="button" disabled={busy} onClick={() => submit('/desk-review',
        { revision: file.revision, packet_hash: file.packet_hash }, 'Sent for desk review to ' + reviewers + '.')}>
        <PaperPlaneTiltIcon size={16} />Send for desk review</button>}</div>
    <div className="approval-columns"><div><h3>Desk findings <span className="sign-count">{signed} of {plan.reviewers.length} signed</span></h3>
      <ul>{plan.reviewers.map(person => <Recipient key={person.id} {...{person, file, staff, busy, open}} editing={canEdit && task === 'review' && staff.id === person.id} />)}</ul></div>
      <div><h3>Final approval</h3><ul><Recipient person={plan.final} {...{file, staff, busy, open}} final editing={canEdit && task === 'decision'} /></ul></div></div>
    {plan.evidence_action && <div className="approval-evidence"><FileTextIcon size={18} /><p>{plan.owner.name} must {plan.evidence_action === 'attach_invoice'
      ? 'attach the supplier invoice' : 'verify the supporting record'} before this revision can be approved.</p>
      {(staff.id === plan.owner.id || staff.desk_picker) && !(canEdit && task === 'evidence') &&
        <button disabled={busy} type="button" onClick={() => open(plan.owner, 'evidence')}>{evidenceLabel}<ArrowRightIcon size={13} /></button>}</div>}
    {task && canEdit && <SigningForm key={[file.case_id, file.revision, file.packet_hash, task, file.reviews.find(r => r.desk === staff.role)?.event_id].join('/')}
      {...{file, staff, busy, submit, task}} close={finish} />}
  </section>
}

export function ApprovalInbox({ staff, items, open, busy }: { staff: Staff; items: Summary[]; open: (id: string) => void; busy: boolean }) {
  return <section className="approval-inbox"><div className="tracker-edition"><TrayIcon size={17} />{staff.name}</div><h1>My approvals</h1>
    <p>{items.length ? 'These packets are waiting for your signature or final decision.' : 'You have no requests waiting for your approval.'}</p>
    {items.length > 0 && <ul>{items.map(item => <li key={item.case_id}><button disabled={busy} onClick={() => open(item.case_id)}>
      <span className="person-icon"><SignatureIcon size={22} /></span><span><strong>{item.case_title}</strong><small>{caseLabel(item.case_id)} · {item.department} · Revision {item.revision}</small></span>
      <b>{item.my_approval === 'decision' ? 'Final decision' : 'Desk review'}</b><ArrowRightIcon size={16} /></button></li>)}</ul>}
  </section>
}
