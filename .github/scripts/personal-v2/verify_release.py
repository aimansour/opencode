#!/usr/bin/env python3
"""Fail closed on an incomplete or substituted personal GitHub Release."""
import json
import re
import sys

if len(sys.argv) != 3 or sys.argv[1] not in {"cli", "windows", "unix"}:
    raise SystemExit("usage: verify_release.py {cli,windows,unix} v2.x.y")
kind, tag = sys.argv[1:]
if not re.fullmatch(r"v2\.\d+\.\d+", tag):
    raise SystemExit(f"Invalid official V2 tag: {tag}")
version = tag[1:]

cli_targets = (
    "darwin-arm64.tar.gz",
    "darwin-x64-baseline.tar.gz",
    "darwin-x64.tar.gz",
    "linux-arm64-musl.tar.gz",
    "linux-arm64.tar.gz",
    "linux-x64-baseline-musl.tar.gz",
    "linux-x64-baseline.tar.gz",
    "linux-x64-musl.tar.gz",
    "linux-x64.tar.gz",
    "windows-arm64.zip",
    "windows-x64-baseline.zip",
    "windows-x64.zip",
)
if kind == "cli":
    installers = {f"opencode-a11y-{version}-{target}" for target in cli_targets}
elif kind == "windows":
    installers = {f"opencode-a11y-desktop-{version}-win-x64.exe"}
else:
    installers = {
        f"opencode-a11y-desktop-{version}-mac-{arch}.{ext}"
        for arch in ("x64", "arm64")
        for ext in ("dmg", "zip")
    } | {
        f"opencode-a11y-desktop-{version}-linux-{arch}.{ext}"
        for arch in ("x64", "arm64")
        for ext in ("AppImage", "deb", "rpm")
    }

expected = installers | {"SHA256SUMS", "BUILD_INFO.txt"}
release = json.load(sys.stdin)
draft = release.get("isDraft", release.get("draft"))
assets = release.get("assets")
if draft is not False or not isinstance(assets, list):
    raise SystemExit(f"Incomplete {kind} Release for {tag}: draft or missing assets")
names = [asset.get("name") for asset in assets]
if len(names) != len(expected) or len(set(names)) != len(names) or set(names) != expected:
    missing = sorted(expected - set(names))
    unexpected = sorted(set(names) - expected)
    raise SystemExit(f"Incomplete {kind} Release for {tag}: missing={missing}, unexpected={unexpected}, count={len(names)}")
for asset in assets:
    if (
        asset.get("state") != "uploaded"
        or not isinstance(asset.get("size"), int)
        or asset["size"] <= 0
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(asset.get("digest") or ""))
    ):
        raise SystemExit(f"Incomplete {kind} Release for {tag}: invalid asset {asset.get('name')}")
print(f"Verified complete {kind} Release for {tag}: {len(expected)} named assets and SHA-256 digests")
