import { createRoot } from 'react-dom/client'
import { IconContext } from '@phosphor-icons/react'
import './styles.css'
import App from './App'
import { spinGlobe } from './launch-globe'

// The artwork paints from the HTML while React and the desk directory load.
// An arriving keyboard or pointer user can interact with the workspace immediately.
const curtain = document.getElementById('launch-curtain')
if (curtain) {
  const listeners = new AbortController()
  const globe = curtain.querySelector('canvas')
  if (globe) spinGlobe(globe, listeners.signal)
  const dismiss = () => {
    curtain.remove()
    listeners.abort()
    window.clearTimeout(fallback)
  }
  const fallback = window.setTimeout(dismiss, 3000)
  curtain.addEventListener('animationend', event => {
    if (event.target === curtain) dismiss()
  }, { signal: listeners.signal })
  window.addEventListener('keydown', dismiss, { capture: true, signal: listeners.signal })
  window.addEventListener('pointerdown', dismiss, { capture: true, signal: listeners.signal })
}

createRoot(document.getElementById('root')!).render(
  <IconContext.Provider value={{ size: 20, weight: 'regular', 'aria-hidden': true }}>
    <App />
  </IconContext.Provider>,
)
