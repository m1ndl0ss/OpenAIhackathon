import { randomBytes } from 'node:crypto'
import { writeFileSync } from 'node:fs'

// Vite publishes only console/dist. This key travels with the Python function.
writeFileSync(new URL('../backend/_public_demo.key', import.meta.url), randomBytes(32).toString('hex'), { mode: 0o600 })
