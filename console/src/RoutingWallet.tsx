import { useLayoutEffect, useRef, useState } from 'react'
import { CircuitryIcon, TrayIcon, type Icon } from '@phosphor-icons/react'
import './routing-wallet.css'

type Task = { desk: string; title: string; icon: Icon }
type Props = {
  source: string
  tasks: Task[]
  states: string[]
  prepared: number
  active?: number
  reduced: boolean
}

const metals = ['#f2b176', '#e5c78e', '#adcfb5', '#eea17d']

export default function RoutingWallet({ source, tasks, states, prepared, active, reduced }: Props) {
  const board = useRef<HTMLDivElement>(null)
  const [paths, setPaths] = useState<string[]>([])

  useLayoutEffect(() => {
    const stage = board.current
    if (!stage) return
    const origin = stage.querySelector<HTMLElement>('.wallet-source')!
    const hub = stage.querySelector<HTMLElement>('.wallet-card')!
    const coins = Array.from(stage.querySelectorAll<HTMLElement>('.desk-coin'))
    function measure() {
      const bounds = stage!.getBoundingClientRect()
      const from = origin.getBoundingClientRect()
      const card = hub.getBoundingClientRect()
      const cx = card.left + card.width / 2 - bounds.left
      const cardY = card.top + card.height / 2 - bounds.top
      const bottom = card.bottom - bounds.top - 1
      const originX = from.left + from.width / 2 - bounds.left
      let incoming: string
      if (Math.abs(cx - originX) < 5) {
        incoming = `M ${cx} ${from.bottom - bounds.top} V ${card.top - bounds.top}`
      } else {
        const start = from.right - bounds.left
        const end = card.left - bounds.left
        const bend = (start + end) / 2
        const y = from.top + from.height / 2 - bounds.top
        incoming = `M ${start} ${y} C ${bend} ${y}, ${bend} ${cardY}, ${end} ${cardY}`
      }
      const branches = coins.map(coin => {
        const box = coin.getBoundingClientRect()
        const x = box.left + box.width / 2 - bounds.left
        const y = box.top - bounds.top + 2
        const bend = bottom + (y - bottom) * .55
        return `M ${cx} ${bottom} C ${cx} ${bend}, ${x} ${bend}, ${x} ${y}`
      })
      setPaths([incoming, ...branches])
    }
    measure()
    const observer = new ResizeObserver(measure)
    for (const element of [stage, origin, hub, ...coins]) observer.observe(element)
    return () => observer.disconnect()
  }, [tasks, source])

  return <div className="wallet-board" ref={board} role="group" aria-label="Agent request routing">
    <svg className="wallet-rails" aria-hidden="true" width="100%" height="100%">
      {paths.map((path, i) => <path key={i} d={path} className={active === i ? 'current-rail' : undefined}
        style={active === i ? { stroke: metals[i] } : undefined} />)}
      {active !== undefined && paths[active] && !reduced && <g key={active + paths[active]}>
        <animateMotion dur="1.6s" repeatCount="indefinite" path={paths[active]}
          calcMode="spline" keyTimes="0;1" keyPoints="0;1" keySplines=".35 0 .25 1" />
        <g className="travelling-coin">
          <circle cy="1.6" r="9" fill="#392e22" stroke="#171b15" />
          <circle r="8.6" fill={metals[active]} stroke="#fff0cb" strokeWidth="1.1" />
          <circle r="6.5" fill="none" stroke="#796342" strokeWidth=".8" />
          <path d="m-3.4 1 3.4-4 3.4 4m-6.8 2.3L0-.7l3.4 4" fill="none" stroke="#584b35" strokeWidth="1.25" />
        </g>
      </g>}
    </svg>
    <div className={'wallet-source' + (active === 0 ? ' is-active' : '')}>
      <span className="source-seal"><TrayIcon weight="duotone" size={20} /></span>
      <div><small>Request from</small><strong>{source}</strong></div>
    </div>
    <div className={'wallet-card' + (active !== undefined ? ' is-active' : '')}>
      <div className="wallet-face">
        <strong className="wallet-owner"><CircuitryIcon size={17} /> Organizer</strong>
        <div className="wallet-balance"><b>{prepared}<span> / {tasks.length}</span></b><small>Tasks prepared</small></div>
        <span className="wallet-clasp" aria-hidden="true"><i /></span>
      </div>
    </div>
    <div className="wallet-desks">{tasks.map((task, i) =>
      <div key={task.desk} className={'wallet-desk' + (active === i + 1 ? ' is-active' : '')}>
        <span className="desk-coin"><span className="coin-face"><task.icon size={22} weight="bold" /></span></span>
        <strong>{task.title}</strong><small>{states[i]}</small>
      </div>
    )}</div>
  </div>
}
