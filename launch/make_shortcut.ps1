# One-time setup: creates a "TopRepo Agent" icon on the Desktop that
# silently starts the web server (in WSL) and opens it in the browser --
# see README.md in this folder for how to run this script and what to
# do afterward.

$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$here = $PSScriptRoot

$shortcut = $ws.CreateShortcut("$desktop\TopRepo Agent.lnk")
$shortcut.TargetPath = "$here\TopRepo Agent.vbs"
$shortcut.WorkingDirectory = $here
$shortcut.IconLocation = "shell32.dll,13"
$shortcut.Description = "Open the TopRepo Agent web UI"
$shortcut.Save()

Write-Host "Desktop shortcut created: TopRepo Agent"
Write-Host "Double-click it any time to open the web UI -- no console window, no typing a command."
