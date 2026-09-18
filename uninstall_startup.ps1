$p=Join-Path ([Environment]::GetFolderPath("Startup")) "EDGEGUARD Guardian.lnk"; if(Test-Path $p){Remove-Item $p -Force}; Write-Host "EDGEGUARD startup removed."
