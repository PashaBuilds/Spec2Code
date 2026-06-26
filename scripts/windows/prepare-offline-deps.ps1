param(
  [string]$Python = "py",
  [string]$PythonVersion = "-3.12",
  [string]$OfflineRoot = "offline"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

if (!(Test-Path "requirements.txt") -or !(Test-Path "frontend\package-lock.json")) {
  throw "Run this script from a Spec2Code source checkout."
}

$OfflineRootPath = (New-Item -ItemType Directory -Force -Path $OfflineRoot).FullName
$Wheels = Join-Path $OfflineRootPath "wheels"
$NpmCache = Join-Path $OfflineRootPath "npm-cache"
New-Item -ItemType Directory -Force -Path $Wheels | Out-Null
New-Item -ItemType Directory -Force -Path $NpmCache | Out-Null

function Invoke-Python {
  param([string[]]$Arguments)
  if ($PythonVersion -eq "") {
    & $Python @Arguments
  }
  else {
    & $Python $PythonVersion @Arguments
  }
}

Write-Host "Downloading Python wheels to $Wheels"
Invoke-Python -Arguments @("-m", "pip", "download", "--dest", $Wheels, "-r", "requirements.txt")

Write-Host "Populating npm cache at $NpmCache"
Push-Location frontend
try {
  npm ci --cache $NpmCache --prefer-offline
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Offline dependency cache is ready: $OfflineRoot"
Write-Host "Copy this folder next to the Spec2Code source tree on the air-gapped Windows host."
