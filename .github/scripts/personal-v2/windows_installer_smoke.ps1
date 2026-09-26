param(
  [Parameter(Mandatory = $true)][string]$Installer,
  [Parameter(Mandatory = $true)][string]$ExpectedCliHash,
  [Parameter(Mandatory = $true)][string]$ReportDir
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
$summary = @{ installer = (Resolve-Path $Installer).Path; installed = $false; ui = $false }
try {
  if ($ExpectedCliHash -notmatch '^[a-f0-9]{64}$') { throw 'Invalid expected personal CLI hash.' }
  $programs = Join-Path $env:LOCALAPPDATA 'Programs'
  $before = @(Get-ChildItem -Path $programs -Recurse -File -Filter 'opencode-a11y-desktop.exe' -ErrorAction SilentlyContinue)
  if ($before.Count -ne 0) { throw 'Runner has a pre-existing personal Desktop installation: refusing a contaminated test.' }
  $install = Start-Process -FilePath (Resolve-Path $Installer).Path -ArgumentList '/S' -PassThru
  $summary.installerPid = $install.Id
  if (!$install.WaitForExit(480000)) {
    & taskkill.exe /T /F /PID $install.Id 2>$null
    throw 'Silent NSIS installation exceeded 8 minutes.'
  }
  $install.Refresh()
  $summary.installerExitCode = $install.ExitCode
  if ($install.ExitCode -ne 0) { throw "NSIS exited with code $($install.ExitCode)." }
  $deadline = (Get-Date).AddSeconds(90)
  do {
    $found = @(Get-ChildItem -Path $programs -Recurse -File -Filter 'opencode-a11y-desktop.exe' -ErrorAction SilentlyContinue)
    if ($found.Count -eq 1) { break }
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)
  if ($found.Count -ne 1) { throw "Expected one installed personal Desktop exe; found $($found.Count)." }
  $desktop = $found[0].FullName
  $root = Split-Path $desktop
  $embedded = Join-Path $root 'resources/opencode-cli.exe'
  $versionFile = Join-Path $root 'resources/opencode-cli.version'
  $summary.desktopExe = $desktop
  if (!(Test-Path $embedded) -or !(Test-Path $versionFile)) {
    throw 'The installed application lacks its CLI executable or version marker.'
  }
  $actual = (Get-FileHash $embedded -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne $ExpectedCliHash) { throw "Installed CLI hash mismatch: $actual" }
  $summary.cliSha256 = $actual
  $summary.cliVersion = (Get-Content $versionFile -Raw).Trim()
  if ($summary.cliVersion -notmatch '^2\.[0-9]+\.[0-9]+$') { throw 'Installed CLI version marker is invalid.' }
  $summary.installed = $true
  # An NSIS one-click installer may auto-launch the app; ensure the test owns the first instance.
  @(Get-Process -Name 'opencode-a11y-desktop' -ErrorAction SilentlyContinue) | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $nodeTest = Join-Path $PSScriptRoot 'windows_ui_smoke.mjs'
  & node $nodeTest $desktop $ReportDir
  if ($LASTEXITCODE -ne 0) { throw "Packaged Desktop GUI smoke test failed with exit code $LASTEXITCODE." }
  $summary.ui = $true
  Write-Host "PASS: installed NSIS, verified embedded personal CLI hash, loaded usable Windows GUI."
} catch {
  $summary.failure = $_.Exception.Message
  throw
} finally {
  $summary | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $ReportDir 'installer-result.json')
}
