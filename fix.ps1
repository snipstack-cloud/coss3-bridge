# Cossacks 3 bridge - one-shot fix and verify.  ASCII only.
# Run from this folder:  powershell -ExecutionPolicy Bypass -File .\fix.ps1

param([switch]$OnlyHeartbeat)

$ErrorActionPreference = "Continue"
function Say($t) { Write-Host $t }

Say "=== Cossacks 3 bridge: fix and verify ==="

# --- find the game ----------------------------------------------------------
$steam = $null
foreach ($k in @('HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
    $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
    if ($p -ne $null) {
        if ($p.SteamPath)   { $steam = $p.SteamPath }
        if ($p.InstallPath) { $steam = $p.InstallPath }
    }
    if ($steam -ne $null) { break }
}
$game = $null
if ($steam -ne $null) {
    $roots = @($steam)
    $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
    if (Test-Path $vdf) {
        foreach ($m in ([regex]'"path"\s+"(.+?)"').Matches((Get-Content $vdf -Raw))) {
            $roots += ($m.Groups[1].Value -replace '\\\\', '\')
        }
    }
    foreach ($r in $roots) {
        $c = Join-Path $r "steamapps\common\Cossacks 3"
        if ($game -eq $null -and (Test-Path (Join-Path $c "cossacks.exe"))) { $game = $c }
    }
}
if ($game -eq $null) { Say "GAME NOT FOUND - abort"; exit 1 }
Say ("game   : " + $game)

$target = Join-Path $game "data\scripts\units\global.inc\progresseconomicai.inc"

# --- state before -----------------------------------------------------------
$badBefore = @(Select-String -Path $target -Pattern "GetAppSaveDirectoryPath" -ErrorAction SilentlyContinue).Count
Say ("before : GetAppSaveDirectoryPath found " + $badBefore + " time(s)")

# --- find python ------------------------------------------------------------
$py = $null
foreach ($cand in @("python", "py", "python3")) {
    $c = Get-Command $cand -ErrorAction SilentlyContinue
    if ($c -ne $null -and $py -eq $null) { $py = $cand }
}
if ($py -eq $null) {
    Say "PYTHON NOT FOUND on PATH."
    Say "Install Python 3 from https://www.python.org/downloads/ (tick 'Add to PATH'),"
    Say "then run this script again."
    exit 1
}
Say ("python : " + $py)

# --- output directory -------------------------------------------------------
$outdir = Join-Path $env:USERPROFILE "coss3-io"
if (-not (Test-Path $outdir)) { New-Item -ItemType Directory -Path $outdir | Out-Null }
Say ("outdir : " + $outdir + "   <- game folder in Program Files is NOT writable")

# --- reinstall --------------------------------------------------------------
Say ""
Say "--- running installer ---"
$args = @((Join-Path $PSScriptRoot "install_bridge.py"), $game, "--reinstall", "--outdir", $outdir)
if ($OnlyHeartbeat) { $args += "--only-state"; Say "MODE   : state block only (bisection)" }
& $py $args
Say "--- installer done ---"
Say ""

# --- state after ------------------------------------------------------------
$badAfter = @(Select-String -Path $target -Pattern "GetAppSaveDirectoryPath" -ErrorAction SilentlyContinue).Count
$blocks   = @(Select-String -Path $target -Pattern "=== (PEACE-TIME BUILD ORDER BRIDGE: import|BRIDGE STATE)").Count
$want     = 2
if ($OnlyHeartbeat) { $want = 1 }
$paths    = @(Select-String -Path $target -Pattern "coss3_(eco|cmd)_P")

Say ("after  : GetAppSaveDirectoryPath found " + $badAfter + " time(s)")
Say ("blocks : " + $blocks + "  (expect " + $want + ")")
foreach ($h in $paths) { Say ("  line " + $h.LineNumber + ": " + $h.Line.Trim()) }

Say ""
Say "--- where does the engine write? (its own files) ---"
$probe = @($game, $env:USERPROFILE, "$env:LOCALAPPDATA", "$env:APPDATA", "C:\ProgramData")
$eng = @()
foreach ($d in $probe) {
    if (Test-Path $d) {
        $eng += @(Get-ChildItem $d -Recurse -Include resource.lib,mods.restore -EA 0 | Select-Object -First 5)
    }
}
if ($eng.Count -eq 0) { Say "  no resource.lib / mods.restore found yet" }
foreach ($e in $eng) { Say ("  " + $e.FullName + "   " + $e.LastWriteTime.ToString("s")) }

Say ""
if ($blocks -eq $want) {
    Say "RESULT : OK - fixed bridge is installed."
    Say ""
    Say "Next:"
    Say "  1. Launch the game."
    Say "  2. Single player -> Random map."
    Say "  3. Make sure at least one opponent is a COMPUTER player."
    Say "  4. Start the battle, wait 3 minutes, then quit."
    Say "  5. Run:  powershell -ExecutionPolicy Bypass -File .\find_dat.ps1"
    Say ""
    Say ("Bridge files appear in: " + $outdir)
    Say "  coss3_eco_P<n>.dat = game state, every AI tick"
    Say "  coss3_map_P<n>.dat = terrain layer, rebuilt every 20 game seconds"
    Say ""
    Say ("  Show the situation:  python coss3_map.py '" + $outdir + "' <plind>")
} else {
    Say "RESULT : SOMETHING IS WRONG - send this whole output."
}
