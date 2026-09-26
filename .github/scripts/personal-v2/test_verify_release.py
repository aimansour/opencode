#!/usr/bin/env python3
"""Regression checks for the exact-asset release gate."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("verify_release.py")
TAG = "v2.0.18"
DIGEST = "sha256:" + "a" * 64
CLI_TARGETS = (
    "darwin-arm64.tar.gz darwin-x64-baseline.tar.gz darwin-x64.tar.gz "
    "linux-arm64-musl.tar.gz linux-arm64.tar.gz linux-x64-baseline-musl.tar.gz "
    "linux-x64-baseline.tar.gz linux-x64-musl.tar.gz linux-x64.tar.gz "
    "windows-arm64.zip windows-x64-baseline.zip windows-x64.zip"
).split()


def release_for(kind, field="isDraft"):
    version = TAG[1:]
    if kind == "cli":
        names = {f"opencode-a11y-{version}-{target}" for target in CLI_TARGETS}
    elif kind == "windows":
        names = {f"opencode-a11y-desktop-{version}-win-x64.exe"}
    elif kind == "unix":
        names = {
            f"opencode-a11y-desktop-{version}-mac-{arch}.{ext}"
            for arch in ("x64", "arm64")
            for ext in ("dmg", "zip")
        } | {
            f"opencode-a11y-desktop-{version}-linux-{arch}.{ext}"
            for arch in ("x64", "arm64")
            for ext in ("AppImage", "deb", "rpm")
        }
    else:
        raise ValueError(kind)
    return {
        field: False,
        "assets": [
            {"name": name, "state": "uploaded", "size": 1024, "digest": DIGEST}
            for name in sorted(names | {"SHA256SUMS", "BUILD_INFO.txt"})
        ],
    }


class ReleaseVerifierTests(unittest.TestCase):
    def verify(self, kind, release, tag=TAG):
        return subprocess.run(
            [sys.executable, str(SCRIPT), kind, tag],
            input=json.dumps(release),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_complete_releases_accept_both_github_api_shapes(self):
        for kind in ("cli", "windows", "unix"):
            for field in ("isDraft", "draft"):
                with self.subTest(kind=kind, field=field):
                    result = self.verify(kind, release_for(kind, field))
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_names_and_uploaded_hashes_are_required(self):
        def rename(r):
            r["assets"][0]["name"] = "substituted-asset.zip"

        def duplicate(r):
            r["assets"][0]["name"] = r["assets"][1]["name"]

        def extra(r):
            r["assets"].append({**r["assets"][0], "name": "unexpected.bin"})

        mutations = {
            "substituted asset": rename,
            "missing asset": lambda r: r["assets"].pop(),
            "duplicate asset": duplicate,
            "unexpected extra asset": extra,
            "missing hash": lambda r: r["assets"][0].pop("digest"),
            "invalid hash": lambda r: r["assets"][0].update(digest="sha256:123"),
            "empty asset": lambda r: r["assets"][0].update(size=0),
            "not uploaded": lambda r: r["assets"][0].update(state="new"),
        }
        for kind in ("cli", "windows", "unix"):
            for scenario, mutate in mutations.items():
                with self.subTest(kind=kind, scenario=scenario):
                    release = copy.deepcopy(release_for(kind))
                    mutate(release)
                    result = self.verify(kind, release)
                    self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_rejects_drafts_and_absent_assets(self):
        for kind in ("cli", "windows", "unix"):
            draft = release_for(kind)
            draft["isDraft"] = True
            self.assertNotEqual(self.verify(kind, draft).returncode, 0)
            missing = release_for(kind)
            del missing["assets"]
            self.assertNotEqual(self.verify(kind, missing).returncode, 0)

    def test_rejects_invalid_version_tag(self):
        self.assertNotEqual(self.verify("cli", release_for("cli"), "v2.0.18-rc1").returncode, 0)


if __name__ == "__main__":
    unittest.main()
