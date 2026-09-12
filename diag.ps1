# Cossacks 3 bridge - full diagnostic.  ASCII only.
# Run:  powershell -ExecutionPolicy Bypass -File .\diag.ps1

param([string]$GamePath = "")

$ErrorActionPreference = "Continue"
$out = New-Object System.Collections.ArrayList
function Say($t) { Write-Host $t; [void]$out.Add([string]$t) }

Say "=== Cossacks 3 bridge: diagnostic ==="
Say ("date : " + (Get-Date -Format s))

# --- locate game ------------------------------------------------------------
$game = $null
if ($GamePath -ne "" -and (Test-Path (Join-Path $GamePath "cossacks.exe"))) { $game = $GamePath }
if ($game -eq $null) {
    $steam = $null
    foreach ($k in @('HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
        $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
        if ($p -ne $null) {
            if ($p.SteamPath)   { $steam = $p.SteamPath }
            if ($p.InstallPath) { $steam = $p.InstallPath }
        }
        if ($steam -ne $null) { break }
    }
    if ($steam -ne $null) {
        $c = Join-Path $steam "steamapps\common\Cossacks 3"
        if (Test-Path (Join-Path $c "cossacks.exe")) { $game = $c }
    }
}
if ($game -eq $null) { Say "GAME NOT FOUND"; exit 1 }
Say ("game : " + $game)

# --- A. state of the patched script ----------------------------------------
Say ""
Say "--- A. bridge state ---"
$f = Join-Path $game "data\scripts\units\global.inc\progresseconomicai.inc"
if (-not (Test-Path $f)) {
    Say "TARGET MISSING"
} else {
    $it = Get-Item $f
    Say ("size          : " + $it.Length)
    Say ("lines         : " + (Get-Content $f).Count)
    Say ("modified      : " + $it.LastWriteTime.ToString("s"))
    $markers = @(Select-String -Path $f -Pattern "=== PEACE-TIME BUILD ORDER BRIDGE").Count
    Say ("bridge blocks : " + $markers + " (expect 2)")
    $bad = @(Select-String -Path $f -Pattern "GetAppSaveDirectoryPath").Count
    if ($bad -gt 0) {
        Say ("VERSION       : OLD/BROKEN - GetAppSaveDirectoryPath found " + $bad + " time(s)")
        Say "                >>> run: python install_bridge.py <game> --reinstall"
    } elseif ($markers -eq 2) {
        Say "VERSION       : FIXED (relative paths) - OK"
    } else {
        Say "VERSION       : bridge NOT installed"
    }
    foreach ($h in @(Select-String -Path $f -Pattern "coss3_(eco|cmd)_P")) {
        Say ("path line " + $h.LineNumber + ": " + $h.Line.Trim())
    }
    $baks = @(Get-ChildItem (Split-Path $f) -Filter "*.bak-*" -EA 0)
    Say ("backups       : " + $baks.Count)
}

# --- B. did the game ever run? ---------------------------------------------
Say ""
Say "--- B. evidence the game ran ---"
$prof = Join-Path $game "data\profiles"
Say ("data\profiles exists : " + (Test-Path $prof))
if (Test-Path $prof) {
    foreach ($d in @(Get-ChildItem $prof -EA 0)) { Say ("  " + $d.Name + "  " + $d.LastWriteTime.ToString("s")) }
}
$saves = @(Get-ChildItem $game -Recurse -Include *.sav,*.rec,*.log -EA 0 | Select-Object -First 10)
Say ("save/log files       : " + $saves.Count)
foreach ($s in $saves) { Say ("  " + $s.FullName.Replace($game, "<game>") + "  " + $s.LastWriteTime.ToString("s")) }

# --- C. what changed in the game folder recently ---------------------------
Say ""
Say "--- C. files in game folder modified in last 48h ---"
$since = (Get-Date).AddHours(-48)
$recent = @(Get-ChildItem $game -Recurse -File -EA 0 | Where-Object { $_.LastWriteTime -gt $since } |
            Sort-Object LastWriteTime -Descending | Select-Object -First 25)
Say ("count : " + $recent.Count)
foreach ($r in $recent) {
    Say ("  " + $r.LastWriteTime.ToString("s") + "  " + $r.Length.ToString().PadLeft(9) + "  " + $r.FullName.Replace($game, "<game>"))
}
if ($recent.Count -eq 0) {
    Say "  NOTHING changed -> the game most likely was never launched after patching."
}

# --- D. is the game running now? -------------------------------------------
Say ""
Say "--- D. process ---"
$proc = @(Get-Process -Name cossacks -EA 0)
Say ("cossacks.exe running : " + $proc.Count)

$path = Join-Path $PSScriptRoot "diag.txt"
$out -join "`r`n" | Set-Content $path -Encoding UTF8
Say ""
Say ("report saved: " + $path)
