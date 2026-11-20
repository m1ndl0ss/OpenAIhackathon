import SignIn, { type PreferredDesk } from './SignIn'
import { Brand, DeskIcon } from './Brand'
import { Fragment, useCallback, useEffect, useRef, useState, type MutableRefObject, type ReactNode } from 'react'
import { ActionPanel, Inbox } from './Actions'
import { ApprovalInbox, ApprovalPanel, type ApprovalEditor, type ApprovalTask } from './Approvals'
import AgentReply from './AgentReply'
import PacketList from './PacketList'
import DepartmentWorkspace from './DepartmentWorkspace'
import RequestDashboard from './RequestDashboard'
import RequestComposer, { SubmittedDetails } from './RequestComposer'
import {
  ArrowsClockwiseIcon, ArrowsLeftRightIcon, ChatCircleTextIcon, CirclesFourIcon,
  ClockCounterClockwiseIcon, FilePlusIcon, FolderOpenIcon, ListBulletsIcon, SignOutIcon, TrayIcon,
} from '@phosphor-icons/react'
import { bank, BankError, caseLabel, deskName, desks, label, money, textError, type AuditEvent, type CaseFile, type Staff, type StaffContact, type StaffFile, type StaffSession, type Submit, type Summary } from './api'

const sessionKey = 'clearance.staff-token'
const selectedKey = 'clearance.selected-case'

function tabValue(key: string, next?: string | null): string | null {
  try {
    if (next === null) sessionStorage.removeItem(key)
    else if (next !== undefined) sessionStorage.setItem(key, next)
    return sessionStorage.getItem(key)
  } catch { return null }
}

function Badge({ value }: { value: string }) {
  return <span className={'pill ' + value}>{label(value)}</span>
}
function fmtDate(value: string | undefined, time = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', dateStyle: 'medium', ...(time && { timeStyle: 'short' }) }).format(date) + (time ? ' UTC' : '')
}
function Notice({ danger, children }: { danger?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { if (danger) ref.current?.focus() }, [danger, children])
  return <div tabIndex={-1} ref={ref} role={danger ? 'alert' : 'status'} className={'notice ' + (danger ? 'danger' : '')}>{children}</div>
}

function History({ audit, file }: { audit: AuditEvent[]; file: StaffFile }) {
  return <section className="card"><h2>Case history</h2>
      {!audit.length && <p className="muted">No visible activity.</p>}
      <ol className="timeline">{audit.map(event => <li key={event.event_id}><div><strong>{label(event.action)}</strong><span>{fmtDate(event.timestamp, true)}</span></div>
        <p>{event.actor_id} · {deskName(file, event.desk)} · Rev. {event.revision}</p>
        {typeof event.detail === 'string' && event.detail && <p>{event.detail}</p>}
        {event.detail && typeof event.detail === 'object' ? <dl>{Object.entries(event.detail).filter(([,v]) => ['string','number','boolean'].includes(typeof v)).map(([k,v]) => <div key={k}><dt>{label(k)}</dt><dd>{String(v)}</dd></div>)}</dl> : null}
      </li>)}</ol>
    </section>
}

