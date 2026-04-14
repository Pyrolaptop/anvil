# Creates a desktop shortcut that launches Anvil without a console window.
# Re-run this any time you want the shortcut back.

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Anvil.lnk"

# Prefer pythonw.exe (no console). Fall back to python.exe if pythonw isn't found.
$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue)
if ($pyw) {
    $target = $pyw.Source
} else {
    $target = (Get-Command python.exe).Source
}

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($shortcutPath)
$s.TargetPath = $target
$s.Arguments = "-m anvil"
$s.WorkingDirectory = $projectRoot
$s.IconLocation = "$target, 0"
$s.Description = "Anvil - local AI assistant"
$s.WindowStyle = 1
$s.Save()

Write-Host "Created shortcut: $shortcutPath"
Write-Host "  Target:  $target -m anvil"
Write-Host "  CWD:     $projectRoot"
