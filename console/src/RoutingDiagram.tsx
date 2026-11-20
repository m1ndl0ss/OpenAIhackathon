import { useEffect, useRef, useState } from 'react'
import { CircuitryIcon, TrayIcon, type Icon } from '@phosphor-icons/react'
import './routing-diagram.css'

type Task = { desk: string; title: string; icon: Icon }
type Props = { source: string; organizer: string; tasks: Task[]; states: string[]; active?: number; reduced: boolean }
type Point = { x: number; y: number }

function MovingPacket({ path }: { path: string }) {
  const motion = useRef<SVGAnimateMotionElement>(null)
  useEffect(() => { motion.current?.beginElement() }, [path])
  return <g><animateMotion ref={motion} begin="indefinite" dur="1.55s" path={path} repeatCount="indefinite" />
    <circle r="8" fill="#f45b31" opacity=".17" /><circle r="4.3" fill="#dc4b24" /></g>
}

export default function RoutingDiagram({ source, organizer, tasks, states, active, reduced }: Props) {
  const board = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(720)
  useEffect(() => {
    const element = board.current
    if (!element) return
    const measure = () => setWidth(Math.max(1, element.clientWidth))
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  const narrow = width < 525
  const height = narrow ? 305 : 264
  const origin = { x: width * (narrow ? .23 : .13), y: narrow ? 59 : 121 }
  const hub = { x: width * (narrow ? .73 : .43), y: origin.y }
  const workers = tasks.map((_, i) => narrow ? { x: width * (i + .5) / 3, y: 204 } : { x: width * .70, y: 48 + i * 82 })
  const tracks = [`M ${origin.x},${origin.y} H ${hub.x}`, ...workers.map(p => narrow
    ? `M ${hub.x},${hub.y} C ${hub.x},168 ${p.x},136 ${p.x},${p.y}`
    : `M ${hub.x},${hub.y} C ${hub.x + width * .12},${hub.y} ${p.x - width * .12},${p.y} ${p.x},${p.y}`)]
  function caption(point: Point, title: string, status: string, worker: boolean) {
    const beside = worker && !narrow
    const w = beside ? width * .29 - 30 : narrow ? width / (worker ? 3 : 2) - 4 : width * .25
    const x = beside ? point.x + 30 : point.x - w / 2
    return <foreignObject x={x} y={beside ? point.y - 24 : point.y + (worker ? 27 : 42)} width={w} height={beside ? 50 : 75}>
      <div className={'route-caption' + (beside ? ' beside' : '')}><strong>{title}</strong><span>{status}</span></div></foreignObject>
  }
  return <div className="route-surface" ref={board}>
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img"
      aria-label={`Routing from ${source} to Organizer (${organizer}). ${tasks.map((t, i) => t.title + ': ' + states[i]).join('. ')}.`}>
      {tracks.map((path, i) => <g key={i}><path d={path} className={'route-line' + (i === active ? ' active' : '')} />
        {i === active && !reduced && <MovingPacket path={path} />}</g>)}
      <g transform={`translate(${origin.x} ${origin.y})`}><circle r="25" className="source-circle" /><TrayIcon x={-12} y={-12} size={24} weight="duotone" color="#883515" /></g>
      <g transform={`translate(${hub.x} ${hub.y})`}><circle r="35" className={'hub-halo' + (active !== undefined ? ' active' : '')} /><circle r="26" fill="#204438" />
        <CircuitryIcon x={-13} y={-13} size={26} weight="bold" color="#e7f4c7" /></g>
      {workers.map((p, i) => { const Glyph = tasks[i].icon
        return <g key={tasks[i].desk} transform={`translate(${p.x} ${p.y})`}><circle r="20" className={'worker-circle' + (active === i + 1 ? ' active' : '')} />
          <Glyph x={-10} y={-10} size={20} weight="duotone" color="#23513e" /></g> })}
      {caption(origin, source, 'Request source', false)}{caption(hub, 'Organizer', organizer, false)}
      {workers.map((p, i) => <g key={tasks[i].desk}>{caption(p, tasks[i].title, states[i], true)}</g>)}
    </svg>
  </div>
}