function CaseContents({ file, audit, staff, submit, busy }: { file: CaseFile; audit: AuditEvent[]; staff: Staff; submit: Submit; busy: boolean }) {
  const [tab, setTab] = useState('Overview')
  const clearCount = file.reviews.filter(r => r.disposition === 'clear').length
  const controls = { file, staff, submit, busy }
  const receipt = file.receipt
  const mode = file.last_run?.mode || file.mode
  const verifiedPolicy = file.last_run?.analysis?.observations.find(item => item.policy_hash)?.policy_hash
  return <>
    <div className="case-heading"><div><div className="eyebrow">Documentary credit · {file.case_id}</div><h1>Import letter of credit</h1><p className="subhead">Applicant <strong>{file.customer_ref}</strong> <span>·</span> Revision {file.revision}</p></div><Badge value={file.status} /></div>
    <div className="case-stats">
      {[['Requested amount', money(file.amount_minor, file.currency)], ['Facility', file.facility_ref], ['Instrument expiry', fmtDate(file.expiry)], ['Desk clearances', clearCount + ' of 3']].map(([name, value]) => <div key={name}><span>{name}</span><strong>{value}</strong></div>)}
    </div>
    <section className={'next-step ' + (file.holds.length ? 'held' : '')}>
      <div className="eyebrow">{file.holds.length ? 'Issuance blocked' : 'Case status'}</div>
      {file.holds.length > 0 && <strong>{file.holds.map(h => label(h.desk) + ' · ' + label(h.reason_code)).join(' / ')}</strong>}
      <p>{file.next_action}</p>
    </section>
    {file.revision > 1 && <div className="revision-note">Revised file · Only signatures on revision {file.revision} count toward approval.{file.invoice_ref && <> Invoice <code>{file.invoice_ref}</code> is on file.</>}</div>}
    <nav className="view-tabs" aria-label="Case sections">{[{ title: 'Overview', Icon: ListBulletsIcon }, { title: 'Desk messages', Icon: ChatCircleTextIcon }, { title: 'Audit trail', Icon: ClockCounterClockwiseIcon }].map(({ title, Icon }) => <button key={title} aria-current={title === tab ? 'page' : undefined} className={tab === title ? 'active' : ''} onClick={() => setTab(title)}><Icon size={16} />{title}</button>)}</nav>
    {tab === 'Overview' && <div className="case-grid">
      <div className="stack">
        <section className="card"><div className="card-head"><h2>Department sign-offs</h2><span className="quiet">Rev. {file.revision}</span></div>
          {desks.map(desk => {
            const review = file.reviews.find(r => r.desk === desk)
            const hold = file.holds.find(h => h.desk === desk)
            return <div key={desk} className="desk-row"><span className="finding-icon"><DeskIcon role={desk} size={20} /></span><div><strong>{label(desk)}</strong><small>{hold ? label(hold.reason_code) : review ? 'Signed by ' + review.actor_id : 'Awaiting desk finding'}</small>{review?.reason && <p>{review.reason}</p>}</div><Badge value={hold ? 'hold' : review?.disposition || 'pending'} /></div>
          })}
        </section>
        <PacketList packets={file.packets} sources={file.sources} currency={file.currency} mode={file.mode} />
        {file.decision && <section className="card"><h2>Final disposition</h2><p><strong>{label(file.decision.decision)}</strong> · {file.decision.actor_id} · Rev. {file.decision.revision}</p></section>}
        {receipt && <section className="card receipt"><h2>Simulated issuance receipt</h2><p><code>{receipt.receipt_id}</code></p><p>{receipt.actor_id} · Rev. {receipt.revision}</p></section>}
      </div>
      <aside className="stack"><ActionPanel key={file.case_id + ':' + file.revision + ':' + file.packet_hash} {...controls} />
        <section className="card context"><h2>File details</h2><dl>
          <dt>Invoice</dt><dd>{file.invoice_ref || 'Outstanding'}</dd>
          {file.headroom_after_minor != null && <><dt>Headroom after issue</dt><dd>{money(file.headroom_after_minor, file.currency)}</dd></>}
          {file.mandate_minor != null && <><dt>Officer mandate</dt><dd>{money(file.mandate_minor, file.mandate_currency)}</dd></>}
          <dt>Source snapshot</dt><dd>{fmtDate(file.as_of, true)}</dd>
          <dt>Deployment</dt><dd>{file.configured_mode === 'live' ? 'Live · BRANE' : 'Fixture · synthetic'}</dd>
          {mode && <><dt>Packet analysis</dt><dd>{mode === 'fixture' ? 'Fixture · synthetic' : 'Live · BRANE'}</dd></>}
          {file.last_run && <><dt>Last run</dt><dd>{label(file.last_run.status)} <code>{file.last_run.run_id}</code></dd></>}
          {file.last_run?.analysis && <>
            <dt>Configured policy</dt><dd>{file.last_run.analysis.policy_version}</dd>
            {verifiedPolicy && <><dt>Verified policy digest</dt><dd><code>{verifiedPolicy}</code></dd></>}
            {file.last_run.analysis.observations.filter(item => item.route !== 'fixture').map((item, index) =>
              <Fragment key={index}><dt>{label(item.task.replace(/^draft_/, ''))} route</dt><dd>{label(item.route)}{' '}
                {item.model && <code>{item.model}</code>}{' '}
                {(item.log_ref || item.provider_request_id) && <code>{item.log_ref || item.provider_request_id}</code>}
              </dd></Fragment>)}
          </>}
          {file.packet_hash && <><dt>Sealed packet</dt><dd><code>{file.packet_hash}</code></dd></>}
        </dl></section>
      </aside>
    </div>}
    {tab === 'Desk messages' && <Inbox key={file.requests.map(r => r.request_id + r.status).join('|')} {...controls} />}
    {tab === 'Audit trail' && <History audit={audit} file={file} />}
  </>
}

