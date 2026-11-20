import {
  ChartBarIcon, FilesIcon, FolderOpenIcon, HandshakeIcon, PackageIcon,
  ScalesIcon, ShieldCheckIcon, BankIcon, BuildingsIcon, CurrencyCircleDollarIcon,
  ChartLineIcon, UsersThreeIcon, FileMagnifyingGlassIcon, NetworkIcon, BriefcaseIcon,
  IdentificationCardIcon, ClipboardTextIcon, NewspaperIcon, MagnifyingGlassIcon, type Icon,
} from '@phosphor-icons/react'

const deskIcons: Record<string, Icon> = {
  coverage: HandshakeIcon,
  trade_finance: FilesIcon,
  credit_risk: ChartBarIcon,
  compliance: ShieldCheckIcon,
  final_officer: ScalesIcon,
  operations: PackageIcon,
  dept_rm: HandshakeIcon, dept_uw: BankIcon, dept_syn: BuildingsIcon, dept_ls: FilesIcon,
  dept_pay: CurrencyCircleDollarIcon, dept_doc: FileMagnifyingGlassIcon, dept_fx: ChartLineIcon,
  dept_col: ScalesIcon, dept_cus: ShieldCheckIcon, dept_ma: BriefcaseIcon, dept_res: NewspaperIcon,
  dept_ccr: ChartBarIcon, dept_mr: ChartLineIcon, dept_mod: NetworkIcon, dept_orm: ClipboardTextIcon,
  dept_tre: BankIcon, dept_kyc: IdentificationCardIcon, dept_aml: MagnifyingGlassIcon, dept_leg: ScalesIcon,
  dept_sur: FileMagnifyingGlassIcon, dept_aud: ClipboardTextIcon, dept_fin: CurrencyCircleDollarIcon,
  dept_ict: NetworkIcon, dept_hr: UsersThreeIcon, dept_buy: PackageIcon, dept_exe: BuildingsIcon,
}

export function DeskIcon({ role, size = 24 }: { role: string; size?: number }) {
  const Icon = deskIcons[role.replace(/_head$/, '')] ?? FolderOpenIcon
  return <Icon size={size} weight="duotone" aria-hidden="true" />
}

export function Brand() {
  return <div className="brand"><img src={import.meta.env.BASE_URL + 'redwood.svg'} alt="" width="32" height="32" />Redwood</div>
}
