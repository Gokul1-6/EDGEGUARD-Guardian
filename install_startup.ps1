$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python).Source
$Vbs = Join-Path $Project "run_hidden.vbs"
@"
Set shell = CreateObject("WScript.Shell")
shell.Run ""$Python"" & " """$Project\agent.py"""", 0, False
"@ | Set-Content -Encoding ASCII $Vbs
$Startup=[Environment]::GetFolderPath("Startup")
$ShortcutPath=Join-Path $Startup "EDGEGUARD Guardian.lnk"
$w=New-Object -ComObject WScript.Shell
$s=$w.CreateShortcut($ShortcutPath);$s.TargetPath=$Vbs;$s.WorkingDirectory=$Project;$s.Save()
Write-Host "EDGEGUARD startup installed for the current Windows user."
