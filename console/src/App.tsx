import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { ActionPanel, Inbox } from './Actions'
import PacketList from './PacketList'
import { bank, BankError, desks, label, money, textError, type AuditEvent, type CaseFile, type Staff, type Submit, type Summary } from './api'

const sessionKey = 'clearance.staff-token'
const selectedKey = 'clearance.selected-case'

function tabValue(key: string, next?: string | null): string | null {
  try {
    if (next === null) sessionStorage.removeItem(key)
    else if (next !== undefined) sessionStorage.setItem(key, next)
    return sessionStorage.getItem(key)
  } catch { return null }
}

function Brand() {
  return <div className="brand"><span className="brand-mark" aria-hidden="true">C</span>Clearance</div>
}
function Badge({ value }: { value: string }) {
  return <span className={'pill ' + value}>{label(value)}</span>
}
function Login({ start }: { start: (staff: Staff, token: string) => void }) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const field = useRef<HTMLInputElement>(null)
  return <main className="login-page"><div className="login-bar"><Brand /><span>Corporate banking</span></div>
    <div className="login-center"><section className="login-card">
      <div className="eyebrow">Trade finance</div><h1>Staff sign-in</h1>
      <p>Open your assigned cases with your local demo credential.</p>
      <form className="action-form" onSubmit={async e => {
        e.preventDefault()
        if (busy || !token.trim()) return
        setBusy(true); setError('')
        try { const staff = await bank<Staff>(token.trim(), '/me'); start(staff, token.trim()) }
        catch (err) { setError(textError(err)); field.current?.focus() }
        finally { setBusy(false) }
      }}>
        <label>Staff token<input ref={field} type="password" required autoComplete="off" spellCheck={false} autoCapitalize="none" value={token} onChange={e => setToken(e.target.value)} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy || !token.trim()}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </section></div>
  </main>
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

function CaseContents({ file, audit, staff, submit, busy }: { file: CaseFile; audit: AuditEvent[]; staff: Staff; submit: Submit; busy: boolean }) {
  const [tab, setTab] = useState('Overview')
  const clearCount = file.reviews.filter(r => r.disposition === 'clear').length
  const controls = { file, staff, submit, busy }
  const receipt = file.receipt
  const mode = file.last_run?.mode || file.mode
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
    {file.last_run && ['analysis_unavailable', 'unavailable', 'failed'].includes(file.last_run.status) && <Notice danger>Analysis unavailable. The run did not produce a signed packet. <code>{file.last_run.run_id}</code></Notice>}
    <nav className="view-tabs" aria-label="Case sections">{['Overview', 'Desk messages', 'Audit trail'].map(title => <button key={title} aria-current={title === tab ? 'page' : undefined} className={tab === title ? 'active' : ''} onClick={() => setTab(title)}>{title}</button>)}</nav>
    {tab === 'Overview' && <div className="case-grid">
      <div className="stack">
        <section className="card"><div className="card-head"><h2>Department sign-offs</h2><span className="quiet">Rev. {file.revision}</span></div>
          {desks.map(desk => {
            const review = file.reviews.find(r => r.desk === desk)
            const hold = file.holds.find(h => h.desk === desk)
            return <div key={desk} className="desk-row"><div><strong>{label(desk)}</strong><small>{hold ? label(hold.reason_code) : review ? 'Signed by ' + review.actor_id : 'Awaiting desk finding'}</small>{review?.reason && <p>{review.reason}</p>}</div><Badge value={hold ? 'hold' : review?.disposition || 'pending'} /></div>
          })}
        </section>
        <PacketList packets={file.packets} sources={file.sources} currency={file.currency} />
        {file.decision && <section className="card"><h2>Final disposition</h2><p><strong>{label(file.decision.decision)}</strong> · {file.decision.actor_id} · Rev. {file.decision.revision}</p></section>}
        {receipt && <section className="card receipt"><h2>Simulated issuance receipt</h2><p><code>{receipt.receipt_id}</code></p><p>{receipt.actor_id} · Rev. {receipt.revision}</p></section>}
      </div>
      <aside className="stack"><ActionPanel key={file.case_id + ':' + file.revision + ':' + file.packet_hash + ':' + file.reviews.map(r => r.event_id).join(',')} {...controls} />
        <section className="card context"><h2>File details</h2><dl>
          <dt>Invoice</dt><dd>{file.invoice_ref || 'Outstanding'}</dd>
          {file.headroom_after_minor != null && <><dt>Headroom after issue</dt><dd>{money(file.headroom_after_minor, file.currency)}</dd></>}
          {file.mandate_minor != null && <><dt>Officer mandate</dt><dd>{money(file.mandate_minor, file.mandate_currency)}</dd></>}
          <dt>Source snapshot</dt><dd>{fmtDate(file.as_of, true)}</dd>
          <dt>Deployment</dt><dd>{file.configured_mode === 'live' ? 'Live · BRANE' : 'Fixture · synthetic'}</dd>
          {mode && <><dt>Packet analysis</dt><dd>{mode === 'fixture' ? 'Fixture · synthetic' : 'Live · BRANE'}</dd></>}
          {file.last_run && <><dt>Last run</dt><dd>{label(file.last_run.status)} <code>{file.last_run.run_id}</code></dd></>}
          {file.packet_hash && <><dt>Sealed packet</dt><dd><code>{file.packet_hash}</code></dd></>}
        </dl></section>
      </aside>
    </div>}
    {tab === 'Desk messages' && <Inbox key={file.requests.map(r => r.request_id + r.status).join('|')} {...controls} />}
    {tab === 'Audit trail' && <section className="card"><h2>Case history</h2>
      {!audit.length && <p className="muted">No visible activity.</p>}
      <ol className="timeline">{audit.map(event => <li key={event.event_id}><div><strong>{label(event.action)}</strong><span>{fmtDate(event.timestamp, true)}</span></div>
        <p>{event.actor_id} · {label(event.desk)} · Rev. {event.revision}</p>
        {typeof event.detail === 'string' && event.detail && <p>{event.detail}</p>}
        {event.detail && typeof event.detail === 'object' ? <dl>{Object.entries(event.detail).filter(([,v]) => ['string','number','boolean'].includes(typeof v)).map(([k,v]) => <div key={k}><dt>{label(k)}</dt><dd>{String(v)}</dd></div>)}</dl> : null}
      </li>)}</ol>
    </section>}
  </>
}

