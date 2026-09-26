# Personal OpenCode V2 accessibility releases

This automation belongs to aimansour/opencode's default branch (dev), **not**
to the open PR branch streaming-steps-a11y. It tracks official published,
non-prerelease V2 tags starting at v2.0.18 and applies all commits from
anomalyco/opencode#51084 to each tag without updating the PR branch.

## Lifecycle

GitHub Actions runs Personal V2 A11y CLI every hour (at minute 23 UTC).
You can also open Actions > Personal V2 A11y CLI > Run workflow, optionally
supplying a specific official V2 tag. It ships one previously unpublished
official version per run, oldest first, and will stop automatically when
the original PR is closed or merged.

If cherry-picking, version-dependent branding, tests, artifact verification,
or publishing breaks, the workflow creates an issue starting with
[a11y-release-blocked]. **All subsequent scheduled runs skip releases**
until you resolve the problem and close the blocking issue. The Chromium
accessibility regression, CLI build, per-target executable checks, and
workflow-built CLI smoke test must succeed before publishing. If GitHub
leaves an incomplete draft Release, the selector also opens a blocking
issue instead of silently treating that draft as a finished release.

The workflow generates a dedicated tag (a11y-v2.x.y) pointing to the
precise patched and branded source commit and publishes all 12 cross-
compiled CLI target archives, SHA256SUMS, and BUILD_INFO.txt. The Linux
x64 baseline executable is actually run in the workflow from the PATH
directory created by that workflow. Other targets are cross-compiled
and checked by the upstream artifact verifier, but not runtime-tested
on their target OS.

## Install and update

Download the archive for your platform from this fork's Releases page.
For Linux x64 without an AVX2 requirement, extract the archive, then
install its bin/opencode-a11y file to ~/.local/bin/opencode-a11y. Add that
directory to PATH if needed. Leave the official opencode executable
untouched. On macOS, extract the corresponding darwin archive; macOS
may require you to approve the unsigned personal binary. On Windows,
extract the appropriate windows ZIP and put its bin directory on PATH.

Verify the archive against SHA256SUMS before running it. To update a
previously installed personal CLI, replace only opencode-a11y using the
newer personal Release asset. The official in-app updater and upgrade
command are deliberately disabled for the a11y channel, so they cannot
silently install a broken official version. **Automatic updating of an
already-installed desktop/CLI binary is not configured**; this workflow
automatically produces and publishes the new release, not an unattended
update of each user's computer.

If fork Actions are disabled, enable them on the fork. To stop the
automation for any reason before the PR closes, disable Personal V2
A11y CLI under GitHub Actions, or remove the scheduled workflow from
the fork's default branch. Do not edit the PR branch to manage releases.