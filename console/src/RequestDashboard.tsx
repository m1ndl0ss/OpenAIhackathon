import { useEffect, useState } from 'react'
import {
  PulseIcon,
  ArrowDownLeftIcon,
  ArrowRightIcon,
  ArrowUpRightIcon,
  CpuIcon,
  BriefcaseIcon,
  ChartBarIcon,
  CheckIcon,
  RadioButtonIcon,
  ClipboardTextIcon,
  ClockIcon,
  FilesIcon,
  GitBranchIcon,
  TrayIcon,
  StackIcon,
  PauseCircleIcon,
  PlayIcon,
  BroadcastIcon,
  ArrowCounterClockwiseIcon,
  ShieldCheckIcon,
  StopIcon,
  FlowArrowIcon,
  ArrowCircleUpRightIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react'
import {
  desks,
  caseLabel,
  label,
  money,
  type AuditEvent,
  type StaffFile,
  deskName,
  type Staff,
  type Summary,
  type Submit,
} from './api'
import RoutingDiagram from './RoutingDiagram'
import './tracker.css'

const tradeTasks = [
  { desk: 'trade_finance', title: 'Trade Finance', icon: FilesIcon },
  { desk: 'credit_risk', title: 'Credit Risk', icon: ChartBarIcon },
  { desk: 'compliance', title: 'Compliance', icon: ShieldCheckIcon },
]
const specialistTasks = [
  { desk: 'evidence', title: 'Evidence review', icon: FilesIcon },
  { desk: 'policy', title: 'Policy review', icon: ShieldCheckIcon },
  { desk: 'handover', title: 'Handover draft', icon: ClipboardTextIcon },
]
const runLabels: Record<string, string> = {
  pending: 'Processing',
  sealed: 'Packet sealed',
  analysis_unavailable: 'Unavailable',
  analysis_refused: 'Analysis refused',
  analysis_invalid: 'Draft failed validation',
  superseded: 'Superseded',
}
function eventName(action: string) {
  if (action.startsWith('task.')) {
    const [, desk, stage] = action.split('.')
    return label(desk) + (stage === 'prepared' ? ' packet prepared' : ' task started')
  }
  const names: Record<string, string> = {
    'case.opened': 'Request received',
    'run.started': 'Organizer received request',
    'run.sealed': 'Review packets sealed',
    'run.analysis_unavailable': 'Analysis unavailable',
    'run.analysis_refused': 'BRANE refused the request',
    'run.analysis_invalid': 'Draft failed validation',
    'run.superseded': 'Run superseded',
    'review.hold': 'Desk placed hold',
    'review.clear': 'Desk signed clear',
    'evidence.attached': 'Invoice attached',
    'request.created': 'Desk request sent',
    'request.answered': 'Desk request answered',
    'receipt.issued': 'Simulated receipt issued',
  }
  return names[action] ?? label(action)
}

function RouteMap({ file, audit }: { file: StaffFile; audit: AuditEvent[] }) {
  const tasks = file.department_case ? specialistTasks : tradeTasks
  const run = file.last_run
  const recorded = audit.filter(
    (e) => e.revision === file.revision && e.detail === run?.run_id && e.action.startsWith('task.'),
  )
  const starts = recorded.filter((e) => e.action.endsWith('.started'))
  const preview = !run || (run.status === 'sealed' && !starts.length)
  const steps = [
    0,
    ...(preview
      ? tasks.map((_, i) => i + 1)
      : starts
          .map((e) => tasks.findIndex((t) => t.desk === e.action.split('.')[1]) + 1)
          .filter((i) => i > 0)),
  ]
  const [frame, setFrame] = useState<number | null>(null)
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const q = matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(q.matches)
    q.addEventListener('change', update)
    return () => q.removeEventListener('change', update)
  }, [])
  const playback = preview || run?.status !== 'pending'
  useEffect(() => {
    setFrame(!reduced && (preview || (run?.status === 'sealed' && run.mode === 'fixture')) ? 0 : null)
  }, [run?.run_id, run?.status, run?.mode, reduced, preview])
  useEffect(() => {
    if (frame === null) return
    const timeout = window.setTimeout(() => setFrame(frame + 1 < steps.length ? frame + 1 : null), 1600)
    return () => window.clearTimeout(timeout)
  }, [frame, steps.length])
  const states = tasks.map((task) => {
    const stage = recorded
      .filter((e) => e.action.startsWith('task.' + task.desk + '.'))
      .at(-1)
      ?.action.split('.')
      .at(-1)
    if (run?.status === 'sealed') return 'Packet ready'
    if (stage === 'prepared') return run?.status === 'pending' ? 'Draft prepared' : 'Draft withheld'
    if (run?.status.startsWith('analysis_')) {
      return stage === 'started' ? runLabels[run.status] ?? 'Stopped' : 'No packet'
    }
    if (run?.status === 'pending' && stage === 'started') return 'Working'
    return 'Waiting'
  })
  const working = states.indexOf('Working')
  const pendingEdge = working >= 0 || !recorded.length ? working + 1 : undefined
  const active = frame !== null ? steps[frame] : run?.status === 'pending' ? pendingEdge : undefined
  const display =
    frame !== null
      ? preview
        ? 'Route preview'
        : 'Run replay'
      : run ? runLabels[run.status] ?? label(run.status) : 'Awaiting analysis'
  const origin = audit.find((e) => e.action === 'case.opened')
  const sender =
    run &&
    audit.find(
      (e) =>
        e.action === 'run.started' &&
        e.revision === file.revision &&
        e.detail === run.mode + ' · ' + run.run_id,
    )?.desk
  const source = deskName(file, sender ?? origin?.desk ?? 'unknown')
  const taskStatus = (i: number) => {
    if (frame === null || active === undefined) return states[i]
    if (active === i + 1) return 'Receiving request'
    if (steps.slice(0, frame).includes(i + 1)) return preview ? 'Routed' : states[i]
    return 'Queued'
  }
  return (
    <section className="track-panel routing-panel">
      <div className="panel-title">
        <div className="track-heading">
          <span className="title-icon">
            <FlowArrowIcon />
          </span>
          <div>
            <h2>Request routing</h2>
            <p>
              <abbr title={file.case_id}>{caseLabel(file.case_id)}</abbr> <span>·</span> {file.workflow_title}
            </p>
          </div>
        </div>
        {playback && (
          <button className="play-route" onClick={() => setFrame(frame === null ? 0 : null)}>
            {frame === null ? <PlayIcon size={14} /> : <StopIcon size={12} />}
            {frame !== null ? 'Stop' : preview ? 'Preview route' : 'Replay run'}
          </button>
        )}
      </div>
      <RoutingDiagram source={source} organizer={display} tasks={tasks} states={tasks.map((_, i) => taskStatus(i))}
        active={active} reduced={reduced} />
      <div className="map-footer">
        <span>
          <RadioButtonIcon size={14} />
          {display}
        </span>
        <span>
          {active === 0
            ? source + ' → Organizer'
            : active !== undefined
              ? 'Organizer → ' + tasks[active - 1].title
              : 'One organizer · three packet tasks'}
        </span>
      </div>
    </section>
  )
}

