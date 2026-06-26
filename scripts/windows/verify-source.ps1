param(
  [switch]$SkipSelftest
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
  throw "Python venv not found. Run scripts\windows\setup-source.ps1 first."
}

Write-Host "Tool resolution:"
& $Python -c "from hostplat import tools; import json; print(json.dumps(tools.status(), indent=2))"

Write-Host ""
Write-Host "CRLF output probe:"
& $Python -c 'from hostplat import io; p=io.write_output("outputs/_crlf_probe.txt","a\nb\n"); print(io.detect_line_ending(p))'

if (!$SkipSelftest) {
  Write-Host ""
  Write-Host "Running deterministic selftest:"
  & $Python -m orchestrator.selftest
}

Write-Host ""
Write-Host "Verification complete."