function Workspace({ token, staff, end }: { token: string; staff: Staff; end: () => void }) {
  const [queue, setQueue] = useState<Summary[]>([])
  const [selected, setSelected] = useState('')
  const [file, setFile] = useState<CaseFile | null>(null)
  const [audit, setAudit] = useState<AuditEvent[]>([])
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const sequence = useRef(0)
  const lock = useRef(false)
  const retryKeys = useRef(new Map<string, string>())

  const load = useCallback(async (id?: string) => {
    const request = ++sequence.current
    setLoading(true); setError('')
    try {
      const cases = await bank<Summary[]>(token, '/cases')
      const target = cases.find(item => item.case_id === id)?.case_id || cases[0]?.case_id || ''
      const path = '/cases/' + encodeURIComponent(target)
      const [detail, history] = target ? await Promise.all([bank<CaseFile>(token, path), bank<AuditEvent[]>(token, path + '/audit')]) : [null, []]
      if (request !== sequence.current) return
      setQueue(cases); setSelected(target); tabValue(selectedKey, target); setFile(detail); setAudit(history)
    } catch (err) {
      if (request !== sequence.current) return
      if (err instanceof BankError && err.status === 401) { end(); return }
      setError(textError(err)); setFile(null); setAudit([]); setQueue([])
    } finally { if (request === sequence.current) setLoading(false) }
  }, [token, end])
  useEffect(() => { void load(tabValue(selectedKey) || undefined); return () => { sequence.current++ } }, [load])

  useEffect(() => {
    if (file?.last_run?.status !== 'pending' || loading || busy) return
    const timer = window.setTimeout(() => { void load(file.case_id) }, 1000)
    return () => window.clearTimeout(timer)
  }, [file, loading, busy, load])

  const submit: Submit = async (suffix, body, message) => {
    if (lock.current) return false
    lock.current = true; setBusy(true); setError(''); setNotice('')
    const path = '/cases/' + encodeURIComponent(selected) + suffix
    const identity = path + JSON.stringify(body)
    const key = retryKeys.current.get(identity) || crypto.randomUUID()
    retryKeys.current.set(identity, key)
    try {
      await bank(token, path, body, key)
      retryKeys.current.delete(identity)
      await load(selected)
      setNotice(message)
      return true
    } catch (err) {
      if (err instanceof BankError && err.status === 401) { end(); return false }
      if (err instanceof BankError && err.status > 0 && err.status < 500) retryKeys.current.delete(identity)
      if (err instanceof BankError && (err.status === 409 || err.status === 404)) await load(selected)
      setError(textError(err)); return false
    } finally { lock.current = false; setBusy(false) }
  }
  return <div className="workspace"><header><Brand /><span className="product-name">Corporate banking</span><div className="account"><div><strong>{staff.name}</strong><small>{label(staff.role)}</small></div><button onClick={end}>Sign out</button></div></header>
    <div className="shell"><aside className="sidebar"><div className="eyebrow">Work queue</div><div className="queue-head"><h2>Assigned cases</h2><span>{queue.length}</span></div>
      <nav aria-label="Assigned cases">{queue.map(item => <button disabled={busy} aria-current={item.case_id === selected ? 'page' : undefined} className={'queue-item ' + (item.case_id === selected ? 'selected' : '')} key={item.case_id} onClick={() => { setNotice(''); void load(item.case_id) }}>
        <strong>{item.case_id}</strong><span>{item.customer_ref}</span><small>{label(item.status)} · Rev. {item.revision}</small>
      </button>)}</nav>
      {staff.role === 'coverage' && <button className="intake" disabled={busy || loading} onClick={async () => {
        if (lock.current) return
        lock.current = true; setBusy(true); setError(''); setNotice('')
        const intake = { fixture_id: 'LC-DEMO-001', customer_ref: staff.customer_ref, facility_ref: 'FAC-USD-01', amount_minor: 200000000, currency: 'USD', instrument: 'import_documentary_credit', expiry: '2027-01-31' }
        const key = retryKeys.current.get('intake') || crypto.randomUUID()
        retryKeys.current.set('intake', key)
        try {
          const created = await bank<Summary>(token, '/cases', intake, key)
          retryKeys.current.delete('intake')
          await load(created.case_id); setNotice('Synthetic intake opened.')
        } catch (err) {
          if (err instanceof BankError && err.status === 401) { end(); return }
          if (err instanceof BankError && err.status > 0 && err.status < 500) retryKeys.current.delete('intake')
          setError(textError(err))
        } finally { lock.current = false; setBusy(false) }
      }}>Open synthetic intake</button>}
    </aside><main className="case-main">
      <div className="toolbar"><span>Trade finance <i>/</i> Case workspace</span><button className="text-button" disabled={busy || loading} onClick={() => {setNotice(''); void load(selected)}}>Refresh</button></div>
      {error && <Notice danger>{error}</Notice>}{notice && <Notice>{notice}</Notice>}
      {file ? <CaseContents key={file.case_id} file={file} audit={audit} staff={staff} busy={busy || loading} submit={submit} /> : loading ? <p className="card muted" role="status">Loading case workspace…</p> : !error && <section className="card empty"><h1>No assigned cases</h1><p>Your assigned work will appear here.</p></section>}
    </main></div></div>
}

export default function App() {
  const [session, setSession] = useState<{staff: Staff; token: string} | null>(null)
  const [saved, setSaved] = useState(() => tabValue(sessionKey))
  const [restoreError, setRestoreError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const end = useCallback(() => {
    tabValue(sessionKey, null); tabValue(selectedKey, null)
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
    <h1>Staff session</h1>{restoreError ? <><Notice danger>{restoreError}</Notice><button onClick={() => setAttempt(value => value + 1)}>Reconnect</button><button onClick={end}>Sign out</button></> : <p role="status">Verifying your staff credential…</p>}
  </section></div></main>
  return session ? <Workspace {...session} end={end} /> : <Login start={(staff, token) => {
    tabValue(sessionKey, token); tabValue(selectedKey, null); setSession({ staff, token })
  }} />
}