type WorkspaceView = 'dashboard' | 'case' | 'approvals'

function Workspace({ token, staff, end, initialView, initialCase, compose, reviewDesk, initialEditor, focusRun }: {
  token: string; staff: Staff; end: (nextView?: WorkspaceView, preferred?: PreferredDesk) => void; initialView: WorkspaceView
  initialCase: string; compose: (workflow: string, caseId: string, view: WorkspaceView) => void
  reviewDesk: (session: StaffSession, editor: ApprovalEditor, view: WorkspaceView) => void; initialEditor: ApprovalEditor | null
  focusRun: MutableRefObject<string | null>
}) {
  const [view, setView] = useState<WorkspaceView>(initialView)
  const [syncError, setSyncError] = useState('')
  const [queue, setQueue] = useState<Summary[]>([])
  const [selected, setSelected] = useState('')
  const [workflowFilter, setWorkflowFilter] = useState('')
  const [file, setFile] = useState<StaffFile | null>(null)
  const [audit, setAudit] = useState<AuditEvent[]>([])
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editor, setEditor] = useState(initialEditor)
  const sequence = useRef(0)
  const lock = useRef(false)
  const retryKeys = useRef(new Map<string, string>())

  const load = useCallback(async (id?: string, background = false) => {
    const request = ++sequence.current
    if (!background) { setLoading(true); setError('') }
    try {
      const cases = await bank<Summary[]>(token, '/cases')
      const target = cases.find(item => item.case_id === id)?.case_id || cases[0]?.case_id || ''
      const path = '/cases/' + encodeURIComponent(target)
      const [detail, history] = target ? await Promise.all([bank<StaffFile>(token, path), bank<AuditEvent[]>(token, path + '/audit')]) : [null, []]
      if (request !== sequence.current) return
      setSyncError(''); setQueue(cases); setSelected(target); tabValue(selectedKey, target); setFile(detail); setAudit(history)
      return detail
    } catch (err) {
      if (request !== sequence.current) return
      if (err instanceof BankError && err.status === 401) { end(); return }
      if (background && err instanceof BankError && (err.status === 0 || err.status >= 500)) {
        setSyncError('Updates paused. Showing the last available activity.')
        return
      }
      setError(textError(err)); setFile(null); setAudit([]); setQueue([])
    } finally { if (request === sequence.current) setLoading(false) }
  }, [token, end])
  useEffect(() => { void load(initialCase || tabValue(selectedKey) || undefined); return () => { sequence.current++ } }, [load, initialCase])

  useEffect(() => {
    if (!focusRun.current || file?.last_run?.run_id !== focusRun.current) return
    const panel = document.getElementById('agent-reply')
    if (!panel) return
    focusRun.current = null
    panel.focus({ preventScroll: true })
    panel.scrollIntoView({ block: window.matchMedia('(max-width: 750px)').matches ? 'start' : 'nearest' })
  }, [file?.last_run?.run_id, view, focusRun])

  useEffect(() => {
    const pending = file?.last_run?.status === 'pending'
    if (loading || busy) return
    let stopped = false
    let timer: number
    const poll = async () => {
      if (!document.hidden) await load(selected, true)
      if (!stopped) schedule()
    }
    const schedule = () => { timer = window.setTimeout(poll, pending ? 800 : 3500) }
    schedule()
    return () => { stopped = true; window.clearTimeout(timer) }
  }, [selected, file?.last_run?.status, loading, busy, view, load])

  const submit: Submit = async (suffix, body, message) => {
    if (lock.current) return false
    lock.current = true; setBusy(true); setError(''); setNotice('')
    const path = '/cases/' + encodeURIComponent(selected) + suffix
    const identity = path + JSON.stringify(body)
    const key = retryKeys.current.get(identity) || crypto.randomUUID()
    retryKeys.current.set(identity, key)
    try {
      const result = await bank<{ run_id?: string }>(token, path, body, key)
      if (suffix === '/runs' && result.run_id) focusRun.current = result.run_id
      retryKeys.current.delete(identity)
      const updated = await load(selected)
      const plan = updated?.human_approval
      if (plan?.stage === 'decision' && file?.human_approval?.stage !== 'decision') {
        setNotice('Desk review signed. Sent to ' + plan.final.name + ' for final approval.')
        document.querySelector('.approval-panel')?.scrollIntoView({ block: 'start' })
      } else if (suffix !== '/runs') setNotice(message)
      return true
    } catch (err) {
      if (err instanceof BankError && err.status === 401) { end(); return false }
      if (err instanceof BankError && err.status > 0 && err.status < 500) retryKeys.current.delete(identity)
      if (err instanceof BankError && (err.status === 409 || err.status === 404)) await load(selected)
      setError(textError(err)); return false
    } finally { lock.current = false; setBusy(false) }
  }
  const workflows = new Map(queue.map(item => [item.workflow_id, item.workflow_title]))
  const filteredQueue = workflowFilter ? queue.filter(item => item.workflow_id === workflowFilter) : queue
  const myApprovals = queue.filter(item => item.my_approval)
  function openReview(caseId: string) {
    const item = myApprovals.find(entry => entry.case_id === caseId)
    if (!item?.my_approval) return
    setNotice(''); setEditor({caseId, revision:item.revision, task:item.my_approval}); setView('dashboard')
    if (caseId !== selected) void load(caseId)
  }
  async function openRecipient(person: StaffContact, task: ApprovalTask) {
    if (lock.current || !file) return
    const nextEditor = {caseId:file.case_id, revision:file.revision, task}
    setNotice('')
    if (person.id === staff.id) { setEditor(nextEditor); return }
    if (!staff.desk_picker) return
    lock.current = true; setBusy(true); setError('')
    try {
      const next = await bank<StaffSession>(null, '/demo-session', {desk_id: person.id})
      reviewDesk(next, nextEditor, view)
    } catch (err) { setError(textError(err)) }
    finally { lock.current = false; setBusy(false) }
  }
  const controls = { staff, submit, busy: busy || loading || !!syncError }
  const stage = file?.human_approval?.stage
  const approval = file && stage && stage !== 'preparing' && stage !== 'other_mode'
    ? <ApprovalPanel file={file} open={openRecipient} task={editor?.caseId === file.case_id && editor.revision === file.revision ? editor.task : null}
        close={() => setEditor(null)} {...controls} /> : null
  let content: ReactNode
  if (view === 'approvals') {
    content = loading ? <p role="status">Loading your inbox…</p>
      : !error && <ApprovalInbox items={myApprovals} open={openReview} staff={staff} busy={controls.busy} />
  } else if (!file) {
    content = loading ? <p className="card muted" role="status">Loading case workspace…</p>
      : !error && <section className="card empty"><h1>No assigned cases</h1><p>Your assigned work will appear here.</p></section>
  } else if (view === 'dashboard') {
    content = <RequestDashboard key={file.case_id} file={file} audit={audit} queue={filteredQueue} approval={approval}
      open={() => setView('case')} select={id => { setNotice(''); void load(id) }} {...controls} />
  } else {
    content = <><AgentReply file={file} />{approval}<SubmittedDetails file={file} />
      {file.department_case
        ? <DepartmentWorkspace key={file.case_id} file={file} history={<History audit={audit} file={file} />} {...controls} />
        : <CaseContents key={file.case_id} file={file} audit={audit} {...controls} />}</>
  }
  let handoff: PreferredDesk | undefined
  if (file?.department_case) {
    const meta = file.department_case
    const next = meta.evidence_verified && file.packet_hash
      ? file.holds[0]?.desk || meta.reviewers.find(role => !file.reviews.some(r => r.desk === role && r.disposition === 'clear'))
      : meta.analyst
    handoff = { workflowId: file.workflow_id, seat: file.status === 'ready_for_decision' ? 'approver' : 'analyst',
      partner: next && next !== meta.analyst ? next : undefined }
  }
  return <div className={'workspace ' + (view === 'dashboard' ? 'tracking-workspace' : '')}><header><Brand /><span className="product-name">Corporate banking</span><div className="account"><span className="account-icon"><DeskIcon role={staff.role} size={21} /></span><div><strong>{staff.name}</strong><small>{staff.role_label || label(staff.role)}</small></div><button disabled={busy} onClick={() => end(staff.desk_picker ? view : 'dashboard', handoff)}>{staff.desk_picker ? <ArrowsLeftRightIcon size={16} /> : <SignOutIcon size={16} />}{staff.desk_picker ? 'Switch desk' : 'Sign out'}</button></div></header>
    <div className="shell"><aside className="sidebar">
      <nav className="workspace-nav" aria-label="Workspace">
        {(staff.desk_picker || staff.role === 'coverage' || (staff.role.startsWith('dept_') && !staff.role.endsWith('_head'))) &&
          <button className="new-request-button" disabled={busy} onClick={() => compose(file?.workflow_id || '', selected, view)}><FilePlusIcon size={19} />New request</button>}
        <button aria-current={view === 'dashboard' ? 'page' : undefined} onClick={() => setView('dashboard')}><CirclesFourIcon size={19} weight="duotone" />Agent dashboard</button>
        <button aria-current={view === 'case' ? 'page' : undefined} onClick={() => setView('case')}><FolderOpenIcon size={19} weight="duotone" />Case workspace</button>
        <button aria-current={view === 'approvals' ? 'page' : undefined} onClick={() => { setNotice(''); setView('approvals'); void load(selected) }}><TrayIcon size={19} weight="duotone" />My approvals <span className="inbox-count">{myApprovals.length}</span></button>
      </nav>
      <div className="sidebar-cases"><div className="queue-head"><h2>Assigned cases</h2><span>{queue.length}</span></div>
      {workflows.size > 1 && <label className="queue-filter">Workflow<select value={workflowFilter} onChange={e => {
        const id=e.target.value; setWorkflowFilter(id)
        const next=queue.find(item => item.workflow_id === id)
        if (id && next && file?.workflow_id !== id) {setNotice(''); void load(next.case_id)}
      }}><option value="">All assigned workflows</option>{[...workflows].map(([id,title])=><option key={id} value={id}>{title}</option>)}</select></label>}
      <nav aria-label="Assigned cases">{filteredQueue.map(item => <button disabled={busy} aria-current={item.case_id === selected ? 'true' : undefined} className={'queue-item ' + (item.case_id === selected ? 'selected' : '')} key={item.case_id} onClick={() => { setNotice(''); if (view === 'approvals') setView('case'); void load(item.case_id) }}>
        <strong title={item.case_id}>{caseLabel(item.case_id)}</strong><span>{item.case_title || item.customer_ref}</span><small>{label(item.status)} · Rev. {item.revision}</small>
      </button>)}</nav>
      </div>
    </aside><main className="case-main">
      <div className="toolbar"><span>{view === 'approvals' ? staff.name : file?.department || 'Corporate banking'} <i>/</i> {view === 'dashboard' ? 'Dashboard' : view === 'approvals' ? 'My approvals' : 'Case workspace'}</span><button className="refresh-button" disabled={busy || loading} onClick={() => {setNotice(''); void load(selected)}}><ArrowsClockwiseIcon size={15} />Refresh</button></div>
      {error && <Notice danger>{error}</Notice>}{syncError && <Notice>{syncError}</Notice>}{notice && <Notice>{notice}</Notice>}
      {content}
    </main></div></div>
}

