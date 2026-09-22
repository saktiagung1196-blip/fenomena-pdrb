$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $folder "jalankan_auto_update_riau.bat"

$action = New-ScheduledTaskAction -Execute $bat
$trigger = New-ScheduledTaskTrigger -Daily -At 06:00
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName "Auto Update Berita Riau" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Menjalankan app_berita_riau_final.py --collect setiap hari pukul 06.00." `
    -Force

Write-Host "Task Auto Update Berita Riau berhasil dibuat." -ForegroundColor Green
Write-Host "Jadwal: setiap hari pukul 06.00"
Write-Host "Untuk tes: Start-ScheduledTask -TaskName 'Auto Update Berita Riau'"
