#!/usr/bin/env python3
"""Turn off upstream Apple signing/notarization for unsigned personal macOS builds."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: unix_brand.py <personal-source-dir>")
path = Path(sys.argv[1]).resolve() / "packages/desktop/electron-builder.config.ts"
source = path.read_text(encoding="utf-8")
old = '''        publish: { provider: "github", owner: "aimansour", repo: "opencode", channel: "a11y" },
        protocols: [],'''
new = '''        publish: { provider: "github", owner: "aimansour", repo: "opencode", channel: "a11y" },
        // Personal macOS builds are unsigned and unnotarized; no upstream Apple credentials.
        mac: { ...base.mac, identity: null, sign: undefined, notarize: false, hardenedRuntime: false },
        protocols: [],'''
if source.count(old) != 1 or source.count(new) != 0:
    raise SystemExit("UNIX BRANDING INCOMPATIBLE: personal provider or signing structure changed; manual review required.")
path.write_text(source.replace(old, new, 1), encoding="utf-8")
utils = Path(sys.argv[1]).resolve() / "packages/desktop/scripts/utils.ts"
utils_source = utils.read_text(encoding="utf-8")
mac_sign = 'if (process.platform === "darwin") await $`codesign --force --sign - ${dest}`'
mac_personal = 'if (process.platform === "darwin" && Bun.env.OPENCODE_CHANNEL !== "a11y") await $`codesign --force --sign - ${dest}`'
if utils_source.count(mac_sign) != 1 or mac_personal in utils_source:
    raise SystemExit("UNIX BRANDING INCOMPATIBLE: macOS CLI signing changed; manual review required.")
utils.write_text(utils_source.replace(mac_sign, mac_personal, 1), encoding="utf-8")
print("Personal macOS Desktop signing disabled and the embedded CLI bytes preserved.")
