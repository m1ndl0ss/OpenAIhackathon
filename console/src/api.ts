export interface Staff {
  role_label?: string | null
  desk_picker: boolean
  id: string
  name: string
  configured_mode: 'live' | 'fixture'
  analysis_available: boolean
  role: string
  customer_ref: string
}

export interface Summary {
  my_approval?: 'review' | 'decision' | null
  case_id: string
  customer_ref: string
  revision: number
  status: string
  next_action: string
  workflow_id: string
  workflow_title: string
  department: string
  definition_version: number
  case_title: string
  amount_minor: number | null
  currency: string | null
}

export type StaffContact = Pick<Staff, 'id' | 'name' | 'role'>
export interface ApprovalRecipient extends StaffContact {
  status: 'not_sent' | 'awaiting' | 'signed' | 'hold' | 'waiting' | 'approve' | 'decline' | 'refer'
  sent_at: string | null
}
export interface HumanApproval {
  reviewers: ApprovalRecipient[]
  final: ApprovalRecipient
  can_send: boolean
  stage: 'preparing' | 'other_mode' | 'ready' | 'review' | 'decision' | 'closed'
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
    model_calls: number
    tool_reads: number
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
export interface FileBase extends Summary {
  human_approval?: HumanApproval
  request_input?: RequestValues | null
  recommendation?: { tone: 'review' | 'attention'; title: string; guidance: string } | null
  packet_hash: string | null
  as_of: string
  mode: string | null
  configured_mode: 'live' | 'fixture'
  analysis_available: boolean
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
export interface CaseFile extends FileBase {
  department_case?: undefined
  currency: string
  amount_minor: number
  facility_ref: string
  expiry: string
  invoice_ref: string | null
  invoice_document_id: string
  within_mandate: boolean
  mandate_currency: string
  mandate_minor: number | null
  headroom_after_minor: number | null
}
export interface DepartmentFile extends FileBase {
  department_case: {
    examples: string[]
    analyst: string
    approver: string
    reviewers: string[]
    role_labels: Record<string, string>
    local_only: boolean
    evidence_verified: boolean
    source: string
    outcome: string
  }
}
export type StaffFile = CaseFile | DepartmentFile

export function caseLabel(id: string) {
  const generated = /^([A-Z]+)-([0-9a-f]{8})[0-9a-f]{24}$/.exec(id)
  return generated ? generated[1] + '-' + generated[2].toUpperCase() : id
}

export interface RequestValues {
  subject: string
  context: string
  reference: string
  requested_date: string
  amount_minor: number | null
  currency: string | null
  notes: string
}
export interface RequestType {
  id: string
  code: string
  group: string
  title: string
  desk: string
  owner_role: string
  desk_id: string
  decision_desk: string
  reviewers: StaffContact[]
  final: StaffContact
  context_label: string
  source_label: string
  date_label: string
  min_date: string
  amount_label: string | null
  currencies: string[]
  examples: RequestValues[]
}
export type StaffSession = { staff: Staff; token: string }
export function deskName(file: StaffFile, role: string) {
  return file.department_case?.role_labels[role] || label(role)
}
export interface Department {
  id: string
  group: string
  desk: string
  workflow: string
  code: string
  outcome: string
  analyst: { id: string; name: string }
  approver: { id: string; name: string }
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
  evidence: 'Evidence review', policy: 'Policy review', handover: 'Handover draft', completed: 'Completed',
  coverage: 'Coverage', trade_finance: 'Trade Finance', credit_risk: 'Credit Risk', compliance: 'Compliance',
  final_officer: 'Mandated officer', operations: 'Operations', issued_simulated: 'Issued · simulated',
  preparing: 'Preparing file', ready_for_review: 'Ready to send', in_review: 'In review', on_hold: 'On hold', ready_for_decision: 'Ready for decision',
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
