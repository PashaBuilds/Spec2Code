<#
.SYNOPSIS
  apply.ps1 ile degistirilen Vitis which.exe dosyasini yedekten geri yukler.
#>
param(
    [Parameter(Mandatory = $true)][string]$VitisRoot
)
$ErrorActionPreference = "Stop"
$target = Join-Path $VitisRoot "gnuwin\bin\which.exe"
$backup = "$target.s2cbackup"
if (-not (Test-Path $backup)) { throw "Yedek yok: $backup (apply.ps1 hic uygulanmamis)" }
Copy-Item $backup $target -Force
Remove-Item $backup
Write-Host "Orijinal which.exe geri yuklendi: $target"
