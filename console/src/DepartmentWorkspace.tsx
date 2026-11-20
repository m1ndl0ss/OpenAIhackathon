import { useState, type ReactNode } from 'react'
import { ClipboardTextIcon, ClockCounterClockwiseIcon, FingerprintSimpleIcon, FilesIcon } from '@phosphor-icons/react'
import { deskName, label, type DepartmentFile, type Staff, type Submit } from './api'
import { DeskIcon } from './Brand'
import PacketList from './PacketList'
import { ReasonField } from './Actions'

type Controls = { file: DepartmentFile; staff: Staff; busy: boolean; submit: Submit }

export function DepartmentSignature({ file, staff, busy, submit }: Controls) {
  const [reason, setReason] = useState('')
  const meta = file.department_case
  const final = staff.role === meta.approver
  const ownHold = file.holds.some(h => h.desk === staff.role)
  const actions = file.permitted_actions.filter(k => ['sign', 'hold', 'complete', 'refer'].includes(k))
  const names: Record<string, string> = { sign: ownHold ? 'Release hold and sign' : 'Sign desk finding', hold: 'Place on hold', complete: 'Final approve', refer: 'Refer for further review' }
  async function act(action: string) {
    const body = { action, revision: file.revision,
      packet_hash: file.packet_hash, reason: reason.trim(), expected_event_id: file.reviews.find(r => r.desk === staff.role)?.event_id ?? null,
    }
    const message = { sign: 'Desk finding signed.', hold: 'Desk hold recorded.', complete: 'Final approval recorded.', refer: 'Department referral recorded.' }[action]
    if (await submit('/workflow-action', body, message || 'Action recorded.')) setReason('')
  }
  const example = final ? 'I reviewed the signed desk findings and the supporting record for my final decision.'
    : 'I reviewed the available evidence and the ' + deskName(file, staff.role) + ' findings for this revision.'
  return <div className="action-form">
    {final && <p>Approval records the following outcome. <strong>{meta.outcome}</strong>.</p>}
    {!meta.evidence_verified && <p className="inline-note">The analyst must verify the supporting record before this desk can sign a clearance.</p>}
    {actions.length > 0 && <><ReasonField label={final ? 'Decision reason' : 'Reason for this finding'} value={reason} change={setReason}
      busy={busy} example={staff.desk_picker ? example : undefined} />
      <div className="sign-actions">{actions.map((k,i) => <button type="button" className={i === 0 ? 'primary' : ''} key={k}
        disabled={busy || reason.trim().length < 10} onClick={() => act(k)}>{names[k]}</button>)}</div></>}
  </div>
}

export function VerifyRecord({ file, busy, submit }: Controls) {
  return <div className="action-form"><p>Verify the registered synthetic record, <strong>{file.department_case.source}</strong>, to attach it to a new revision.</p>
    <button disabled={busy} onClick={() => submit('/workflow-action', {action:'verify', revision:file.revision}, 'Supporting record verified. Run analysis on the new revision.')}><FilesIcon size={16} />Verify supporting record</button></div>
}

export default function DepartmentWorkspace({file, staff, busy, submit, history}: {
  file: DepartmentFile; staff: Staff; busy: boolean; submit: Submit; history: ReactNode
}) {
  const [tab,setTab] = useState<'Overview'|'Audit trail'>('Overview')
  const meta = file.department_case
  const route = meta.local_only ? 'Bank only · zero model calls' : file.configured_mode === 'live' ? 'Live · BRANE' : 'Fixture · synthetic'
  const lastRun = file.last_run
  return <>
    <div className="case-heading"><div><div className="eyebrow">{file.department} · {file.case_id}</div><h1>{file.case_title}</h1>
      <p className="subhead">{file.workflow_title} <span>·</span> Revision {file.revision}</p></div><span className={'pill ' + file.status}>{label(file.status)}</span></div>
    <div className="case-stats">{[['Department',file.department],['Drafting route',route],['Supporting record',meta.evidence_verified ? 'Verified' : 'Awaiting verification'],
      ['Desk signatures',file.reviews.filter(r => r.disposition === 'clear').length + ' of ' + meta.reviewers.length]].map(([k,v])=><div key={k}><span>{k}</span><strong>{v}</strong></div>)}</div>
    <section className={'next-step ' + (file.holds.length ? 'held' : '')}><div className="eyebrow">Next handoff</div><p>{file.next_action}</p></section>
    <nav className="view-tabs" aria-label="Case sections">{(['Overview','Audit trail'] as const).map(t =>
      <button className={tab === t ? 'active' : ''} aria-current={tab === t ? 'page' : undefined} key={t} onClick={()=>setTab(t)}>
        {t === 'Overview' ? <ClipboardTextIcon size={16} /> : <ClockCounterClockwiseIcon size={16} />}{t}</button>)}</nav>
    {tab === 'Audit trail' ? history : <div className="case-grid"><div className="stack">
      <section className="card"><div className="card-head"><h2>Human review</h2><span className="quiet">Rev. {file.revision}</span></div>
        {[...meta.reviewers,meta.approver].map(role => {
          const finding=file.reviews.find(r => r.desk === role)
          const status=role === meta.approver ? (file.decision ? file.status : 'pending') : finding?.disposition || 'pending'
          return <div className="desk-row" key={role}><span className="finding-icon"><DeskIcon role={role} size={19} /></span>
            <div><strong>{deskName(file,role)}</strong><small>{role === meta.approver ? 'Final human disposition' : 'Evidence and draft review'}</small>{finding?.reason && <p>{finding.reason}</p>}</div>
            <span className={'pill ' + status}>{label(status)}</span></div>
        })}</section>
      <PacketList packets={file.packets} sources={file.sources} currency="" mode={meta.local_only ? 'bank_local' : file.mode} />
      {file.receipt && <section className="card receipt"><h2>Recorded outcome</h2><p>{file.decision?.decision === 'refer' ? 'Referred for further review' : meta.outcome}</p>
        <p><code>{file.receipt.receipt_id}</code> · Rev. {file.receipt.revision}</p></section>}
    </div><aside className="stack">
      {(file.permitted_actions.includes('run') || (file.permitted_actions.includes('verify') && !file.human_approval?.evidence_action)) && <section className="card action-form"><h2>Prepare this revision</h2>
        {file.permitted_actions.includes('verify') && !file.human_approval?.evidence_action && <VerifyRecord {...{file,staff,busy,submit}} />}
        {file.permitted_actions.includes('run') && <button className="primary" disabled={busy || file.last_run?.status === 'pending'} onClick={() => submit('/runs', {revision:file.revision, mode:file.configured_mode}, 'Analysis run submitted.')}>Run analysis</button>}
      </section>}
      <section className="card"><div className="card-head"><h2>Case evidence</h2><FingerprintSimpleIcon size={19} /></div>
        {file.sources.map(s => <details key={s.ref} className="packet"><summary>{s.label}</summary><p>{s.detail}</p><code>{s.ref}</code></details>)}</section>
      {lastRun?.analysis && <section className="card context"><h2>Last drafting run</h2><dl>
        <dt>Result</dt><dd>{label(lastRun.status)}</dd>
        <dt>{lastRun.mode === 'fixture' ? 'Simulated model calls' : 'Model calls'}</dt><dd>{lastRun.analysis.model_calls}</dd>
        <dt>Local tool reads</dt><dd>{lastRun.analysis.tool_reads}</dd>
        <dt>Observed routes</dt><dd>{[...new Set(lastRun.analysis.observations.map(item => label(item.route)))].join(', ') || 'None recorded'}</dd>
      </dl></section>}
    </aside></div>}
  </>
}
