import { useEffect, useRef, useState } from 'react'
import { bank, label, textError, type Department, type Staff } from './api'
import { ArrowRightIcon, ArrowUpRightIcon, KeyholeIcon, MagnifyingGlassIcon } from '@phosphor-icons/react'
import { Brand, DeskIcon } from './Brand'
import campus from './assets/redwood-campus.webp'
import './sign-in.css'

type Desk = Pick<Staff, 'id' | 'name' | 'role'>
type Session = { staff: Staff; token: string }
const duties: Record<string, string> = {
  coverage: 'Open the case and supply evidence.',
  trade_finance: 'Check the instrument and documents.',
  credit_risk: 'Review exposure and facility limits.',
  compliance: 'Review evidence and resolve holds.',
  final_officer: 'Make the final decision.',
  operations: 'Record simulated issuance.',
}

const groups = [
  ['Letter of credit', 'Letter of credit'], ['Corporate banking', 'Corporate banking'],
  ['Markets and securities', 'Markets'], ['Risk and control', 'Risk & control'], ['Group functions', 'Group functions'],
]

function Campus({ departments }: { departments: number }) {
  return <aside className="case-brief" aria-labelledby="campus-heading">
    <div className="brief-art">
      <img src={campus} alt="An orange-trimmed tower rises above the bank’s columned entrance, surrounded by office buildings and tree-lined streets." width="1120" height="540" />
    </div>
    <div className="brief-info">
      <h2 id="campus-heading">BRANE <span>×</span> Redwood</h2>
      <p className="campus-purpose">Corporate banking agentic application</p>
      <dl className="brief-meta">
        <div><dt>Workflows</dt><dd>{departments + 1}</dd></div>
        <div><dt>Seeded cases</dt><dd>{departments * 2 + 2}</dd></div>
      </dl>
    </div>
  </aside>
}
export type PreferredDesk = { workflowId: string; seat: 'analyst' | 'approver'; partner?: string }
export default function SignIn({ start, preferred }: { start: (staff: Staff, token: string) => void; preferred?: PreferredDesk }) {
  const [desks, setDesks] = useState<Desk[] | null>(null)
  const [departments, setDepartments] = useState<Department[]>([])
  const [group, setGroup] = useState('Letter of credit')
  const [query, setQuery] = useState('')
  const [seat, setSeat] = useState<'analyst' | 'approver'>(preferred?.seat || 'analyst')
  const [live, setLive] = useState(false)
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const [token, setToken] = useState('')
  const lock = useRef(false)
  useEffect(() => {
    let current = true
    setError('')
    bank<{ desks: Desk[], departments?: Department[], mode?: string }>(null, '/entry')
      .then(result => {
        if (current) {
          setLive(result.mode === 'live')
          setDesks(result.desks)
          const profiles = result.departments || []
          setDepartments(profiles)
          const nextDesk = profiles.find(p => p.id === preferred?.workflowId)
          if (preferred?.partner) {
            setGroup('Letter of credit')
            setQuery(label(preferred.partner))
          } else if (nextDesk) {
            setGroup(nextDesk.group)
            setQuery(nextDesk.desk)
          }
        }
      })
      .catch(reason => { if (current) setError(textError(reason)) })
    return () => { current = false }
  }, [retry, preferred])

  async function enter(desk?: Pick<Desk, 'id'>) {
    if (lock.current) return
    lock.current = true
    setPending(desk?.id ?? 'staff')
    setError('')
    try {
      if (desk) {
        const session = await bank<Session>(null, '/demo-session', { desk_id: desk.id })
        start(session.staff, session.token)
      } else {
        const credential = token.trim()
        start(await bank<Staff>(credential, '/me'), credential)
      }
    } catch (reason) {
      setError(textError(reason))
    } finally {
      lock.current = false
      setPending('')
    }
  }

  const demo = Boolean(desks?.length)
  const term = query.trim().toLowerCase()
  const directory = departments.filter(d => term
    ? [d.desk, d.workflow, d.code, d.group].some(text => text.toLowerCase().includes(term)) : d.group === group)
  const core = (desks || []).filter(d => term
    ? [label(d.role), d.name, 'Letter of credit'].some(text => text.toLowerCase().includes(term)) : group === 'Letter of credit')
  return <main className="entry-page">
    <header className="entry-header"><div className="entry-mast"><Brand /><span className="mast-unit">Corporate banking</span></div>
      {desks && <span className="mode-pill"><i />{demo ? (live ? 'Live BRANE rehearsal' : 'Local fixture') : 'Staff access'}</span>}
    </header>
    {demo ? <section className="entry-body">
      <div className="entry-intro"><div className="entry-kicker section-label">Staff directory</div>
        <h1>Choose your desk</h1>
        <p>Open the letter-of-credit walkthrough or choose a specialist desk to work its assigned cases.</p>
      </div>
      {departments.length > 0 && <div className="directory-bar">
        <nav className="directory-groups" aria-label="Desk groups">{groups.map(([key, title]) =>
          <button type="button" key={key} aria-pressed={!term && group === key} onClick={() => {setGroup(key); setQuery('')}}>{title}</button>
        )}</nav>
        <label className="directory-search"><MagnifyingGlassIcon size={16} />
          <input type="search" aria-label="Find a desk or workflow" placeholder="Find a desk or workflow" value={query} onChange={e => setQuery(e.target.value)} />
        </label>
      </div>}
      <div className="entry-layout">
        <Campus departments={departments.length} />
        <div className="directory-results">
          {directory.length > 0 && <div className="seat-controls"><span>Specialist access</span>
            <div role="group" aria-label="Specialist seat">{(['analyst', 'approver'] as const).map(v =>
              <button type="button" key={v} aria-pressed={v === seat} onClick={() => setSeat(v)}>{v === 'analyst' ? 'Analyst' : 'Approver'}</button>)}</div>
          </div>}
          <div className="desk-grid" aria-label="Demo desks">
            {core.map(desk => <button key={desk.id} type="button" className={'desk-choice desk-' + desk.role} disabled={Boolean(pending)} onClick={() => enter(desk)}>
              <span className="desk-top" aria-hidden="true"><span className="desk-icon"><DeskIcon role={desk.role} /></span><ArrowUpRightIcon className="desk-arrow" size={19} /></span>
              <strong>{label(desk.role)}</strong><span className="desk-name">{desk.name}</span>
              <span className="desk-duty">{pending === desk.id ? 'Opening desk…' : duties[desk.role]}</span>
            </button>)}
            {directory.map(dept => <button key={dept.id} type="button" className="desk-choice" disabled={Boolean(pending)} onClick={() => enter(dept[seat])}>
              <span className="desk-top" aria-hidden="true"><DeskIcon role={'dept_' + dept.code.toLowerCase()} /><ArrowUpRightIcon className="desk-arrow" size={19} /></span>
              <strong>{dept.desk}</strong><span className="desk-name">{dept[seat].name} · {seat}</span>
              <span className="desk-duty">{pending === dept[seat].id ? 'Opening desk…' : dept.workflow}</span>
            </button>)}
          </div>
          {!core.length && !directory.length && <p className="card muted" role="status">No desks match this search.</p>}
        </div>
      </div>
      {error && <p role="alert" className="error">{error}</p>}
    </section> : <div className="login-center"><section className="login-card">
      {desks ? <><KeyholeIcon size={32} weight="duotone" /><h1>Staff sign-in</h1></> : <h1>Corporate banking</h1>}
      {desks && <form className="action-form" onSubmit={event => { event.preventDefault(); void enter() }}>
        <label>Staff token<input required type="password" value={token} onChange={e => setToken(e.target.value)} autoComplete="off" spellCheck={false} /></label>
        <button className="primary" disabled={Boolean(pending) || !token.trim()}>{pending ? 'Opening desk…' : 'Sign in'} <ArrowRightIcon size={16} /></button>
      </form>}
      {!desks && !error && <p role="status">Loading workspace…</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {!desks && error && <button onClick={() => setRetry(n => n + 1)}>Try again</button>}
    </section></div>}
  </main>
}
