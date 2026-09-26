#!/usr/bin/env python3
"""Fail-closed Windows Desktop branding for the personal V2 distribution."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: desktop_brand.py <official-v2-source-dir>")
root = Path(sys.argv[1]).resolve()

def change(relative: str, before: str, after: str) -> None:
    path = root / relative
    value = path.read_text(encoding="utf-8")
    count = value.count(before)
    if count != 1:
        raise SystemExit(f"DESKTOP BRANDING INCOMPATIBLE: {relative}: expected one match, found {count}. Resolve manually.")
    path.write_text(value.replace(before, after, 1), encoding="utf-8")
    print(f"desktop branded: {relative}")

utils = "packages/desktop/scripts/utils.ts"
change(utils, 'export type Channel = "dev" | "beta" | "prod"', 'export type Channel = "dev" | "beta" | "prod" | "a11y"')
change(utils, 'raw === "dev" || raw === "beta" || raw === "prod"', 'raw === "dev" || raw === "beta" || raw === "prod" || raw === "a11y"')
change(utils, 'cli.os === "win32" ? "opencode.exe" : "opencode"', 'Bun.env.OPENCODE_CHANNEL === "a11y" ? (cli.os === "win32" ? "opencode-a11y.exe" : "opencode-a11y") : (cli.os === "win32" ? "opencode.exe" : "opencode")')
change(utils, 'if (process.platform === "win32" && process.env.GITHUB_ACTIONS === "true") {', 'if (process.platform === "win32" && process.env.GITHUB_ACTIONS === "true" && Bun.env.OPENCODE_CHANNEL !== "a11y") {')
change(utils, '  if (!manifest.version) throw new Error(', '  if (Bun.env.OPENCODE_CHANNEL === "a11y" && manifest.name !== "@aimansour/" + cli.package.replace("@opencode/", "")) throw new Error("Personal desktop requires the tested personal CLI package")\n  if (!manifest.version) throw new Error(')
change(utils, 'as { version?: string }', 'as { version?: string; name?: string }')

prebuild = "packages/desktop/scripts/prebuild.ts"
change(prebuild, 'channel === "prod" && !Bun.env.OPENCODE_CLI_DIST', '(channel === "prod" || channel === "a11y") && !Bun.env.OPENCODE_CLI_DIST')
change(prebuild, '(channel === "beta" || channel === "prod") && Bun.env.OPENCODE_CLI_DIST', '(channel === "beta" || channel === "prod" || channel === "a11y") && Bun.env.OPENCODE_CLI_DIST')
change("packages/desktop/scripts/copy-icons.ts", 'const src = ' + chr(96) + './icons/' + chr(36) + '{channel}' + chr(96), 'const src = ' + chr(96) + './icons/' + chr(36) + '{channel === "a11y" ? "dev" : channel}' + chr(96))

vite = "packages/desktop/electron.vite.config.ts"
change(vite, 'raw === "beta" || raw === "prod"', 'raw === "beta" || raw === "prod" || raw === "a11y"')
change(vite, '"import.meta.env.VITE_OPENCODE_CHANNEL": JSON.stringify(channel)', '"import.meta.env.VITE_OPENCODE_CHANNEL": JSON.stringify(channel === "a11y" ? "dev" : channel)')

constants = "packages/desktop/src/main/constants.ts"
change(constants, 'type Channel = "local" | "dev" | "beta" | "prod"', 'type Channel = "local" | "dev" | "beta" | "prod" | "a11y"')
change(constants, 'raw === "beta" || raw === "prod"', 'raw === "beta" || raw === "prod" || raw === "a11y"')
change(constants, 'app.isPackaged && CHANNEL !== "dev"', 'app.isPackaged && CHANNEL !== "dev" && CHANNEL !== "a11y"')
change(constants, '  prod: "OpenCode",', '  prod: "OpenCode",\n  a11y: "OpenCode A11y",')
change(constants, '  prod: "ai.opencode.desktop",', '  prod: "ai.opencode.desktop",\n  a11y: "ai.aimansour.opencode.a11y",')
environment = "packages/desktop/src/main/lifecycle/environment.ts"
change(environment, 'import { DesktopPaths } from "../paths"', 'import { DesktopPaths } from "../paths"\nimport { CHANNEL } from "../constants"')
change(environment, 'if (app.isPackaged || process.env.OPENCODE_DESKTOP_DISABLE_PROTOCOL_REGISTRATION !== "1")', 'if (CHANNEL !== "a11y" && (app.isPackaged || process.env.OPENCODE_DESKTOP_DISABLE_PROTOCOL_REGISTRATION !== "1"))')

builder = "packages/desktop/electron-builder.config.ts"
change(builder, '  if (process.platform !== "win32") return', '  if (process.platform !== "win32" || process.env.OPENCODE_CHANNEL === "a11y") return')
change(builder, 'raw === "dev" || raw === "beta" || raw === "prod"', 'raw === "dev" || raw === "beta" || raw === "prod" || raw === "a11y"')
change(builder, '  prod: "ai.opencode.desktop",', '  prod: "ai.opencode.desktop",\n  a11y: "ai.aimansour.opencode.a11y",')
change(builder, '  switch (channel) {\n    case "dev": {', '''  switch (channel) {
    case "a11y": {
      return {
        ...base,
        appId,
        productName: "OpenCode A11y",
        artifactName: "opencode-a11y-desktop-${version}-${os}-${arch}.${ext}",
        // electron-builder creates NSIS update metadata even with --publish never.
        // Use only the personal fork as the provider; the in-app updater remains disabled.
        publish: { provider: "github", owner: "aimansour", repo: "opencode", channel: "a11y" },
        protocols: [],
        win: { ...base.win, executableName: "opencode-a11y-desktop" },
        deb: { fpm: [metainfoFpm(appId)] },
        rpm: { packageName: "opencode-a11y", fpm: [metainfoFpm(appId)] },
      }
    }
    case "dev": {''')
metainfo = "packages/desktop/scripts/copy-metainfo.ts"
change(metainfo, 'const appId = channel === "prod" ? "ai.opencode.desktop" :', 'const appId = channel === "a11y" ? "ai.aimansour.opencode.a11y" : channel === "prod" ? "ai.opencode.desktop" :')
change(metainfo, 'const productName = channel === "prod" ? "OpenCode" :', 'const productName = channel === "a11y" ? "OpenCode A11y" : channel === "prod" ? "OpenCode" :')

# The branded CLI registers its service under the personal global state tree and
# service-a11y.json. Electron must discover/ensure that same file, never the
# official opencode/service.json or a service belonging to another channel.
probe = "packages/desktop/src/main/service/sidecar-probe.ts"
change(probe, 'import { app } from "electron"', 'import { app } from "electron"\nimport { CHANNEL } from "../constants"')
change(probe, 'let probe: Promise<Endpoint | undefined> | undefined', '''let probe: Promise<Endpoint | undefined> | undefined

export function personalServiceFile() {
  if (CHANNEL !== "a11y") return undefined
  const state = process.env.XDG_STATE_HOME ?? path.join(app.getPath("home"), ".local", "state")
  return path.join(state, "opencode-a11y", "service-a11y.json")
}''')
change(probe, 'Service.discover({ version })', 'Service.discover({ version, file: personalServiceFile() })')
service = "packages/desktop/src/main/service/background-service.ts"
change(service, 'import { sidecarProbe } from "./sidecar-probe"', 'import { personalServiceFile, sidecarProbe } from "./sidecar-probe"')
change(service, '          : undefined,\n      version,', '          : personalServiceFile(),\n      version,')

# NSIS otherwise inherits upstream's @opencode/desktop package-name install folder.
# The personal installer must never share the official product's on-disk install path.
installer = "packages/desktop/resources/windows/installer.nsh"
change(installer, "!macro customInstall", '''!macro preInit
  ; Unique per-user installation path for personal OpenCode A11y.
  ; This registry key is scoped to the distinct personal appId / NSIS GUID.
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$LOCALAPPDATA\\Programs\\OpenCode-A11y"
!macroend

!macro customInstall''')
print("Personal Windows Desktop identity, bundled CLI, and updater isolation applied.")
