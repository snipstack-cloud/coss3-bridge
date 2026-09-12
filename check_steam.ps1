# Cossacks 3 bridge - preflight check.  ASCII only on purpose.
# Run:  powershell -ExecutionPolicy Bypass -File .\check_steam.ps1
# Or:   powershell -ExecutionPolicy Bypass -File .\check_steam.ps1 "D:\Games\Cossacks 3"

param([string]$GamePath = "")

$ErrorActionPreference = "Continue"
$out = New-Object System.Collections.ArrayList
function Say($t) { Write-Host $t; [void]$out.Add([string]$t) }

Say "=== Cossacks 3 bridge: preflight ==="
Say ("date      : " + (Get-Date -Format s))
Say ("psversion : " + $PSVersionTable.PSVersion.ToString())

# --- 1. locate the game -----------------------------------------------------
$game = $null
if ($GamePath -ne "" -and (Test-Path (Join-Path $GamePath "cossacks.exe"))) {
    $game = $GamePath
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
    if ($steam -ne $null) { Say ("steam     : " + $steam) } else { Say "steam     : NOT FOUND in registry" }

    $libs = @()
    if ($steam -ne $null) {
        $libs += $steam
        $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            $raw = Get-Content $vdf -Raw
            foreach ($m in ([regex]'"path"\s+"(.+?)"').Matches($raw)) {
                $libs += ($m.Groups[1].Value -replace '\\\\', '\')
            }
        }
    }
    $libs += "C:\GOG Games\Cossacks 3"
    $libs += "C:\Program Files (x86)\Cossacks 3"

    foreach ($l in $libs) {
        if ($game -eq $null) {
            $c1 = Join-Path $l "steamapps\common\Cossacks 3"
            if (Test-Path (Join-Path $c1 "cossacks.exe")) { $game = $c1 }
            elseif (Test-Path (Join-Path $l "cossacks.exe")) { $game = $l }
        }
    }
}

if ($game -eq $null) {
    Say "RESULT    : GAME NOT FOUND"
    Say 'Run again with an explicit path, for example:'
    Say '  powershell -ExecutionPolicy Bypass -File .\check_steam.ps1 "D:\SteamLibrary\steamapps\common\Cossacks 3"'
    $out -join "`r`n" | Set-Content (Join-Path $PSScriptRoot "preflight.txt") -Encoding UTF8
    exit 1
}
Say ("game      : " + $game)

# --- 2. build identity ------------------------------------------------------
$exe = Get-Item (Join-Path $game "cossacks.exe")
Say ("exe size  : " + $exe.Length)
Say ("exe date  : " + $exe.LastWriteTime.ToString("s"))
Say ("exe ver   : " + $exe.VersionInfo.FileVersion)

$steamapps = Split-Path (Split-Path $game)
$manifest  = Join-Path $steamapps "appmanifest_333420.acf"
if (Test-Path $manifest) {
    foreach ($line in (Get-Content $manifest)) {
        if ($line -match '"(buildid|name|StateFlags)"\s+"(.+?)"') {
            Say ("steam " + $Matches[1].PadRight(4) + ": " + $Matches[2])
        }
    }
} else {
    Say "manifest  : appmanifest_333420.acf not found"
}

# --- 3. target file and anchors --------------------------------------------
$f = Join-Path $game "data\scripts\units\global.inc\progresseconomicai.inc"
if (-not (Test-Path $f)) {
    Say ("TARGET MISSING: " + $f)
} else {
    $item  = Get-Item $f
    $lines = Get-Content $f
    Say ("target sz : " + $item.Length)
    Say ("target ln : " + $lines.Count)
    Say ("target dt : " + $item.LastWriteTime.ToString("s"))
    $already = @(Select-String -Path $f -Pattern "BRIDGE").Count
    Say ("bridge    : " + $(if ($already -gt 0) { "ALREADY INSTALLED (" + $already + " markers)" } else { "not installed" }))

    $names    = @("EXPORT anchor", "IMPORT anchor")
    $patterns = @("_misc_ProfilerEnd\('EconomicAI\.EnumUnits'\)", "_ai_ResourcesDistributionScript\(plind, maincid")
    for ($i = 0; $i -lt $names.Count; $i++) {
        $hits = @(Select-String -Path $f -Pattern $patterns[$i])
        if ($hits.Count -eq 1) {
            Say ($names[$i] + ": OK, 1 match at line " + $hits[0].LineNumber)
        } elseif ($hits.Count -eq 0) {
            Say ($names[$i] + ": NOT FOUND")
        } else {
            Say ($names[$i] + ": AMBIGUOUS, " + $hits.Count + " matches")
        }
    }
}

$path = Join-Path $PSScriptRoot "preflight.txt"
$out -join "`r`n" | Set-Content $path -Encoding UTF8
Say ""
Say ("report saved: " + $path)