export default function App() {
  const [session, setSession] = useState<{staff: Staff; token: string} | null>(null)
  const [saved, setSaved] = useState(() => tabValue(sessionKey))
  const [restoreError, setRestoreError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [initialView, setInitialView] = useState<WorkspaceView>('dashboard')
  const [preferred, setPreferred] = useState<PreferredDesk>()
  const [composing, setComposing] = useState<string | null>(null)
  const [initialCase, setInitialCase] = useState('')
  const [initialEditor, setInitialEditor] = useState<ApprovalEditor | null>(null)
  const focusRun = useRef<string | null>(null)
  const end = useCallback((nextView: WorkspaceView = 'dashboard', preferredDesk?: PreferredDesk) => {
    setPreferred(preferredDesk)
    setInitialCase('')
    setInitialEditor(null)
    setInitialView(nextView)
    tabValue(sessionKey, null)
    setSaved(null); setRestoreError(''); setSession(null)
  }, [])
  useEffect(() => {
    if (!saved) return
    let active = true
    setRestoreError('')
    bank<Staff>(saved, '/me').then(staff => {
      if (active) { setSession({ staff, token: saved }); setSaved(null) }
    }).catch(error => {
      if (!active) return
      if (error instanceof BankError && error.status === 401) end()
      else setRestoreError(textError(error))
    })
    return () => { active = false }
  }, [saved, attempt, end])
  if (saved) return <main className="login-page"><div className="login-bar"><Brand /></div><div className="login-center"><section className="login-card action-form">
    <h1>Staff session</h1>{restoreError ? <><Notice danger>{restoreError}</Notice><button onClick={() => setAttempt(value => value + 1)}>Reconnect</button><button onClick={() => end()}>Sign out</button></> : <p role="status">Verifying your staff credential…</p>}
  </section></div></main>
  if (composing !== null) return <RequestComposer preferred={composing} session={session} cancel={() => setComposing(null)} created={(owner, caseId, runId) => {
    focusRun.current = runId
    tabValue(sessionKey, owner.token); tabValue(selectedKey, caseId)
    setSession(owner); setInitialCase(caseId); setInitialEditor(null); setInitialView('dashboard'); setComposing(null); window.scrollTo(0, 0)
  }} />
  return session ? <Workspace key={session.staff.id} {...session} initialCase={initialCase} initialView={initialView} end={end} initialEditor={initialEditor} focusRun={focusRun} reviewDesk={(next, editor, view) => {
    tabValue(sessionKey, next.token); tabValue(selectedKey, editor.caseId)
    setSession(next); setInitialCase(editor.caseId); setInitialView(view); setInitialEditor(editor)
  }} compose={(workflow, caseId, view) => {
    setInitialEditor(null); setInitialCase(caseId); setInitialView(view); setComposing(workflow)
  }} /> : <SignIn preferred={preferred} compose={() => setComposing('')} start={(staff, token) => {
    tabValue(sessionKey, token); setSession({ staff, token })
  }} />
}
