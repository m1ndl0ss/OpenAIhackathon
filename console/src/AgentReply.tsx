import { ChatTeardropTextIcon, ClockIcon, FileTextIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { caseLabel, label, money, type StaffFile } from './api'

const responseStatus: Record<string, string> = {
  pending: 'The organizer is checking the request. The reply will appear here.',
  analysis_refused: 'BRANE declined this request. Review it internally.',
  analysis_invalid: 'The response failed validation. Check the evidence and run the analysis again.',
  analysis_unavailable: 'The analysis service was unavailable. You can retry this revision.',
  unavailable: 'The analysis service was unavailable. You can retry this revision.',
  failed: 'Analysis stopped before the response was ready. Check the case and retry.',
  superseded: 'The evidence changed during analysis. Run the current revision for a new reply.',
  revised: 'The evidence has changed. Run analysis on this revision to get an updated recommendation.',
  other_mode: 'This revision was analyzed in a different mode. Open a new request in the current mode to get a reply.',
}

export default function AgentReply({ file }: { file: StaffFile }) {
  const reply = file.recommendation
  const run = file.last_run
  if (!reply) {
    const status = run && run.mode !== file.configured_mode ? 'other_mode'
      : run?.status || (file.revision > 1 && !file.packet_hash ? 'revised' : '')
    if (!responseStatus[status]) return null
    const pending = status === 'pending'
    const Icon = pending ? ClockIcon : WarningCircleIcon
    return <section id="agent-reply" tabIndex={-1} className={'request-result ' + (pending ? 'processing' : 'attention')} aria-label="Agent response status">
      <span className="result-symbol"><Icon size={26} /></span>
      <div role="status"><h2>{pending ? 'Waiting for the agent reply…' : 'No agent reply'}</h2>
        <p>{responseStatus[status]}</p></div>
    </section>
  }

  const provenance = file.department_case?.local_only ? 'Bank-local rules' : file.mode === 'live' ? 'Live via BRANE' : 'Fixture run'
  const otherDrafts = file.packets.filter(packet => packet.desk !== reply.agent)
  const citedRefs = new Set([...reply.source_refs, ...otherDrafts.flatMap(packet => [...packet.evidence_refs, ...packet.policy_refs])])
  const sources = file.sources.filter(source => citedRefs.has(source.ref))
  const record = file.department_case ? sources.find(source => source.label === file.department_case?.source)
    : sources.find(source => source.ref === file.invoice_ref)
  const headroom = file.department_case ? null : file.headroom_after_minor
  const currency = file.currency
  const amount = file.amount_minor
  const original = file.human_approval?.reviewers.some(person => person.sent_at)
  return <section id="agent-reply" className={'request-result ' + reply.tone} aria-labelledby="reply-heading" tabIndex={-1}>
    <div className="reply-heading">
      <span className="result-symbol"><ChatTeardropTextIcon size={26} weight="duotone" /></span>
      <h2 id="reply-heading">Agent reply</h2><span className="reply-mode">{provenance}</span>
    </div>
    <div className="reply-context"><span>{file.case_title}</span>{currency && amount != null && <strong>{money(amount, currency)}</strong>}</div>
    <div className="reply-message" role="status">
      <p className="reply-caption">{original ? 'Original recommendation' : 'Recommended next step'} · Revision {reply.revision}</p>
      <h3>{reply.title}</h3>
      <blockquote>{reply.guidance}</blockquote>
      {record && <p><strong>{record.label}</strong> · {record.detail}</p>}
      {currency && headroom != null && <p>{headroom < 0
        ? <>The proposed issuance exceeds facility capacity by <strong>{money(-headroom, currency)}</strong>.</>
        : <>The proposed issuance would leave <strong>{money(headroom, currency)}</strong> in the facility.</>}</p>}
      {file.department_case === undefined && !file.within_mandate && <p>The request falls outside the final officer’s mandate.</p>}
    </div>
    <details className="reply-evidence" key={reply.run_id}>
      <summary><FileTextIcon size={16} />Review findings and sources</summary>
      <div className="reply-record">
        <p className="reply-meta">{label(reply.agent)} agent · {caseLabel(file.case_id)} · Revision {reply.revision} · <time dateTime={reply.sealed_at}>{new Date(reply.sealed_at).toLocaleString()}</time></p>
        {otherDrafts.map(packet => <p key={packet.desk}><strong>{label(packet.desk)} agent</strong> {packet.summary}</p>)}
        <ul aria-label="Cited sources">{sources.map(source =>
          <li key={source.ref}><strong>{source.label}</strong> · {source.detail} <code>{source.ref}</code></li>)}</ul>
      </div>
    </details>
  </section>
}
