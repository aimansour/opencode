// Exercise the actual installed Windows Electron executable, not a dev server or unpacked build.
import { spawn, execFile } from "node:child_process"
import { createWriteStream, mkdirSync, writeFileSync } from "node:fs"
import { createServer } from "node:net"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"
import { promisify } from "node:util"
import { collectRuntimeDiagnostics } from "./windows_runtime_diagnostics.mjs"

const [binary, reportDir] = process.argv.slice(2)
if (!binary || !reportDir || process.platform !== "win32") throw new Error("usage (Windows): node windows_ui_smoke.mjs <installed-exe> <report-dir>")
const output = resolve(reportDir)
const home = join(output, "profile")
const data = join(home, "AppData", "Roaming")
const local = join(home, "AppData", "Local")
for (const dir of [output, data, local, join(home, "config"), join(home, "data"), join(home, "cache"), join(home, "state")]) mkdirSync(dir, { recursive: true })
// Never forward GitHub Actions tokens or unrelated runner secrets into the desktop or its logs.
const safeEnv = /^(PATH|PATHEXT|SystemRoot|WINDIR|COMSPEC|TEMP|TMP|USERDOMAIN|USERNAME|USERPROFILE|APPDATA|LOCALAPPDATA|HOMEDRIVE|HOMEPATH|PROCESSOR_ARCHITECTURE|PROCESSOR_IDENTIFIER|NUMBER_OF_PROCESSORS|PROGRAMFILES|PROGRAMFILES\(X86\)|PROGRAMW6432|PROGRAMDATA|ALLUSERSPROFILE|COMMONPROGRAMFILES|COMMONPROGRAMFILES\(X86\)|COMMONPROGRAMW6432|LANG|LC_ALL)$/i
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => safeEnv.test(key)))
// Keep the actual Windows account home: Electron resolves it through Windows APIs while
// Bun/Node can honor USERPROFILE. Spoofing it produced a false service-path mismatch.
Object.assign(env, {
  APPDATA: data, LOCALAPPDATA: local,
  XDG_DATA_HOME: join(home, "data"), XDG_CONFIG_HOME: join(home, "config"),
  XDG_CACHE_HOME: join(home, "cache"), XDG_STATE_HOME: join(home, "state"),
  OPENCODE_CONFIG_DIR: join(home, "config"), OPENCODE_DB: join(home, "data", "opencode-a11y.db"),
  OPENCODE_DISABLE_AUTOUPDATE: "1",
})
const sleep = (ms) => new Promise((done) => setTimeout(done, ms))
const timeout = (ms, message) => new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms))
async function port() {
  const server = createServer()
  await new Promise((done) => server.listen(0, "127.0.0.1", done))
  const number = server.address().port
  await new Promise((done) => server.close(done))
  return number
}
async function pages(number) {
  return fetch("http://127.0.0.1:" + number + "/json/list", { signal: AbortSignal.timeout(1500) })
    .then((response) => response.ok ? response.json() : [])
    .catch(() => [])
}
async function connect(url, events) {
  const ws = new WebSocket(url)
  await Promise.race([
    new Promise((done, fail) => { ws.addEventListener("open", done, { once: true }); ws.addEventListener("error", fail, { once: true }) }),
    timeout(10000, "CDP WebSocket connection timed out"),
  ])
  let id = 0
  const pending = new Map()
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(String(event.data))
    if (message.id && pending.has(message.id)) {
      const { done, fail, timer } = pending.get(message.id)
      clearTimeout(timer)
      pending.delete(message.id)
      message.error ? fail(new Error(JSON.stringify(message.error))) : done(message.result)
    } else if (message.method === "Runtime.exceptionThrown") {
      events.push({ type: "exception", message: message.params?.exceptionDetails?.text })
    } else if (message.method === "Log.entryAdded" && message.params?.entry?.level === "error") {
      events.push({ type: "log", message: message.params.entry.text?.slice(0, 400) })
    }
  })
  return {
    send(method, params = {}) {
      return new Promise((done, fail) => {
        const next = ++id
        const timer = setTimeout(() => { pending.delete(next); fail(new Error("CDP timeout: " + method)) }, 10000)
        pending.set(next, { done, fail, timer })
        ws.send(JSON.stringify({ id: next, method, params }))
      })
    },
    close: () => ws.close(),
  }
}
const probe = `(() => {
  const root = document.getElementById("root");
  const overlay = document.querySelector('[data-component="startup-overlay"]');
  const overlayStyle = overlay ? getComputedStyle(overlay) : null;
  const shell = document.querySelector('#root [data-titlebar-tab-link], #root [data-action="vertical-tabs-home"]');
  const home = document.querySelector('#root [data-action="home-new-session"], #root [data-action="home-add-project-row"]');
  const editor = document.querySelector('#root [data-component="composer-editor"][contenteditable="true"]');
  const visible = [home, editor].some((el) => el && el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0);
  return {
    url: location.href, state: document.readyState, title: document.title,
    rootChildren: root?.children.length ?? 0, shell: !!shell, home: !!home, editor: !!editor,
    visible, splash: !!document.querySelector('[data-component="startup-splash"],[data-component="first-launch-splash"]'),
    overlayBlocking: !!overlayStyle && overlayStyle.pointerEvents !== "none" && Number(overlayStyle.opacity) > 0.05,
    bodyText: document.body.innerText.slice(0, 200),
    errorDetails: document.querySelector("textarea[data-slot=input-input]")?.value?.slice(0, 8000) ?? "",
  };
})()`
const report = { started: new Date().toISOString(), installedExecutable: resolve(binary), ready: false, observations: [], errors: [] }
let child, cdp
try {
  const debugPort = await port()
  const stdout = createWriteStream(join(output, "electron-stdout.log"))
  const stderr = createWriteStream(join(output, "electron-stderr.log"))
  child = spawn(resolve(binary), ["--remote-debugging-port=" + debugPort, "--enable-logging"], { env, windowsHide: false, stdio: ["ignore", "pipe", "pipe"] })
  child.stdout.pipe(stdout)
  child.stderr.pipe(stderr)
  child.on("error", (error) => report.errors.push({ type: "spawn", message: error.message }))
  const deadline = Date.now() + 150000
  let page
  while (Date.now() < deadline && !page) {
    page = (await pages(debugPort)).find((item) => item.type === "page" && item.url.startsWith("oc://"))
    if (!page) await sleep(250)
  }
  if (!page) throw new Error("No packaged oc:// renderer appeared within 150 seconds")
  cdp = await connect(page.webSocketDebuggerUrl, report.errors)
  await cdp.send("Runtime.enable")
  await cdp.send("Page.enable")
  await cdp.send("Log.enable")
  let last
  const readyDeadline = Date.now() + 150000
  while (Date.now() < readyDeadline) {
    if (child.exitCode !== null) throw new Error("Desktop exited before its UI was ready: " + child.exitCode)
    const evaluated = await cdp.send("Runtime.evaluate", { expression: probe, returnByValue: true })
    last = evaluated.result?.value
    if (evaluated.exceptionDetails) report.errors.push({ type: "probe", message: evaluated.exceptionDetails.text })
    if (last) {
      report.last = last
      if (report.observations.length === 0 || Date.now() - report.observations.at(-1).at > 5000)
        report.observations.push({ at: Date.now(), ...last })
      if (last.bodyText?.includes("An error occurred while starting the local server.") && last.errorDetails) break
      if ((last.home || last.editor) && last.visible && !last.overlayBlocking) {
        await sleep(3000)
        const confirm = await cdp.send("Runtime.evaluate", { expression: probe, returnByValue: true })
        if (confirm.result?.value?.visible && !confirm.result.value.overlayBlocking) {
          report.ready = true
          report.last = confirm.result.value
          break
        }
      }
    }
    await sleep(300)
  }
  try {
    const shot = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false })
    if (shot?.data) writeFileSync(join(output, "desktop-window.png"), Buffer.from(shot.data, "base64"))
  } catch (error) { report.errors.push({ type: "screenshot", message: error.message }) }
  if (!report.ready) throw new Error("Desktop renderer never exposed a visible, usable UI; last probe: " + JSON.stringify(last))
  if (report.errors.some((event) => event.type === "exception")) throw new Error("Uncaught renderer exception detected: " + JSON.stringify(report.errors))
  console.log("Installed Windows Desktop opened a visible UI:", JSON.stringify(report.last))
} catch (error) {
  report.failure = error.message
  console.error("WINDOWS RUNTIME SMOKE FAILED:", error)
  process.exitCode = 1
} finally {
  report.finished = new Date().toISOString()
  report.diagnostics = collectRuntimeDiagnostics({ home, data, local, runnerHome: process.env.USERPROFILE })
  writeFileSync(join(output, "smoke-result.json"), JSON.stringify(report, null, 2))
  cdp?.close()
  if (child?.pid) {
    try { await promisify(execFile)("taskkill", ["/PID", String(child.pid), "/T", "/F"], { timeout: 15000 }) } catch {}
  }
}
