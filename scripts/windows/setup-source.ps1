param(
  [string]$Python = "py",
  [string]$PythonVersion = "-3.12",
  [string]$OfflineRoot = "",
  [switch]$SkipFrontend,
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

if (!(Test-Path "requirements.txt") -or !(Test-Path "run_spec2code.py")) {
  throw "Run this script from a Spec2Code source checkout."
}

function Invoke-Python {
  param([string[]]$Arguments)
  if ($PythonVersion -eq "") {
    & $Python @Arguments
  }
  else {
    & $Python $PythonVersion @Arguments
  }
}

if (!(Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Creating Python virtual environment"
  Invoke-Python -Arguments @("-m", "venv", ".venv")
}

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip

$OfflineRootPath = ""
if ($OfflineRoot -ne "") {
  if (!(Test-Path $OfflineRoot)) {
    throw "Offline dependency cache not found: $OfflineRoot"
  }
  $OfflineRootPath = (Resolve-Path $OfflineRoot).Path
}

if ($OfflineRoot -ne "") {
  $WheelDir = Join-Path $OfflineRootPath "wheels"
  if (!(Test-Path $WheelDir)) {
    throw "Offline wheel directory not found: $WheelDir"
  }
  Write-Host "Installing Python dependencies from $WheelDir"
  & $VenvPython -m pip install --no-index --find-links $WheelDir -r requirements.txt
}
else {
  Write-Host "Installing Python dependencies from package indexes"
  & $VenvPython -m pip install -r requirements.txt
}

if (!$SkipFrontend) {
  Push-Location frontend
  try {
    if ($OfflineRoot -ne "") {
      $NpmCache = Join-Path $OfflineRootPath "npm-cache"
      if (!(Test-Path $NpmCache)) {
        throw "Offline npm cache directory not found: $NpmCache"
      }
      npm ci --offline --cache $NpmCache
    }
    else {
      npm ci
    }

    if (!$SkipBuild) {
      npm run build
    }
  }
  finally {
    Pop-Location
  }
}

Write-Host ""
Write-Host "Spec2Code source setup is ready."
Write-Host "Run scripts\windows\verify-source.ps1, then scripts\windows\run-source.ps1."
