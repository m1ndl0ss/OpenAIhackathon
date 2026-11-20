export interface Staff {
  desk_picker: boolean
  id: string
  name: string
  configured_mode: 'live' | 'fixture'
  analysis_available: boolean
  role: string
  customer_ref: string
}

export interface Summary {
  case_id: string
  customer_ref: string
  revision: number
  status: string
  next_action: string
  amount_minor: number
  currency: string
}

export interface Review {
  desk: string
  disposition: string
  event_id: string
  actor_id: string
  reason_code: string
  reason?: string
}
export interface Hold {
  hold_id: string
  desk: string
  reason_code: string
}
export interface DeskRequest {
  request_id: string
  from_desk: string
  to_desk: string
  question: string
  status: string
  blocking: boolean
  reply?: string
  evidence_ref?: string
}
export interface Source {
  ref: string
  label: string
  detail: string
}
export interface DeskPacket {
  desk: string
  summary: string
  facts: { field: string; value: string | number | boolean; source_ref: string }[]
  policy_refs: string[]
  evidence_refs: string[]
  missing_items: string[]
  suggested_next_step?: string
  limitations?: string[]
}
export interface AnalysisRun {
  run_id: string
  mode: 'fixture' | 'live'
  status: string
  analysis?: {
    policy_version: string
    observations: {
      task: string
      route: string
      model?: string | null
      policy_hash?: string | null
      log_ref?: string | null
      provider_request_id?: string | null
    }[]
  } | null
}
export interface CaseFile extends Summary {
  packet_hash: string | null
  facility_ref: string
  expiry: string
  as_of: string
  invoice_ref: string | null
  invoice_document_id: string
  within_mandate: boolean
  mandate_currency: string
  mode: string | null
  configured_mode: 'live' | 'fixture'
  analysis_available: boolean
  mandate_minor: number | null
  headroom_after_minor: number | null
  permitted_actions: string[]
  reviews: Review[]
  holds: Hold[]
  requests: DeskRequest[]
  packets: DeskPacket[]
  sources: Source[]
  receipt: { receipt_id: string; revision: number; actor_id: string } | null
  decision: { decision: string; revision: number; actor_id: string } | null
  last_run: AnalysisRun | null
}
export interface AuditEvent {
  sequence: number
  event_id: string
  revision: number
  actor_id: string
  desk: string
  action: string
  timestamp: string
  detail: unknown
}

export class BankError extends Error {
  constructor(message: string, readonly status: number, readonly requestId?: string) {
    super(message)
  }
}

export async function bank<T>(token: string | null, path: string, body?: object, key?: string): Promise<T> {
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = 'Bearer ' + token
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    headers['Idempotency-Key'] = key || crypto.randomUUID()
  }
  let response: Response
  try {
    response = await fetch('/v2/trade' + path, {
      method: body === undefined ? 'GET' : 'POST', headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store', credentials: 'omit', redirect: 'error',
    })
  } catch {
    throw new BankError('Could not reach the case service. Check the connection and try again.', 0)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const message = data?.message || (response.status === 401 ? 'The staff credential was rejected.' : 'The case service could not complete this request.')
    throw new BankError(message, response.status, data?.request_id)
  }
  if (data === null) throw new BankError('The case service returned an unreadable response. Refresh the case before retrying.', 502)
  return data as T
}

export function textError(error: unknown): string {
  if (error instanceof BankError && error.requestId) return error.message + ' · Ref ' + error.requestId
  return error instanceof Error ? error.message : 'The request could not be completed.'
}

export const desks = ['trade_finance', 'credit_risk', 'compliance']
export const roles = ['coverage', ...desks, 'final_officer', 'operations']
const labels: Record<string, string> = {
  coverage: 'Coverage', trade_finance: 'Trade Finance', credit_risk: 'Credit Risk', compliance: 'Compliance',
  final_officer: 'Mandated officer', operations: 'Operations', issued_simulated: 'Issued · simulated',
  preparing: 'Preparing file', in_review: 'In review', on_hold: 'On hold', ready_for_decision: 'Ready for decision',
  clear: 'Cleared', hold: 'On hold', unknown: 'Unknown', MANUAL_REVIEW: 'Manual review',
  DOCUMENT_REQUIRED: 'Invoice required', FACILITY_EXCEPTION: 'Facility exception', CHECKS_COMPLETE: 'Checks complete',
}
export function label(value: string): string {
  if (!value) return '—'
  if (labels[value]) return labels[value]
  const words = value.replace(/[_.]/g, ' ').toLowerCase()
  return words.charAt(0).toUpperCase() + words.slice(1)
}
export function money(minor: number | null, currency: string): string {
  if (minor == null) return 'Unavailable'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, currencyDisplay: 'code', minimumFractionDigits: minor % 100 ? 2 : 0 }).format(minor / 100)
}
export type Submit = (suffix: string, body: object, message: string) => Promise<boolean>
