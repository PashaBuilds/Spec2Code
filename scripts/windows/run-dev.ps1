param(
  [string]$HostName = "127.0.0.1",
  [int]$BackendPort = 8077
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
  throw "Python venv not found. Run scripts\windows\setup-source.ps1 first."
}

Write-Host "Starting backend on http://${HostName}:$BackendPort"
$BackendArgs = @(
  "-m", "uvicorn",
  "backend.main:app",
  "--host", $HostName,
  "--port", "$BackendPort"
)
Start-Process -FilePath $Python -ArgumentList $BackendArgs -WorkingDirectory $Root

Write-Host "Starting Vite dev server on http://localhost:5181"
Push-Location frontend
try {
  npm run dev
}
finally {
  Pop-Location
}
