$chronosExe = "$env:LOCALAPPDATA\Chronos\chronos.exe"
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

if (Test-Path $chronosExe) {
    Set-ItemProperty -Path $regPath -Name "Chronos" -Value $chronosExe
    Write-Host "Chronos added to Windows startup."
} else {
    Write-Host "Chronos executable not found at $chronosExe"
}
