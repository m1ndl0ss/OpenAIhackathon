import { createRoot } from 'react-dom/client'
import { IconContext } from '@phosphor-icons/react'
import './styles.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <IconContext.Provider value={{ size: 20, weight: 'regular', 'aria-hidden': true }}>
    <App />
  </IconContext.Provider>,
)
