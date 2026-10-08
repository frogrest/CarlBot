import react from '@vitejs/plugin-react'
import { defineConfig, type CommonServerOptions } from 'vite'

// Derived from Vite's public config types so the callback signature always
// matches the installed Vite version (no reliance on ProxyOptions export).
type ProxyEntry = Exclude<NonNullable<CommonServerOptions['proxy']>[string], string>
type ProxyConfigure = NonNullable<ProxyEntry['configure']>

// NOTE: use 127.0.0.1 (not `localhost`) for proxy targets on Windows.
// `localhost` can resolve to ::1 first; Node's dual-stack connect then
// reports `AggregateError [ECONNREFUSED]` even when a backend listens on
// IPv4 only. Respond 502 JSON immediately on proxy failure so the UI shows
// a clear "backend_unreachable" error instead of the request hanging.
// Vite attaches its own error logger after `configure` runs, so this
// listener fires first and Vite's handler then skips its duplicate write.
function respondOnProxyError(proxy: Parameters<ProxyConfigure>[0]) {
  proxy.on('error', (_err, _req, res) => {
    const writable = res as unknown as {
      headersSent?: boolean
      writableEnded?: boolean
      writeHead?: (code: number, headers?: Record<string, string>) => void
      end?: (body?: string) => void
    }
    if (
      !writable?.headersSent &&
      !writable?.writableEnded &&
      typeof writable?.writeHead === 'function'
    ) {
      writable.writeHead(502, { 'Content-Type': 'application/json' })
      writable.end?.(JSON.stringify({ ok: false, error: 'backend_unreachable' }))
    }
  })
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/helpdesk': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/helpdesk/, ''),
        configure: respondOnProxyError,
      },
      '/portal': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/portal/, ''),
        configure: respondOnProxyError,
      },
      '/agent': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, ''),
        configure: respondOnProxyError,
      },
    },
  },
})
