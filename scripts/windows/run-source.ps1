param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8077,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
  throw "Python venv not found. Run scripts\windows\setup-source.ps1 first."
}

$Args = @("run_spec2code.py", "--host", $HostName, "--port", "$Port")
if ($NoBrowser) {
  $Args += "--no-browser"
}

& $Python @Args
