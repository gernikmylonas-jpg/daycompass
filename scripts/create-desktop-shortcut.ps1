# Creates a "DayCompass" icon on your Desktop that starts the app and opens it. Run it once:
#   powershell -ExecutionPolicy Bypass -File scripts\create-desktop-shortcut.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'DayCompass.lnk'))
$link.TargetPath = Join-Path $here 'start-daycompass.bat'
$link.WorkingDirectory = Split-Path -Parent $here
$link.IconLocation = Join-Path $here 'daycompass.ico'
$link.WindowStyle = 7  # minimised console
$link.Save()
Write-Host 'Desktop shortcut created.'
