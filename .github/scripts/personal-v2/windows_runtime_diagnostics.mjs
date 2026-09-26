// Collect only synthetic-runner app diagnostics. Never copy service passwords or raw secrets.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"

function safeLines(file) {
  try {
    if (statSync(file).size > 2_000_000) return ["log too large to include"]
    return readFileSync(file, "utf8")
      .split(/\r?\n/)
      .filter((line) => /error|failed|fatal|service|start|registration|timed out/i.test(line))
      .slice(-35)
      .map((line) => line
        .replace(/(password|token|authorization|api[_-]?key|secret|credential)(\s*["'=:\s]+)([^\s,;}"']+)/gi, "$1$2[REDACTED]")
        .replace(/Basic\s+[A-Za-z0-9+/=_-]+/gi, "Basic [REDACTED]")
        .slice(0, 950))
  } catch (error) { return ["log read failed: " + error.code] }
}

function logsIn(root, depth = 2) {
  if (!root || !existsSync(root) || depth < 0) return []
  let entries
  try { entries = readdirSync(root, { withFileTypes: true }) }
  catch { return [] }
  return entries.flatMap((item) => {
    const path = join(root, item.name)
    if (item.isDirectory()) return logsIn(path, depth - 1)
    if (!item.isFile() || !item.name.endsWith(".log")) return []
    return [{ file: path, lines: safeLines(path) }]
  }).slice(0, 60)
}

function inspectRegistration(path) {
  if (!existsSync(path)) return { file: path, exists: false }
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8"))
    // In particular, NEVER include the service's password or auth headers.
    return { file: path, exists: true, pid: parsed.pid, version: parsed.version, url: parsed.url }
  } catch (error) {
    return { file: path, exists: true, error: error.message }
  }
}

export function collectRuntimeDiagnostics({ home, data, local, runnerHome }) {
  const users = [...new Set([home, runnerHome].filter(Boolean))]
  const states = [...new Set([
    join(home, "state"),
    ...users.map((root) => join(root, ".local", "state")),
    join(data, "ai.aimansour.opencode.a11y"),
    join(local, "ai.aimansour.opencode.a11y"),
  ])]
  const registrations = states.flatMap((base) => [
    inspectRegistration(join(base, "opencode-a11y", "service-a11y.json")),
    inspectRegistration(join(base, "opencode", "service.json")),
  ])
  const logs = [...new Set([
    join(data, "ai.aimansour.opencode.a11y", "logs"),
    join(local, "ai.aimansour.opencode.a11y", "logs"),
    join(home, "data", "opencode-a11y", "log"),
    ...users.map((root) => join(root, ".local", "share", "opencode-a11y", "log")),
  ])].flatMap((root) => logsIn(root))
  return {
    registrations: registrations.filter((item) => item.exists),
    checkedRegistrationPaths: registrations.map((item) => item.file),
    logs,
  }
}
