import { label, money, type DeskPacket, type Source } from './api'

function Reference({ refId, sources }: { refId: string; sources: Source[] }) {
  const source = sources.find(item => item.ref === refId)
  if (!source) return <span className="withheld">{refId} · Detail withheld</span>
  return <details className="reference">
    <summary>{source.label} <code>{source.ref}</code></summary>
    <p>{source.detail}</p>
  </details>
}

export default function PacketList({ packets, sources, currency }: { packets: DeskPacket[]; sources: Source[]; currency: string }) {
  return <section className="card">
    <h2>Review packets</h2>
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
      {packet.missing_items.length > 0 && <p><strong>Outstanding</strong> · {packet.missing_items.map(label).join(', ')}</p>}
      {packet.limitations?.map(item => <p className="muted" key={item}>{item}</p>)}
    </details>)}
  </section>
}
