# Cossacks 3 bridge - console overlay on top of the game.  ASCII only.
#
#   powershell -ExecutionPolicy Bypass -File .\overlay.ps1
#   powershell -ExecutionPolicy Bypass -File .\overlay.ps1 -Opacity 0.35 -Lines 18
#   powershell -ExecutionPolicy Bypass -File .\overlay.ps1 -ClickThrough
#
# Shows the tail of coss3_llm.log (written by llm_policy.py --log) in a small
# always-on-top window in the top right corner, so you can watch the decisions
# without alt-tabbing out of the game.  Default 400x200 fits a full line of the
# model's explanation without cutting it; -Width 200 makes it smaller again.
#
# IMPORTANT: an overlay cannot draw over EXCLUSIVE FULLSCREEN.  Set the game to
# windowed or borderless window mode, otherwise the window will be hidden.
#
# Close it: double-click the window, press Esc, or close this PowerShell window.
# With -ClickThrough the window ignores the mouse (so it never steals a click
# from the game) - then close it from the console with Ctrl+C.

param(
    [string]$Log = "",
    [int]$Width = 400,
    [int]$Height = 200,
    [double]$Opacity = 0.5,
    [int]$Lines = 16,
    [int]$MaxChars = 0,
    [int]$FontSize = 8,
    [int]$Margin = 8,
    [int]$RefreshMs = 700,
    [switch]$ClickThrough
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Long lines wrap and flood a 200px window, so we cut them to fit.  Consolas
# glyph width is about 0.62 of the font size in pixels.
if ($MaxChars -le 0) {
    $MaxChars = [Math]::Max(16, [int]($Width / ($FontSize * 0.62)) - 1)
}

if ([string]::IsNullOrEmpty($Log)) {
    $Log = Join-Path $PSScriptRoot "coss3_llm.log"
}
Write-Host ("overlay: watching " + $Log)
Write-Host ("overlay: " + $Width + "x" + $Height + " at top right, opacity " + $Opacity)
Write-Host "overlay: game must be in WINDOWED or BORDERLESS mode, not exclusive fullscreen"
Write-Host ("overlay: " + $Lines + " lines, cut at " + $MaxChars + " chars")
Write-Host "overlay: Esc or double-click to close"

# --- window -----------------------------------------------------------------
$form = New-Object System.Windows.Forms.Form
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.Width = $Width
$form.Height = $Height
$form.Opacity = $Opacity
$form.BackColor = [System.Drawing.Color]::Black

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$form.Left = $screen.Right - $Width - $Margin
$form.Top = $screen.Top + $Margin

$label = New-Object System.Windows.Forms.Label
$label.Dock = [System.Windows.Forms.DockStyle]::Fill
$label.BackColor = [System.Drawing.Color]::Black
$label.ForeColor = [System.Drawing.Color]::FromArgb(180, 255, 120)
$label.Font = New-Object System.Drawing.Font("Consolas", $FontSize)
$label.Text = "waiting for the log..."
$form.Controls.Add($label)

# --- click-through (optional) ----------------------------------------------
# WS_EX_LAYERED | WS_EX_TRANSPARENT makes the window ignore the mouse entirely,
# so a click goes to the game underneath instead of to the overlay.
if ($ClickThrough) {
    $script:form = $form
    $sig = @"
using System;
using System.Runtime.InteropServices;
public class OverlayNative {
    [DllImport("user32.dll", SetLastError=true)]
    public static extern int GetWindowLong(IntPtr hWnd, int nIndex);
    [DllImport("user32.dll", SetLastError=true)]
    public static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);
}
"@
    Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue
    $form.Add_Shown({
        $GWL_EXSTYLE = -20
        $WS_EX_LAYERED = 0x80000
        $WS_EX_TRANSPARENT = 0x20
        $st = [OverlayNative]::GetWindowLong($script:form.Handle, $GWL_EXSTYLE)
        [void][OverlayNative]::SetWindowLong($script:form.Handle, $GWL_EXSTYLE,
            $st -bor $WS_EX_LAYERED -bor $WS_EX_TRANSPARENT)
    })
    Write-Host "overlay: click-through is ON - close with Ctrl+C here"
}

# --- reading the tail -------------------------------------------------------
# The log is open for writing by python, so we must share read AND write,
# otherwise every read throws "file is being used by another process".
function Read-Tail([string]$path, [int]$count, [int]$cut) {
    if (-not (Test-Path $path)) { return "no log yet: " + [System.IO.Path]::GetFileName($path) }
    try {
        $fs = New-Object System.IO.FileStream($path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite)
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
        $all = $sr.ReadToEnd()
        $sr.Close(); $fs.Close()
    } catch {
        return "log is locked"
    }
    $rows = @($all -split "`r?`n" | Where-Object { $_.Trim() -ne "" })
    if ($rows.Count -eq 0) { return "log is empty" }
    $take = [Math]::Min($count, $rows.Count)
    $tail = $rows[($rows.Count - $take)..($rows.Count - 1)]
    # The console uses an 8-space indent for sub-lines; in a 200px window that
    # is a quarter of the width, so squeeze it down to two.
    $short = foreach ($r in $tail) {
        $t = $r -replace "^\s{3,}", "  "
        if ($t.Length -gt $cut) { $t.Substring(0, $cut - 1) + [char]0x2026 } else { $t }
    }
    return ($short -join "`n")
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = $RefreshMs
$script:Log = $Log
$script:Lines = $Lines
$script:MaxChars = $MaxChars
$script:label = $label
$timer.Add_Tick({
    $script:label.Text = Read-Tail $script:Log $script:Lines $script:MaxChars
})
$timer.Start()

$script:form = $form
$form.Add_DoubleClick({ $script:form.Close() })
$label.Add_DoubleClick({ $script:form.Close() })
$form.Add_KeyDown({ if ($_.KeyCode -eq [System.Windows.Forms.Keys]::Escape) { $script:form.Close() } })
$form.KeyPreview = $true

[void][System.Windows.Forms.Application]::Run($form)
$timer.Stop()
Write-Host "overlay: closed"
