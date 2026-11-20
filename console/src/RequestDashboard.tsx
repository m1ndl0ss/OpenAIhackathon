import { useEffect, useState, type CSSProperties } from 'react'
import {
  Activity,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Bot,
  BriefcaseBusiness,
  ChartNoAxesColumnIncreasing,
  Check,
  CircleDot,
  ClipboardList,
  Clock3,
  FileCheck2,
  GitBranch,
  Inbox,
  Layers3,
  Network,
  OctagonPause,
  Play,
  Radio,
  RotateCcw,
  ShieldCheck,
  Square,
  Waypoints,
} from 'lucide-react'
import {
  desks,
  label,
  money,
  type AuditEvent,
  type CaseFile,
  type Staff,
  type Summary,
  type Submit,
} from './api'
import './tracker.css'

const tasks = [
  { desk: 'trade_finance', title: 'Trade Finance', icon: FileCheck2, tint: '#9fb8ff' },
  { desk: 'credit_risk', title: 'Credit Risk', icon: ChartNoAxesColumnIncreasing, tint: '#b8a0ef' },
  { desk: 'compliance', title: 'Compliance', icon: ShieldCheck, tint: '#84cfaf' },
]
const originColor = '#91bfdc'
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
  ['M 432 151 C 580 151 540 54 706 54 H 816', 'M670 82 C670 150 166 124 166 219'],
  ['M 432 151 H 816', 'M670 82 C670 160 500 145 500 219'],
  ['M 432 151 C 580 151 540 248 706 248 H 816', 'M670 82 C670 148 833 143 833 219'],
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
        const color = i === 0 ? originColor : tasks[i - 1].tint
        return (
          <g key={i}>
            <path
              d={path}
              fill="none"
              stroke={color}
              strokeOpacity={active === i ? '.88' : '.5'}
              strokeWidth={active === i ? 2 : 1.4}
              vectorEffect="non-scaling-stroke"
            />
            {active === i && (
              <g className="flying-packet" key={path}>
                <animateMotion dur="1.6s" path={path} repeatCount="indefinite" />
                <ellipse rx="23" ry="13" fill={color} opacity=".19" />
                <rect
                  x="-11"
                  y="-7"
                  width="22"
                  height="14"
                  rx="3"
                  stroke={color}
                  fill="#20232a"
                  strokeWidth="2.2"
                />
                <path d="M-9 -5 L0 1 L9 -5" fill="none" stroke={color} strokeWidth="2" />
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

function RouteMap({ file, audit }: { file: CaseFile; audit: AuditEvent[] }) {
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
  const source = label(sender ?? origin?.desk ?? 'unknown')
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
            <Waypoints />
          </span>
          <div>
            <h2>Request routing</h2>
            <p>
              {file.case_id} <span>·</span> Import letter of credit
            </p>
          </div>
        </div>
        {playback && (
          <button className="play-route" onClick={() => setFrame(frame === null ? 0 : null)}>
            {frame === null ? <Play size={14} /> : <Square size={12} />}
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
              <Inbox />
            </div>
            <strong>{source}</strong>
            <small>Request source</small>
          </div>
          <div className={'hub-node' + (active !== undefined ? ' energized' : '')}>
            <div className="orbit">
              <div className="hub-core">
                <Network />
              </div>
            </div>
            <strong>Organizer</strong>
            <small>{hubState}</small>
          </div>
          {tasks.map((task, i) => (
            <div
              key={task.desk}
              className={'work-node node-' + i + (active === i + 1 ? ' energized' : '')}
              style={{ '--tint': task.tint } as CSSProperties}
            >
              <span className="worker-icon">
                <task.icon />
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
          <CircleDot size={14} />
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
  file: CaseFile
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
    { name: 'Assigned requests', value: queue.length, icon: Layers3, color: 'sky' },
    {
      name: 'In review',
      value: queue.filter((c) => c.status === 'in_review').length,
      icon: ClipboardList,
      color: 'violet',
    },
    {
      name: 'On hold',
      value: queue.filter((c) => c.status === 'on_hold').length,
      icon: OctagonPause,
      color: 'gold',
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
            <Radio size={14} />
            {file.configured_mode === 'fixture' ? 'Fixture mode' : 'Live mode'}
          </div>
          <h1>Agent operations</h1>
        </div>
        <button className="case-link" onClick={open}>
          Open case <ArrowUpRight size={15} />
        </button>
      </div>
      <div className="tracker-stats">
        {stats.map((s) => (
          <div className={'trk-stat ' + s.color} key={s.name}>
            <span className="metric-icon">
              <s.icon />
            </span>
            <div>
              <small>{s.name}</small>
              <strong>{s.value}</strong>
            </div>
          </div>
        ))}
      </div>
      <RouteMap key={file.case_id + file.revision} file={file} audit={audit} />
      <div className="handoff-strip">
        <span className="handoff-icon">
          <GitBranch size={19} />
        </span>
        <div>
          <small>Next handoff</small>
          <p>{file.next_action}</p>
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
            <Play size={14} /> Run analysis
          </button>
        )}
      </div>
      <div className="tracker-lower">
        <div className="tracker-stack">
          <section className="track-panel">
            <div className="panel-title">
              <div className="track-heading">
                <Inbox size={18} />
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
                  <ArrowDownLeft size={17} />
                </span>
                <span>
                  <strong>{c.case_id}</strong>
                  <small>
                    {money(c.amount_minor, c.currency)} · Rev. {c.revision}
                  </small>
                </span>
                <span className={'pill ' + c.status}>{label(c.status)}</span>
                <ArrowRight size={14} />
              </button>
            ))}
            {incoming && (
              <p className="tracker-foot">
                <BriefcaseBusiness size={13} /> {file.case_id} originated at {label(incoming.desk)}.
              </p>
            )}
          </section>
          <section className="track-panel">
            <div className="panel-title">
              <div className="track-heading">
                <ShieldCheck size={18} />
                <h2>Human review</h2>
              </div>
              <small>Revision {file.revision}</small>
            </div>
            {desks.map((d) => {
              const finding = file.reviews.find((r) => r.desk === d)
              const disposition = file.holds.some((h) => h.desk === d)
                ? 'hold'
                : (finding?.disposition ?? 'pending')
              return (
                <div className="desk-disposition" key={d}>
                  {label(d)}
                  <span className={'pill ' + disposition}>
                    {disposition === 'clear' && <Check size={12} />} {label(disposition)}
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
              <Activity size={18} />
              <h2>Activity stream</h2>
            </div>
            <small>UTC</small>
          </div>
          <ol>
            {(allEvents ? history : history.slice(0, 5)).map((e) => (
              <li key={e.event_id}>
                <span className={'feed-dot ' + (e.desk === 'analysis' ? 'automated' : '')}>
                  {e.desk === 'analysis' ? <Bot size={13} /> : <Clock3 size={13} />}
                </span>
                <div>
                  <strong>{eventName(e.action)}</strong>
                  <small>
                    {e.desk === 'analysis' ? 'Organizer' : label(e.desk)} · Rev. {e.revision}
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
              <RotateCcw size={13} />
              {allEvents ? 'Show latest five' : 'Show all ' + history.length + ' events'}
            </button>
          )}
          <p className="tracker-foot">
            <CircleDot size={12} /> Visible to {label(staff.role)}
          </p>
        </section>
      </div>
    </div>
  )
}
