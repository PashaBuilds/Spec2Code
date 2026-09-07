<#
.SYNOPSIS
  Vitis `which sdscc` donmasi (S2C-VITIS-HANG-010) icin which.exe stub'unu uygular.

.DESCRIPTION
  Vitis 2023.2 XSCT `app create`, SDSCorePlugin icinde `which sdscc` calistirir; bazi
  Windows makinelerinde (antivirus/EDR, konsol host) bu cocuk surec konsol
  baslatmasinda kilitlenir ve XSCT sonsuza dek bekler. Belirti: platform olusur,
  application projesinde yalniz lscript.ld/README kalir, kaynaklar import edilmez.
  Bu betik <Vitis>\gnuwin\bin\which.exe dosyasini `which.exe.s2cbackup` olarak
  yedekler ve konsol acmayan (GUI-subsystem) stub'u yerine koyar.
  Vitis/XSCT KAPALIYKEN, yonetici PowerShell'de calistirin. Geri almak: restore.ps1

.PARAMETER VitisRoot
  Vitis surum klasoru, orn. C:\Xilinx\Vitis\2023.2
#>
param(
    [Parameter(Mandatory = $true)][string]$VitisRoot
)
$ErrorActionPreference = "Stop"
$target = Join-Path $VitisRoot "gnuwin\bin\which.exe"
$backup = "$target.s2cbackup"
$stub = Join-Path $PSScriptRoot "which.exe"
if (-not (Test-Path $target)) { throw "which.exe bulunamadi: $target (VitisRoot dogru mu?)" }
if (-not (Test-Path $stub)) { throw "stub bulunamadi: $stub" }
if (Test-Path $backup) {
    Write-Host "Yedek zaten var, korunuyor: $backup"
} else {
    Copy-Item $target $backup
    Write-Host "Orijinal yedeklendi: $backup"
}
Copy-Item $stub $target -Force
Write-Host "Stub uygulandi: $target"
Write-Host "Not: Vitis'i yeniden baslatin; takili kalmis eski which.exe surecleri yeniden baslatmaya kadar kalabilir (zararsiz)."
