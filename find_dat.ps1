# Cossacks 3 bridge - find and dump the state file.  ASCII only.
# Run:  powershell -ExecutionPolicy Bypass -File .\find_dat.ps1
# Optional explicit game path:  ... -File .\find_dat.ps1 "D:\Games\Cossacks 3"

param([string]$GamePath = "")

$ErrorActionPreference = "Continue"
$out = New-Object System.Collections.ArrayList
function Say($t) { Write-Host $t; [void]$out.Add([string]$t) }

Say "=== Cossacks 3 bridge: find state file ==="
Say ("date : " + (Get-Date -Format s))

# --- where to look ----------------------------------------------------------
$roots = @()
if ($GamePath -ne "" -and (Test-Path $GamePath)) {
    $roots += $GamePath
} else {
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
        $roots += (Join-Path $steam "steamapps\common\Cossacks 3")
        $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            $raw = Get-Content $vdf -Raw
            foreach ($m in ([regex]'"path"\s+"(.+?)"').Matches($raw)) {
                $lib = $m.Groups[1].Value -replace '\\\\', '\'
                $roots += (Join-Path $lib "steamapps\common\Cossacks 3")
            }
        }
    }
}
$roots += $env:USERPROFILE

$found = @()
foreach ($r in $roots) {
    if (Test-Path $r) {
        Say ("scan : " + $r)
        $hits = @(Get-ChildItem -LiteralPath $r -Recurse -Filter "coss3_*.dat" -ErrorAction SilentlyContinue)
        foreach ($h in $hits) { $found += $h }
    }
}

$found = $found | Sort-Object FullName -Unique
Say ("found: " + $found.Count + " file(s)")

if ($found.Count -eq 0) {
    Say ""
    Say "NOTHING FOUND. Checklist:"
    Say "  1. Did you actually play a skirmish WITH A COMPUTER OPPONENT?"
    Say "     The bridge only runs for AI players (guarded by 'if (bai)')."
    Say "  2. Did the match run for a minute or more?"
    Say "  3. Is the bridge still installed? Steam file verification removes it."
    $out -join "`r`n" | Set-Content (Join-Path $PSScriptRoot "find_dat.txt") -Encoding UTF8
    exit 1
}

foreach ($f in $found) {
    Say ""
    Say ("file : " + $f.FullName)
    Say ("size : " + $f.Length + " bytes,  modified " + $f.LastWriteTime.ToString("s"))
}

# --- dump the newest one ----------------------------------------------------
$newest = $found | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Say ""
Say ("=== CONTENT OF " + $newest.Name + " (first 60 lines) ===")
$i = 0
foreach ($line in (Get-Content -LiteralPath $newest.FullName -TotalCount 60)) {
    $i++
    Say ("{0,3}| {1}" -f $i, $line)
}
Say "=== END OF CONTENT ==="

$path = Join-Path $PSScriptRoot "find_dat.txt"
$out -join "`r`n" | Set-Content $path -Encoding UTF8
Say ""
Say ("report saved: " + $path)
