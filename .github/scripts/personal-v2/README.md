# Personal OpenCode V2 accessibility releases

This automation belongs to aimansour/opencode's default branch (dev), **not**
to the open PR branch streaming-steps-a11y. It tracks official published,
non-prerelease V2 tags starting at v2.0.18 and applies all commits from
anomalyco/opencode#51084 to each tag without updating the PR branch.

## Lifecycle

GitHub Actions runs Personal V2 A11y CLI at minute 23 UTC and Personal
V2 A11y Windows Desktop at minute 41 UTC and Personal V2 A11y macOS and
Linux Desktop at minute 49 UTC every hour. All workflows take official
V2 tags oldest-first, starting at v2.0.18. Desktop builders wait for the
matching verified personal CLI release and embed its exact executable.
Each workflow also supports manual Actions dispatch with an official V2 tag.

Closing the PR without merging it, including automatic inactivity closure,
does NOT stop personal releases. All workflows stop after the PR is
actually merged, or when you explicitly set the fork's Actions repository
variable PERSONAL_A11Y_STOP to true. You can also disable all three workflows
under Actions, or open an issue beginning [a11y-release-stop]. The original
PR branch is never edited by the release automation.

If cherry-picking, version-dependent branding, tests, artifact verification,
or publishing breaks, the workflow creates an issue starting with
[a11y-release-blocked]. **All scheduled workflows skip releases**
until you resolve the problem and close the blocking issue. The Chromium
accessibility regression, CLI build, per-target executable checks, and
workflow-built CLI smoke test must succeed before publishing. The Windows
Desktop pipeline additionally checks that the exact CLI from the personal
CLI Release is bundled, and verifies the packaged executable hash. A shared
fail-closed release verifier checks the exact required filename set, uploaded
state, nonzero size, and SHA-256 digest before any published CLI, Windows, or
Unix release is considered complete. Draft or incomplete releases are blockers,
never treated as finished.

The workflow generates a dedicated tag (a11y-v2.x.y) pointing to the
precise patched and branded source commit and publishes all 12 cross-
compiled CLI target archives, SHA256SUMS, and BUILD_INFO.txt. The Linux
x64 baseline executable is actually run in the workflow from the PATH
directory created by that workflow. Other targets are cross-compiled
and checked by the upstream artifact verifier, but not runtime-tested
on their target OS.

## Windows Desktop

The dedicated Windows Desktop release is tagged a11y-desktop-v2.x.y and
contains a Windows x64 NSIS installer, BUILD_INFO.txt, and SHA256SUMS.
Its product name is OpenCode A11y, and its application identity, installer
location (`%LOCALAPPDATA%\\Programs\\OpenCode-A11y`), and user-data directory
are distinct from official OpenCode. CI places a sentinel in the upstream
package-name install directory and rejects a personal installer that touches
that directory or installs outside the dedicated personal location. The Windows builder
checks out the immutable source tag used by the tested personal CLI Release
(not the mutable PR head) and verifies that source against the hash-checked
CLI BUILD_INFO.txt before packaging. It bundles opencode-a11y.exe
from the matching personal CLI Release. Both the official Electron updater and
bundled CLI's official updater are disabled.
The personal installer is unsigned and may trigger SmartScreen; verify
SHA256SUMS before installing. Windows releases must now pass a real NSIS
installation and installed-app GUI startup smoke test on a Windows runner:
the test rejects a blank renderer, a splash that never finishes, and a local
CLI server startup error. The personal Desktop uses the same
opencode-a11y/service-a11y.json registration as its branded CLI, never the
official OpenCode service registry. The personal Desktop doesn't take over the
official opencode:// protocol. Desktop updates are published automatically
but must be installed manually from the next personal Desktop Release.
Only Windows x64 Desktop is built and packaged by this workflow. To test a
future workflow change without modifying a published release, manually
dispatch it with upstream_tag set to an already-published V2 tag and
verify_only=true. This rebuilds, tests, packages and checks the installer,
but does not push source tags or publish assets. A failed verification still
blocks subsequent releases until manually resolved. After a successful
verification, a broken published installer can be replaced without mutating
its old release by dispatching an explicit official upstream_tag with
hotfix_suffix=r1 (or the next unused rN); this creates a separate immutable
source tag and GitHub Release only after the install-and-launch gate passes.
A blocking issue must be resolved and closed before hotfix publication.

## macOS and Linux Desktop

The separate a11y-desktop-unix-v2.x.y release contains unsigned macOS
Intel/Apple Silicon DMG and ZIP packages and Linux x64/ARM64 AppImage,
DEB and RPM packages. Four native builders download and verify the
matching personal CLI archive and compare executable bytes after prebuild
and packaging. All installers and their source trees must pass checks
before a draft can be published. Personal app identity and user data are
isolated; the upstream desktop updater is disabled. macOS builds are not
Apple-notarized and may require manual Gatekeeper approval. Install newer
personal releases manually; packages are automatically built and published.

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

If fork Actions are disabled, enable them on the fork. To stop all
pipelines, set PERSONAL_A11Y_STOP=true under Settings > Secrets and
variables > Actions > Variables, or disable all three workflows. Do not edit
the PR branch to manage releases.