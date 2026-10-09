/**
 * Responsive / overflow audit for the running CarlBot frontend.
 *
 * Drives the real app in headless Chrome over the DevTools Protocol and checks
 * every primary navigation view for horizontal page overflow at phone and
 * desktop widths. This is the executable half of the `frontend-visual-qa`
 * skill's responsive checks.
 *
 * Usage (with the dev server or Docker frontend running):
 *   node scripts/responsive-audit.mjs
 *   APP_URL=http://localhost:8003 node scripts/responsive-audit.mjs
 *
 * Requires: Google Chrome installed, Node 18+ (global fetch + WebSocket).
 */
import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME =
  process.env.CHROME_PATH ||
  'C:/Program Files/Google/Chrome/Application/chrome.exe'
const APP_URL = process.env.APP_URL || 'http://localhost:5173'
const PORT = Number(process.env.CDP_PORT || 9333)

const VIEWPORTS = [
  { name: 'phone', width: 390, height: 844, mobile: true },
  { name: 'desktop', width: 1280, height: 800, mobile: false },
]

// Navigation items in the top nav (order matters only for readability).
const VIEWS = ['Dashboard', 'Tasks', 'Tickets', 'Knowledge', 'CarlBot AI', 'Assets']

function launchChrome(userDataDir) {
  const args = [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ]
  return spawn(CHROME, args, { stdio: 'ignore' })
}

async function browserWsUrl() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`)
      const info = await res.json()
      if (info.webSocketDebuggerUrl) return info.webSocketDebuggerUrl
    } catch {
      // not ready yet
    }
    await sleep(200)
  }
  throw new Error('Chrome DevTools endpoint did not come up')
}

class CDP {
  constructor(ws) {
    this.ws = ws
    this.nextId = 0
    this.pending = new Map()
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(JSON.stringify(msg.error)))
        else resolve(msg.result)
      }
    }
  }

  send(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = (this.nextId += 1)
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params, sessionId }))
    })
  }
}

async function evaluate(cdp, sessionId, expression) {
  const result = await cdp.send(
    'Runtime.evaluate',
    { expression, returnByValue: true, awaitPromise: true },
    sessionId,
  )
  if (result.exceptionDetails) {
    throw new Error('page evaluate failed: ' + JSON.stringify(result.exceptionDetails))
  }
  return result.result.value
}

async function waitFor(cdp, sessionId, expression, { timeout = 15000, label = 'condition' } = {}) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    if (await evaluate(cdp, sessionId, expression)) return true
    await sleep(200)
  }
  throw new Error(`timed out waiting for ${label}`)
}

const MEASURE = `(() => {
  const doc = document.documentElement;
  const vw = window.innerWidth;
  const overflowX = doc.scrollWidth - doc.clientWidth;
  const rightmost = [...document.querySelectorAll('body *')]
    .map((el) => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        cls: String(el.className || '').slice(0, 48),
        right: Math.round(r.right),
        width: Math.round(r.width),
      };
    })
    .sort((a, b) => b.right - a.right)
    .slice(0, 5);
  return {
    overflowX,
    innerWidth: window.innerWidth,
    docClientWidth: doc.clientWidth,
    docScrollWidth: doc.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    cards: document.querySelectorAll('.model-card').length,
    rightmost,
  };
})()`

async function openView(cdp, sessionId, label) {
  await evaluate(
    cdp,
    sessionId,
    `[...document.querySelectorAll('.nav-item')].find(b => b.textContent.includes(${JSON.stringify(label)}))?.click(), true`,
  )
  await sleep(450)
  // In the copilot view, make sure the model chooser panel is expanded.
  await evaluate(
    cdp,
    sessionId,
    `(() => {
      const t = document.querySelector('.model-manager .model-manager-header button');
      if (t && t.getAttribute('aria-expanded') === 'false') t.click();
      return true;
    })()`,
  )
  await sleep(350)
}

async function auditViewport(cdp, viewport) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true })
  const rows = []
  try {
    await cdp.send('Page.enable', {}, sessionId)
    await cdp.send('Runtime.enable', {}, sessionId)
    await cdp.send(
      'Emulation.setDeviceMetricsOverride',
      { width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: viewport.mobile },
      sessionId,
    )
    await cdp.send('Page.navigate', { url: APP_URL }, sessionId)
    await waitFor(cdp, sessionId, 'document.readyState === "complete"', { label: 'load' })
    await waitFor(cdp, sessionId, '!!document.querySelector(".primary-nav")', { label: 'app shell' })

    for (const label of VIEWS) {
      await openView(cdp, sessionId, label)
      rows.push({ view: label, ...(await evaluate(cdp, sessionId, MEASURE)) })
    }
  } finally {
    await cdp.send('Target.closeTarget', { targetId }).catch(() => {})
  }
  return rows
}

async function main() {
  const userDataDir = mkdtempSync(join(tmpdir(), 'carlbot-audit-'))
  const chrome = launchChrome(userDataDir)
  const all = []
  try {
    const ws = new WebSocket(await browserWsUrl())
    await new Promise((resolve, reject) => {
      ws.onopen = resolve
      ws.onerror = reject
    })
    const cdp = new CDP(ws)
    for (const viewport of VIEWPORTS) {
      for (const row of await auditViewport(cdp, viewport)) {
        all.push({ viewport, ...row })
      }
    }
    ws.close()
  } finally {
    chrome.kill()
    // Chrome can hold the profile dir briefly after exit; cleanup is best-effort.
    await sleep(500)
    try {
      rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
    } catch {
      // leave the temp profile behind rather than failing the audit
    }
  }

  let failed = false
  for (const r of all) {
    const status = r.overflowX > 0 ? 'FAIL' : 'PASS'
    if (r.overflowX > 0) failed = true
    console.log(
      `${status}  ${r.viewport.name.padEnd(8)} ${String(r.viewport.width).padEnd(5)} ` +
        `${r.view.padEnd(11)} overflowX=${r.overflowX}px cards=${r.cards}`,
    )
    if (r.overflowX > 0) {
      console.log(
        `        innerWidth=${r.innerWidth} docClient=${r.docClientWidth} ` +
          `docScroll=${r.docScrollWidth} bodyScroll=${r.bodyScrollWidth}`,
      )
      for (const o of r.rightmost) {
        console.log(`        rightmost: <${o.tag} class="${o.cls}"> right=${o.right} width=${o.width}`)
      }
    }
  }
  console.log(failed ? '\nResponsive audit FAILED' : '\nResponsive audit passed')
  process.exit(failed ? 1 : 0)
}

main().catch((error) => {
  console.error('responsive audit failed:', error.message)
  process.exit(2)
})
