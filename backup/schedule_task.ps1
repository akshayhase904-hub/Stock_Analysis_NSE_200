$action = New-ScheduledTaskAction -Execute "c:\Akshay\Share_Market_Analysis\dist\main\main.exe" -Argument "--auto-run"
$trigger = New-ScheduledTaskTrigger -Daily -At 9:30AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName "Nifty 200 AI Swing Trader" -Description "Runs the AI Swing Trading analysis every morning at 9:30 AM" -Force
Write-Host "Task successfully scheduled for 9:30 AM every day!"
Read-Host "Press Enter to exit..."

