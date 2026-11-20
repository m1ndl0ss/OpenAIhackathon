// Orthographic projection of an original dotted globe. All artwork stays in the page.
export function spinGlobe(canvas: HTMLCanvasElement, signal: AbortSignal) {
  const ctx = canvas.getContext('2d')
  if (!ctx || matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const scale = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = 286 * scale; canvas.height = 206 * scale
  ctx.scale(scale, scale)
  const rad = Math.PI / 180
  // Coarse land silhouettes, sampled once as points in geographic coordinates.
  const outlines = [
    [[-164,66],[-126,72],[-94,74],[-59,55],[-78,47],[-80,29],[-98,18],[-108,27],[-124,36],[-131,53]],
    [[-81,12],[-64,11],[-36,-6],[-43,-23],[-68,-55],[-75,-37],[-79,-4]],
    [[-58,60],[-46,82],[-21,78],[-30,65]],
    [[-12,36],[-10,44],[7,58],[23,71],[36,64],[43,53],[52,56],[68,65],[111,75],[169,65],[162,51],[140,45],[123,30],[106,16],[100,5],[88,23],[76,8],[65,25],[52,27],[40,17],[28,34],[14,36]],
    [[-17,32],[1,36],[32,31],[43,12],[51,12],[39,-10],[32,-30],[17,-35],[9,-17],[9,-2],[-14,6]],
    [[112,-22],[126,-13],[139,-15],[144,-12],[154,-26],[147,-39],[128,-33],[115,-35]],
  ]
  function inside(lon: number, lat: number, shape: number[][]) {
    let result = false
    for (let i = 0, j = shape.length - 1; i < shape.length; j = i++) {
      const [x, y] = shape[i], [u, v] = shape[j]
      if ((y > lat) !== (v > lat) && lon < (u - x) * (lat - y) / (v - y) + x) result = !result
    }
    return result
  }
  const land: number[][] = []
  for (let lat = -56; lat <= 80; lat += 4) {
    for (let lon = -178; lon < 180; lon += 4 / Math.cos(lat * rad)) {
      if (outlines.some(poly => inside(lon, lat, poly))) land.push([lon, lat])
    }
  }
  const meridians = Array.from({length: 12}, (_, i) => Array.from({length: 61}, (_, j) => [i * 30, -90 + j * 3]))
  const parallels = Array.from({length: 7}, (_, i) => Array.from({length: 121}, (_, j) => [j * 3, -67.5 + i * 22.5]))
  const grid = [...meridians, ...parallels]
  const sites = [[4.9, 52.4], [-74, 40.7], [103.8, 1.4], [55.3, 25.2]]
  const tilt = 17 * rad, roll = -.19, start = performance.now()
  let frame = 0
  function draw(time: number) {
    if (!ctx || signal.aborted) return
    const angle = -34 + (time - start) * .049
    function project(lon: number, lat: number) {
      const a = (lon + angle) * rad, b = lat * rad
      const x = Math.cos(b) * Math.sin(a), z = Math.cos(b) * Math.cos(a)
      const y = Math.sin(b) * Math.cos(tilt) - z * Math.sin(tilt)
      return [143 + 83 * (x * Math.cos(roll) - y * Math.sin(roll)), 103 - 83 * (x * Math.sin(roll) + y * Math.cos(roll)), Math.sin(b) * Math.sin(tilt) + z * Math.cos(tilt)]
    }
    ctx.clearRect(0, 0, 286, 206)
    ctx.beginPath(); ctx.arc(143, 103, 83, 0, 2 * Math.PI); ctx.fillStyle = '#f0f4e9'; ctx.fill(); ctx.strokeStyle = '#8c9e8b'; ctx.lineWidth = .8; ctx.stroke()
    ctx.strokeStyle = '#b5c2ac'; ctx.lineWidth = .58; ctx.beginPath()
    for (const line of grid) {
      let pen = false
      for (const [lon, lat] of line) {
        const [x, y, z] = project(lon, lat)
        if (z > 0) { if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y) }
        pen = z > 0
      }
    }
    ctx.stroke(); ctx.fillStyle = '#5d7c68'; ctx.beginPath()
    for (const [lon, lat] of land) {
      const [x, y, z] = project(lon, lat)
      if (z > .03) { const r = .6 + z * .55; ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, 2 * Math.PI) }
    }
    ctx.fill()
    for (const [lon, lat] of sites) {
      const [x, y, z] = project(lon, lat)
      if (z <= .05) continue
      ctx.beginPath(); ctx.arc(x, y, 4.6, 0, 2 * Math.PI); ctx.fillStyle = '#f9d8b7'; ctx.fill()
      ctx.beginPath(); ctx.arc(x, y, 2.6, 0, 2 * Math.PI); ctx.fillStyle = '#c95126'; ctx.fill()
    }
    frame = requestAnimationFrame(draw)
  }
  draw(start); canvas.classList.add('painted')
  signal.addEventListener('abort', () => cancelAnimationFrame(frame), { once: true })
}
