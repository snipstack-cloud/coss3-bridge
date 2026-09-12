# Cossacks 3 bridge - remove the bridge completely (control experiment).
# Run:  powershell -ExecutionPolicy Bypass -File .\off.ps1
# Put it back with:  powershell -ExecutionPolicy Bypass -File .\fix.ps1

$ErrorActionPreference = "Continue"
function Say($t) { Write-Host $t }

Say "=== Cossacks 3 bridge: UNINSTALL (control test) ==="

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
Say ("game : " + $game)

$py = $null
foreach ($cand in @("python", "py", "python3")) {
    $c = Get-Command $cand -ErrorAction SilentlyContinue
    if ($c -ne $null -and $py -eq $null) { $py = $cand }
}
if ($py -eq $null) { Say "PYTHON NOT FOUND on PATH - abort"; exit 1 }

& $py (Join-Path $PSScriptRoot "install_bridge.py") $game "--uninstall"

$target = Join-Path $game "data\scripts\units\global.inc\progresseconomicai.inc"
$left  = @(Select-String -Path $target -Pattern "BRIDGE" -EA 0).Count
$lines = (Get-Content $target).Count

# Anything left over -> fall back to the OLDEST backup. copy2 preserved the
# original file date, so the oldest .bak is the pristine untouched file.
if ($left -ne 0 -or $lines -ne 3924) {
    Say ""
    Say "not clean - falling back to the oldest backup"
    $baks = @(Get-ChildItem (Split-Path $target) -Filter "*.bak-*" -EA 0 | Sort-Object LastWriteTime)
    foreach ($b in $baks) { Say ("  " + $b.Name + "  " + $b.LastWriteTime.ToString("s") + "  " + $b.Length) }
    if ($baks.Count -gt 0) {
        Say ("restoring from: " + $baks[0].Name)
        Copy-Item $baks[0].FullName $target -Force
        $left  = @(Select-String -Path $target -Pattern "BRIDGE" -EA 0).Count
        $lines = (Get-Content $target).Count
    }
}

Say ""
Say ("bridge markers left : " + $left + "   (expect 0)")
Say ("lines               : " + $lines + "  (original is 3924)")
if ($left -eq 0 -and $lines -eq 3924) {
    Say "RESULT : clean original restored."
} else {
    Say "RESULT : NOT clean - send this output."
}
Say ""
Say "Now launch the game and play a skirmish against the SAME AI opponent."
Say "Question: does the AI build anything - new buildings, busy peasants?"
