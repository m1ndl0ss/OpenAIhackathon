import { useState, type ReactNode } from 'react'
import { ClipboardTextIcon, ClockCounterClockwiseIcon, FingerprintSimpleIcon, FilesIcon } from '@phosphor-icons/react'
import { deskName, label, type DepartmentFile, type Staff, type Submit } from './api'
import { DeskIcon } from './Brand'
import PacketList from './PacketList'

function DepartmentActions({ file, staff, busy, submit }: { file: DepartmentFile; staff: Staff; busy: boolean; submit: Submit }) {
  const [reason, setReason] = useState('')
  const meta = file.department_case
  const allowed = file.permitted_actions
  const signedActions = allowed.filter(k => ['sign', 'hold', 'complete', 'refer'].includes(k))
  const names: Record<string, string> = { sign: 'Sign desk review', hold: 'Place on hold', complete: 'Approve request', refer: 'Refer for further review' }
  async function act(action: string) {
    const body = { action, revision: file.revision, ...(action === 'verify' ? {} : {
      packet_hash: file.packet_hash, reason: reason.trim(), expected_event_id: file.reviews.find(r => r.desk === staff.role)?.event_id ?? null,
    }) }
    const message = { verify: 'Supporting record verified. A new revision is ready for analysis.', sign: 'Desk review signed.',
      hold: 'Desk hold recorded.', complete: 'Department outcome recorded.', refer: 'Department referral recorded.' }[action]
    if (await submit('/workflow-action', body, message || 'Action recorded.')) setReason('')
  }
  return <section className="card action-form" id="approval-action" tabIndex={-1}>
    <h2>{allowed.includes('complete') ? 'Your final decision' : signedActions.length ? 'Your desk review' : 'Your desk action'}</h2>
    <p className="muted">{staff.name} · {deskName(file, staff.role)} · Revision {file.revision}</p>
    {allowed.includes('complete') && <p>Approval records the following outcome. <strong>{meta.outcome}</strong>.</p>}
    {allowed.includes('verify') && <div className="action-form"><p>Verify the registered synthetic record, <strong>{meta.source}</strong>, to attach it to a new revision.</p>
      <button disabled={busy} onClick={() => act('verify')}><FilesIcon size={16} />Verify supporting record</button></div>}
    {allowed.includes('run') && <button className="primary" disabled={busy || file.last_run?.status === 'pending'} onClick={() => submit('/runs', {revision:file.revision, mode:file.configured_mode}, 'Analysis run submitted.')}>Run analysis</button>}
    {!!signedActions.length && <><label>Reason for this action<textarea minLength={10} maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label>
      {signedActions.map((k,i) => <button className={i === 0 ? 'primary' : ''} key={k} disabled={busy || reason.trim().length < 10} onClick={() => act(k)}>{names[k]}</button>)}</>}
    {!allowed.length && <p>{file.next_action}</p>}
  </section>
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
    {file.last_run && file.last_run.status.startsWith('analysis_') && <p className="error" role="alert">{label(file.last_run.status)}. The file is still open for review.</p>}
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
    </div><aside className="stack"><DepartmentActions key={file.case_id + '-' + file.revision} {...{file,staff,busy,submit}} />
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
