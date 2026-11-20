import { label, money, type DeskPacket, type Source } from './api'

function Reference({ refId, sources }: { refId: string; sources: Source[] }) {
  const source = sources.find(item => item.ref === refId)
  if (!source) return <span className="withheld">{refId} · Detail withheld</span>
  return <details className="reference">
    <summary>{source.label} <code>{source.ref}</code></summary>
    <p>{source.detail}</p>
  </details>
}

const questions: Record<string, { text: string; owner: string }> = {
  supplier_invoice: { text: 'Supply the supplier invoice for this instrument.', owner: 'Coverage' },
  facility_snapshot: { text: 'Verify the current facility amount, currency and expiry.', owner: 'Credit Risk' },
}

export default function PacketList({ packets, sources, currency, mode }: {
  packets: DeskPacket[]; sources: Source[]; currency: string; mode: string | null
}) {
  return <section className="card">
    <div className="card-head"><h2>Review packets</h2>
      {mode && <span className="quiet">{mode === 'live' ? 'Live · BRANE' : 'Fixture · synthetic'}</span>}
    </div>
    {!packets.length && <p className="muted">No sealed draft is available to your desk for this revision.</p>}
    {packets.map(packet => <details className="packet" key={packet.desk}>
      <summary>{label(packet.desk)} <span>Draft</span></summary>
      <p>{packet.summary}</p>
      {packet.facts.map(fact => <div className="fact" key={fact.field}>
        <span>{label(fact.field.replace(/_minor$/, ''))}</span>
        <strong>{typeof fact.value === 'number' && fact.field.endsWith('_minor') ? money(fact.value, currency) : String(fact.value)}</strong>
        <Reference refId={fact.source_ref} sources={sources} />
      </div>)}
      {[...new Set([...packet.policy_refs, ...packet.evidence_refs])].map(ref => <Reference key={ref} refId={ref} sources={sources} />)}
      {packet.missing_items.length > 0 && <>
        <strong>Outstanding evidence</strong>
        <ul>{packet.missing_items.map(item => <li key={item}>
          {questions[item] ? <>{questions[item].text} <strong>Owner · {questions[item].owner}</strong></> : label(item)}
        </li>)}</ul>
      </>}
      {packet.limitations?.map(item => <p className="muted" key={item}>{item}</p>)}
    </details>)}
  </section>
}
