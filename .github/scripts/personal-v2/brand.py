#!/usr/bin/env python3
"""Fail-closed branding for aimansour's OpenCode V2 accessibility fork."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: brand-personal-v2.py <upstream-source-dir>")
root = Path(sys.argv[1]).resolve()

def change(relative: str, before: str, after: str) -> None:
    path = root / relative
    source = path.read_text(encoding="utf-8")
    count = source.count(before)
    if count != 1:
        raise SystemExit(f"BRANDING INCOMPATIBLE: {relative}: expected one match, found {count}. Stop and update branding manually.")
    path.write_text(source.replace(before, after, 1), encoding="utf-8")
    print(f"branded: {relative}")

build = "packages/cli/script/build.ts"
change(build, 'const binary = "opencode"', 'const binary = "opencode-a11y"')
change(build, "OPENCODE_CLI_NAME: \"'opencode'\"", "OPENCODE_CLI_NAME: \"'opencode-a11y'\"")
change(build, "@opencode/" + chr(36) + "{name}", "@aimansour/" + chr(36) + "{name}")
change(build, "git+https://github.com/anomalyco/opencode.git", "git+https://github.com/aimansour/opencode.git")
change("packages/util/src/global.ts", 'const app = "opencode"', 'const app = "opencode-a11y"')

updater = "packages/cli/src/services/updater.ts"
change(updater,
       '  const readPolicy = Effect.fnUntraced(function* () {\n',
       '  const readPolicy = Effect.fnUntraced(function* () {\n    if (OPENCODE_CHANNEL === "a11y") return "disable" as const\n')
change(updater,
       '  const check = Effect.fn("cli.updater.check")(function* () {\n',
       '  const check = Effect.fn("cli.updater.check")(function* () {\n    if (OPENCODE_CHANNEL === "a11y") return { type: "unavailable" as const, message: "Personal updates: https://github.com/aimansour/opencode/releases" }\n')

upgrade = "packages/cli/src/commands/handlers/upgrade.ts"
change(upgrade,
       'import { OPENCODE_VERSION } from "../../version"',
       'import { OPENCODE_CHANNEL, OPENCODE_VERSION } from "../../version"')
change(upgrade,
       '      intro("Upgrade")',
       '      if (OPENCODE_CHANNEL === "a11y") return yield* Effect.fail(new Error("This personal CLI only updates through https://github.com/aimansour/opencode/releases; official upgrade is disabled."))\n      intro("Upgrade")')
change("packages/cli/src/commands/commands.ts",
       'description: "OpenCode command line interface"',
       'description: "OpenCode A11y personal CLI (aimansour)"')
print("Personal identity and official-updater isolation applied.")