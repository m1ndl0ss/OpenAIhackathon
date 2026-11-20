import { ArrowRightIcon, ArrowSquareOutIcon, CheckCircleIcon, PaperPlaneTiltIcon, SignatureIcon, TrayIcon, UserCircleIcon } from '@phosphor-icons/react'
import { caseLabel, deskName, type ApprovalRecipient, type Staff, type StaffFile, type Submit, type Summary } from './api'
import './approvals.css'

const names = new Intl.ListFormat('en', { style: 'long', type: 'conjunction' })
const statusText: Record<ApprovalRecipient['status'], string> = {
  not_sent: 'Ready to send', awaiting: 'In approval inbox', signed: 'Signed', hold: 'On hold',
  waiting: 'After desk sign-off', approve: 'Approved', decline: 'Declined', refer: 'Referred',
}

function Recipient({ person, file, staff, busy, open, final = false }: {
  person: ApprovalRecipient; file: StaffFile; staff: Staff; busy: boolean; final?: boolean; open: (person: ApprovalRecipient) => void
}) {
  const isMe = staff.id === person.id
  const active = !!person.sent_at && (person.status === 'awaiting' || person.status === 'hold') && file.mode === file.configured_mode && !file.decision
  const Icon = person.status === 'signed' || person.status === 'approve' ? CheckCircleIcon : final ? SignatureIcon : UserCircleIcon
  return <li className={'approval-person ' + (final ? 'final-person' : '')}>
    <span className="person-icon"><Icon size={21} weight="duotone" /></span>
    <div className="person-name"><strong>{person.name}</strong><small>{deskName(file, person.role)}</small></div>
    <span className={'person-status ' + person.status}>{statusText[person.status]}</span>
    {active && (isMe || staff.desk_picker) && <button type="button" disabled={busy} onClick={() => open(person)}
      aria-label={isMe ? (final ? 'Record your final decision' : 'Review your assigned request') : 'Open ' + person.name + '’s demo desk'}>
      {isMe ? (final ? 'Record decision' : 'Review request') : 'Open demo desk'}{isMe ? <ArrowRightIcon size={13} /> : <ArrowSquareOutIcon size={13} />}</button>}
  </li>
}

export function ApprovalPanel({ file, staff, busy, submit, open }: {
  file: StaffFile; staff: Staff; busy: boolean; submit: Submit; open: (person: ApprovalRecipient) => void
}) {
  const plan = file.human_approval
  if (!plan || plan.stage === 'preparing' || plan.stage === 'other_mode') return null
  const reviewers = names.format(plan.reviewers.map(person => person.name))
  const waiting = plan.reviewers.filter(p => p.status === 'awaiting' || p.status === 'hold')
  const final = plan.final.name
  let message: string
  if (plan.stage === 'closed') message = final + ' recorded the final decision.'
  else if (plan.stage === 'decision') message = 'The desk reviews are signed. The request is in ' + final + '’s approval inbox.'
  else if (plan.stage === 'review') message = waiting.length
    ? 'Waiting for ' + names.format(waiting.map(p => p.name)) + ' to sign. They can open this request in My approvals.'
    : 'The desk reviews are signed. Outstanding case checks must clear before final approval.'
  else message = 'Send this packet to ' + reviewers + '. After desk sign-off and required checks, ' + final + ' receives it for final approval.'
  return <section className="approval-panel" aria-label="Human approval">
    <div className="approval-heading"><div><h2>Human approval</h2><p role="status">{message}</p></div>
      {plan.can_send && <button className="primary" type="button" disabled={busy} onClick={() => submit('/desk-review',
        { revision: file.revision, packet_hash: file.packet_hash }, 'Sent for desk review to ' + reviewers + '.')}>
        <PaperPlaneTiltIcon size={16} />Send for desk review</button>}</div>
    <div className="approval-columns"><div><h3>Desk review</h3><ul>{plan.reviewers.map(person => <Recipient key={person.id} {...{person, file, staff, busy, open}} />)}</ul></div>
      <div><h3>Final approval</h3><ul><Recipient person={plan.final} {...{file, staff, busy, open}} final /></ul></div></div>
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