type Props = {
  file: StaffFile
  staff: Staff
  queue: Summary[]
  audit: AuditEvent[]
  busy: boolean
  open: () => void
  select: (id: string) => void
  submit: Submit
}

function RequestResult({ file }: { file: StaffFile }) {
  const result = file.recommendation
  const stage = file.last_run?.status
  const pending = stage === 'pending'
  const stopped = stage && ['analysis_refused', 'analysis_unavailable', 'analysis_invalid', 'superseded'].includes(stage)
  if (!result && !pending && !stopped) return null
  const attention = result?.tone === 'attention' || stopped
  const Icon = pending ? ClockIcon : attention ? WarningCircleIcon : ArrowCircleUpRightIcon
  const amount = file.request_input?.amount_minor ?? file.amount_minor
  const currency = file.request_input?.currency || file.currency
  return <section className={'request-result ' + (pending ? 'processing' : attention ? 'attention' : 'review')} role="status">
    <span className="result-symbol"><Icon size={32} weight="duotone" /></span>
    <div className="result-body"><span className="result-label">{result ? 'Organizer recommendation' : pending ? 'Request received' : 'Organizer update'}</span>
      <h2>{result?.title || (pending ? 'Preparing your review packet' : runLabels[stage!] || 'Analysis stopped')}</h2>
      <p>{result?.guidance || (pending ? 'Follow the handoffs below while the agents check the file.' : 'This run produced no current recommendation. Open the case to review its status.')}</p>
      <div className="result-context"><span title={file.case_id}>{caseLabel(file.case_id)}</span><span>{file.request_input?.subject || file.workflow_title}</span>
        {currency && amount != null && <span>{money(amount, currency)}</span>}</div>
    </div></section>
}

