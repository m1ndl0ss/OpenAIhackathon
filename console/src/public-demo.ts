export const publicDemo = import.meta.env.MODE === 'hosted'
const workspaceKey = 'redwood.public-workspace.v1'

// A desk change and a case update may arrive together. Apply them in order so
// each action uses the latest signed workspace from this tab.
let queue: Promise<unknown> = Promise.resolve()
let workspace: string | null = null
try { workspace = sessionStorage.getItem(workspaceKey) } catch { /* memory-only tab */ }

function remember(value: string | null) {
  workspace = value
  try {
    if (value === null) sessionStorage.removeItem(workspaceKey)
    else sessionStorage.setItem(workspaceKey, value)
  } catch { /* The demo still works until the tab is reloaded. */ }
}

export function publicRequest(token: string | null, path: string, body?: object, actionKey?: string): Promise<Response> {
  const run = async () => {
    const response = await fetch('/api/demo', {
      method: 'POST', cache: 'no-store', credentials: 'omit', redirect: 'error',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, body, desk_token: token, action_key: actionKey, workspace }),
    })
    if (response.status === 410) {
      remember(null)
      // Restore and workspace polling already handle an expired staff session.
      return Response.json({ message: 'A new version of the demo is available. Reopen your desk.' }, { status: 401 })
    }
    if (!response.ok) return response
    const result = await response.json()
    if (typeof result.workspace === 'string') remember(result.workspace)
    return Response.json(result.data, { status: result.status })
  }
  const pending = queue.then(run)
  queue = pending.catch(() => undefined)
  return pending
}
