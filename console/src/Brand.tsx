import {
  ChartBarIcon, FilesIcon, FolderOpenIcon, HandshakeIcon, PackageIcon,
  ScalesIcon, ShieldCheckIcon, type Icon,
} from '@phosphor-icons/react'

const deskIcons: Record<string, Icon> = {
  coverage: HandshakeIcon,
  trade_finance: FilesIcon,
  credit_risk: ChartBarIcon,
  compliance: ShieldCheckIcon,
  final_officer: ScalesIcon,
  operations: PackageIcon,
}

export function DeskIcon({ role, size = 24 }: { role: string; size?: number }) {
  const Icon = deskIcons[role] ?? FolderOpenIcon
  return <Icon size={size} weight="duotone" aria-hidden="true" />
}

export function Brand() {
  return <div className="brand"><img src={import.meta.env.BASE_URL + 'redwood.svg'} alt="" width="32" height="32" />Redwood</div>
}