export default function RequestDashboard({ file, staff, queue, audit, busy, open, select, submit }: Props) {
  const stats = [
    { name: 'Assigned requests', value: queue.length, icon: StackIcon },
    {
      name: 'In review',
      value: queue.filter((c) => c.status === 'in_review').length,
      icon: ClipboardTextIcon,
    },
    {
      name: 'On hold',
      value: queue.filter((c) => c.status === 'on_hold').length,
      icon: PauseCircleIcon,
    },
  ]
  const canRun = file.permitted_actions.includes('run') && file.last_run?.status !== 'pending'
  const incoming = audit.find((e) => e.action === 'case.opened')
  const history = [...audit].reverse()
  const [allEvents, setAllEvents] = useState(false)
  return (
    <div className="tracker">
      <div className="tracker-title">
        <div>
          <div className="tracker-edition">
            <BroadcastIcon size={14} />
            {file.department_case?.local_only ? 'Bank-only workflow' : file.configured_mode === 'fixture' ? 'Fixture mode' : 'Live mode'}
          </div>
          <h1>Agent operations</h1>
        </div>
        <button className="case-link" onClick={open}>
          Open case <ArrowUpRightIcon size={15} />
        </button>
      </div>
      <RequestResult file={file} />
      <div className="tracker-summary">
        <div className="tracker-stats">
          {stats.map((s) => (
            <div className="trk-stat" key={s.name}>
              <span className="metric-icon">
                <s.icon weight="duotone" />
              </span>
              <div>
                <small>{s.name}</small>
                <strong>{s.value}</strong>
              </div>
            </div>
          ))}
        </div>
        <div className="handoff-strip">
          <span className="handoff-icon">
            <GitBranchIcon size={19} />
          </span>
          <div>
            <small>Next handoff</small>
            <p>{file.last_run?.status === 'pending' ? 'The organizer is preparing the three review packets.' : file.next_action}</p>
            {canRun && !file.analysis_available && <p>The configured analysis service is unavailable.</p>}
          </div>
          {canRun && (
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                submit(
                  '/runs',
                  { revision: file.revision, mode: file.configured_mode },
                  'Analysis run submitted.',
                )
              }
            >
              <PlayIcon size={14} /> Run analysis
            </button>
          )}
        </div>
      </div>
      <RouteMap key={file.case_id + file.revision} file={file} audit={audit} />
      <div className="tracker-lower">
        <div className="tracker-stack">
          <section className="track-panel">
            <div className="panel-title">
              <div className="track-heading">
                <TrayIcon size={18} />
                <h2>Request queue</h2>
              </div>
              <small>{queue.length} assigned</small>
            </div>
            {queue.map((c) => (
              <button
                key={c.case_id}
                className={'tracked-request' + (c.case_id === file.case_id ? ' current' : '')}
                disabled={busy}
                aria-pressed={c.case_id === file.case_id}
                onClick={() => select(c.case_id)}
              >
                <span className="request-icon">
                  <ArrowDownLeftIcon size={17} />
                </span>
                <span>
                  <strong title={c.case_id}>{caseLabel(c.case_id)}</strong>
                  <small>
                    {c.currency && c.amount_minor != null ? money(c.amount_minor, c.currency) : c.case_title} · Rev. {c.revision}
                  </small>
                </span>
                <span className={'pill ' + c.status}>{label(c.status)}</span>
                <ArrowRightIcon size={14} />
              </button>
            ))}
            {incoming && (
              <p className="tracker-foot">
                <BriefcaseIcon size={13} /> {caseLabel(file.case_id)} originated at {deskName(file, incoming.desk)}.
              </p>
            )}
          </section>
          <section className="track-panel">
            <div className="panel-title">
              <div className="track-heading">
                <ShieldCheckIcon size={18} />
                <h2>Human review</h2>
              </div>
              <small>Revision {file.revision}</small>
            </div>
            {(file.department_case?.reviewers || desks).map((d) => {
              const finding = file.reviews.find((r) => r.desk === d)
              const disposition = file.holds.some((h) => h.desk === d)
                ? 'hold'
                : (finding?.disposition ?? 'pending')
              return (
                <div className="desk-disposition" key={d}>
                  {deskName(file, d)}
                  <span className={'pill ' + disposition}>
                    {disposition === 'clear' && <CheckIcon size={12} />} {label(disposition)}
                  </span>
                </div>
              )
            })}
            {file.requests.length > 0 && (
              <div className="visible-requests">
                <h3>Desk requests</h3>
                {file.requests.map((r) => (
                  <p key={r.request_id}>
                    <span>
                      {label(r.from_desk)} → {label(r.to_desk)}
                    </span>
                    <small>{label(r.status)}</small>
                  </p>
                ))}
              </div>
            )}
          </section>
        </div>
        <section className="track-panel feed">
          <div className="panel-title">
            <div className="track-heading">
              <PulseIcon size={18} />
              <h2>Activity stream</h2>
            </div>
            <small>UTC</small>
          </div>
          <ol>
            {(allEvents ? history : history.slice(0, 5)).map((e) => (
              <li key={e.event_id}>
                <span className={'feed-dot ' + (e.desk === 'analysis' ? 'automated' : '')}>
                  {e.desk === 'analysis' ? <CpuIcon size={13} /> : <ClockIcon size={13} />}
                </span>
                <div>
                  <strong>{eventName(e.action)}</strong>
                  <small>
                    {e.desk === 'analysis' ? 'Organizer' : deskName(file, e.desk)} · Rev. {e.revision}
                  </small>
                </div>
                <time dateTime={e.timestamp}>
                  {new Date(e.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC' })}
                </time>
              </li>
            ))}
          </ol>
          {!history.length && <p className="tracker-foot">No visible activity yet.</p>}
          {history.length > 5 && (
            <button className="stream-more" onClick={() => setAllEvents((v) => !v)}>
              <ArrowCounterClockwiseIcon size={13} />
              {allEvents ? 'Show latest five' : 'Show all ' + history.length + ' events'}
            </button>
          )}
          <p className="tracker-foot">
            <RadioButtonIcon size={12} /> Visible to {deskName(file, staff.role)}
          </p>
        </section>
      </div>
    </div>
  )
}
