import { useEffect, useRef, useState } from 'react'
import { bank, label, textError, type Staff } from './api'
import './sign-in.css'

export function Brand() {
  return <div className="brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>Clearance</div>
}

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

function CaseBrief() {
  return <aside className="case-brief" aria-label="Walkthrough case">
    <div className="brief-graphic" aria-hidden="true">
      <div className="paper-back" />
      <div className="paper-front"><i className="paper-seal" /><i className="paper-lines" /><i className="paper-sign" /></div>
    </div>
    <div className="brief-info"><div className="entry-kicker">Walkthrough case</div>
      <h2>Import letter<br /> of credit</h2>
      <div className="brief-meta"><code>LC-001</code><span>USD 2,000,000</span></div>
    </div>
  </aside>
}

export default function SignIn({ start }: { start: (staff: Staff, token: string) => void }) {
  const [desks, setDesks] = useState<Desk[] | null>(null)
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const [token, setToken] = useState('')
  const lock = useRef(false)
  useEffect(() => {
    let current = true
    setError('')
    bank<{ desks: Desk[] }>(null, '/entry')
      .then(result => { if (current) setDesks(result.desks) })
      .catch(reason => { if (current) setError(textError(reason)) })
    return () => { current = false }
  }, [retry])

  async function enter(desk?: Desk) {
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
  return <main className="entry-page">
    <header className="entry-header"><div className="entry-mast"><Brand /><span className="mast-unit">Corporate banking</span></div>
      {desks && <span className="mode-pill"><i />{demo ? 'Local demo' : 'Staff access'}</span>}
    </header>
    {demo ? <section className="entry-body">
      <div className="entry-intro"><div className="entry-kicker">Trade finance</div>
        <h1>Choose your desk</h1>
        <p>Start with Coverage, or pick a desk to take over its part of the case.</p>
      </div>
      <div className="entry-layout">
        <CaseBrief />
        <div className="desk-grid" aria-label="Demo desks">{desks!.map(desk =>
          <button key={desk.id} type="button" className={'desk-choice desk-' + desk.role} disabled={Boolean(pending)} onClick={() => enter(desk)}>
            <span className="desk-top"><span className="desk-avatar" aria-hidden="true">{desk.name.split(' ').map(word => word[0]).join('')}</span><span className="desk-arrow" aria-hidden="true">↗</span></span>
            <strong>{label(desk.role)}</strong><span className="desk-name">{desk.name}</span>
            <span className="desk-duty">{pending === desk.id ? 'Opening desk…' : duties[desk.role]}</span>
          </button>
        )}</div>
      </div>
      {error && <p role="alert" className="error">{error}</p>}
    </section> : <div className="login-center"><section className="login-card">
      <div className="entry-kicker">Corporate banking</div><h1>Staff sign-in</h1>
      {desks && <form className="action-form" onSubmit={event => { event.preventDefault(); void enter() }}>
        <label>Staff token<input required type="password" value={token} onChange={e => setToken(e.target.value)} autoComplete="off" spellCheck={false} /></label>
        <button className="primary" disabled={Boolean(pending) || !token.trim()}>{pending ? 'Opening desk…' : 'Sign in'}</button>
      </form>}
      {!desks && !error && <p role="status">Loading workspace…</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {!desks && error && <button onClick={() => setRetry(n => n + 1)}>Try again</button>}
    </section></div>}
  </main>
}
