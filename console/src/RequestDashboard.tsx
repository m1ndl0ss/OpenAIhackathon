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
  CircuitryIcon,
  PauseCircleIcon,
  PlayIcon,
  BroadcastIcon,
  ArrowCounterClockwiseIcon,
  ShieldCheckIcon,
  StopIcon,
  FlowArrowIcon,
} from '@phosphor-icons/react'
import {
  desks,
  label,
  money,
  type AuditEvent,
  type StaffFile,
  deskName,
  type Staff,
  type Summary,
  type Submit,
} from './api'
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
const tracks = [
  ['M 132 151 H 432', 'M 200 82 H 670'],
  ['M432 151 H536 L633 54 H816', 'M670 82 V133 L626 151 H212 L166 170 V219'],
  ['M 432 151 H 816', 'M670 82 V145 L500 181 V219'],
  ['M432 151 H536 L633 248 H816', 'M670 82 V133 L716 151 H790 L833 170 V219'],
]

function LinkLayer({ narrow, active }: { narrow: boolean; active: number | undefined }) {
  return (
    <svg
      className={'route-lines ' + (narrow ? 'narrow-lines' : 'wide-lines')}
      viewBox="0 0 1000 300"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {tracks.map((paths, i) => {
        const path = paths[narrow ? 1 : 0]
        const color = active === i ? '#ff7041' : '#84887a'
        return (
          <g key={i}>
            <path
              d={path}
              fill="none"
              stroke={color}
              strokeOpacity={active === i ? 1 : .8}
              strokeWidth={active === i ? 2 : 1.4}
              vectorEffect="non-scaling-stroke"
            />
            {active === i && (
              <g className="flying-packet" key={path}>
                <animateMotion dur="1.6s" path={path} repeatCount="indefinite" />
                <rect x="-9" y="-10" width="18" height="20" rx="2" fill="#ff7041" />
                <path d="M-5 -3 H5 M-5 2 H3 M-5 6 H0" fill="none" stroke="#252720" strokeWidth="1.8" />
              </g>
            )}
          </g>
        )
      })}
    </svg>
  )
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
    setFrame(!reduced && playback && (file.configured_mode === 'fixture' || !preview) ? 0 : null)
  }, [run?.run_id, run?.status, reduced, playback, preview, file.configured_mode])
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
    if (stage === 'prepared' || run?.status === 'sealed') return 'Packet ready'
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
  const hubState = frame === null && run?.status === 'sealed' ? 'Completed' : display
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
              {file.case_id} <span>·</span> {file.workflow_title}
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
      <div className="route-board">
        <div className="route-stage">
          <LinkLayer key={'wide-' + active} narrow={false} active={reduced ? undefined : active} />
          <LinkLayer key={'narrow-' + active} narrow active={reduced ? undefined : active} />
          <div className="origin-node">
            <div className="origin-icon">
              <TrayIcon weight="duotone" />
            </div>
            <strong>{source}</strong>
            <small>Request source</small>
          </div>
          <div className={'hub-node' + (active !== undefined ? ' energized' : '')}>
            <div className="orbit">
              <div className="hub-core">
                <CircuitryIcon weight="bold" />
              </div>
            </div>
            <strong>Organizer</strong>
            <small>{hubState}</small>
          </div>
          {tasks.map((task, i) => (
            <div
              key={task.desk}
              className={'work-node node-' + i + (active === i + 1 ? ' energized' : '')}
            >
              <span className="worker-icon">
                <task.icon weight="duotone" />
              </span>
              <div>
                <strong>{task.title}</strong>
                <small>{taskStatus(i)}</small>
              </div>
            </div>
          ))}
        </div>
      </div>
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
                  <strong>{c.case_id}</strong>
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
                <BriefcaseIcon size={13} /> {file.case_id} originated at {deskName(file, incoming.desk)}.
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
