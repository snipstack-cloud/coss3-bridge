# Cossacks 3 bridge - live watcher.  ASCII only.
#
#   powershell -ExecutionPolicy Bypass -File .\watch.ps1
#   powershell -ExecutionPolicy Bypass -File .\watch.ps1 -Launch
#   powershell -ExecutionPolicy Bypass -File .\watch.ps1 -Launch -Minutes 15
#
# Watches the game folder while you play and reports everything the game writes.
# Stop with Ctrl+C.  Full log goes to watch.txt next to this script.

param([switch]$Launch, [int]$Minutes = 10, [string]$GamePath = "")

$ErrorActionPreference = "Continue"
$log = New-Object System.Collections.ArrayList
function Say($t) {
    $line = "[" + (Get-Date -Format "HH:mm:ss") + "] " + $t
    Write-Host $line
    [void]$log.Add($line)
}
function Flush() {
    $log -join "`r`n" | Set-Content (Join-Path $PSScriptRoot "watch.txt") -Encoding UTF8
}

Say "=== Cossacks 3 bridge: live watch ==="

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
}
if ($game -eq $null) { Say "GAME NOT FOUND - abort"; Flush; exit 1 }
Say ("game    : " + $game)

# --- bridge sanity ----------------------------------------------------------
$target = Join-Path $game "data\scripts\units\global.inc\progresseconomicai.inc"
# Current installer marks the two blocks separately.  The old scheme used the
# same "PEACE-TIME" marker twice, so counting that one alone always gives 1
# and produced a false warning.
$impo = @(Select-String -Path $target -Pattern "=== PEACE-TIME BUILD ORDER BRIDGE: import commands" -EA 0).Count
$stat = @(Select-String -Path $target -Pattern "=== BRIDGE STATE" -EA 0).Count
$bad  = @(Select-String -Path $target -Pattern "GetAppSaveDirectoryPath" -EA 0).Count
Say ("bridge  : import=" + $impo + "  state=" + $stat + "  broken_calls=" + $bad)
if ($impo -lt 1 -or $stat -lt 1) {
    Say "WARNING : bridge blocks missing. Reinstall: python install_bridge.py <game> --reinstall"
} elseif ($bad -ne 0) {
    Say "WARNING : file reads in the interface actor - this kills the state block."
} else {
    Say "bridge  : OK"
}

# --- baseline ---------------------------------------------------------------
$start = Get-Date
Say "scanning baseline (this takes a few seconds)..."
$outdir = Join-Path $env:USERPROFILE "coss3-io"
if (-not (Test-Path $outdir)) { New-Item -ItemType Directory -Path $outdir | Out-Null }
$watched = @($game, $outdir)
Say ("outdir  : " + $outdir)
$before = @{}
foreach ($w in $watched) {
    foreach ($f in (Get-ChildItem $w -Recurse -File -EA 0)) { $before[$f.FullName] = $f.LastWriteTime }
}
Say ("baseline: " + $before.Count + " files")

# --- launch -----------------------------------------------------------------
if ($Launch) {
    Say "launching via steam://rungameid/333420 ..."
    Start-Process "steam://rungameid/333420"
}

Say ""
Say "WATCHING. Play a Random Map skirmish WITH A COMPUTER OPPONENT."
Say ("Will run for " + $Minutes + " minutes. Ctrl+C to stop early.")
Say ""

# --- watch loop -------------------------------------------------------------
$deadline  = $start.AddMinutes($Minutes)
$seenProc  = $false
$dumped    = @{}
$reported  = @{}
$ticks     = 0

while ((Get-Date) -lt $deadline) {
    $ticks++

    $proc = @(Get-Process -Name cossacks -EA 0)
    if ($proc.Count -gt 0 -and -not $seenProc) {
        Say ("PROCESS : cossacks.exe started, pid " + $proc[0].Id)
        $seenProc = $true
    } elseif ($proc.Count -eq 0 -and $seenProc) {
        Say "PROCESS : cossacks.exe exited"
        $seenProc = $false
    }

    foreach ($f in ($watched | ForEach-Object { Get-ChildItem $_ -Recurse -File -EA 0 })) {
        $isNew = -not $before.ContainsKey($f.FullName)
        $isMod = (-not $isNew) -and ($f.LastWriteTime -gt $before[$f.FullName])
        if (-not ($isNew -or $isMod)) { continue }
        $before[$f.FullName] = $f.LastWriteTime
        $short = $f.FullName.Replace($game, "<game>").Replace($outdir, "<out>")
        $key   = $short + "|" + $f.Length
        if ($reported.ContainsKey($key)) { continue }
        $reported[$key] = $true
        $tag = "MODIFIED"
        if ($isNew) { $tag = "NEW     " }
        Say ($tag + ": " + $short + "  (" + $f.Length + " bytes)")

        if ($f.Name -like "coss3_*") {
            if (-not $dumped.ContainsKey($f.Name)) {
                $dumped[$f.Name] = $true
                Say ""
                Say ("*** BRIDGE IS ALIVE - content of " + $f.Name + " ***")
                $n = 0
                foreach ($line in (Get-Content -LiteralPath $f.FullName -EA 0)) {
                    $n++
                    Say ("  " + $n.ToString().PadLeft(3) + "| " + $line)
                }
                Say "*** end of content ***"
                Say ""
            }
        }
    }

    if ($ticks % 20 -eq 0) { Flush }
    Start-Sleep -Seconds 3
}

# --- summary ----------------------------------------------------------------
Say ""
Say "--- summary ---"
$dat = @($watched | ForEach-Object { Get-ChildItem $_ -Recurse -Filter "coss3_*.dat" -EA 0 })
Say ("coss3_*.dat files : " + $dat.Count)
foreach ($d in $dat) { Say ("  " + $d.FullName + "  " + $d.Length + " bytes  " + $d.LastWriteTime.ToString("s")) }
if ($dat.Count -eq 0) {
    Say "  Bridge did NOT write anything."
    Say "  -> Did the match actually include a COMPUTER opponent?"
    Say "  -> If yes, the script section is probably failing to compile."
}
Flush
Say ("report saved: " + (Join-Path $PSScriptRoot "watch.txt"))
