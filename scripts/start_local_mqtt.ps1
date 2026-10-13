param(
    [string]$EnvironmentPath = "E:\Anaconda\envs\edge-ecg-tf215",
    [string]$ConfigPath = "$PSScriptRoot\..\config\mosquitto-experiment.conf"
)

$brokerCandidates = @(
    (Join-Path $EnvironmentPath "Library\bin\mosquitto.exe"),
    (Join-Path $EnvironmentPath "Library\sbin\mosquitto.exe")
)
$broker = $brokerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $broker) {
    throw "Mosquitto is not installed under $EnvironmentPath\Library\bin or $EnvironmentPath\Library\sbin"
}
$resolvedConfig = (Resolve-Path -LiteralPath $ConfigPath).Path
$process = Start-Process -FilePath $broker -ArgumentList @("-c", ('"{0}"' -f $resolvedConfig)) -WindowStyle Hidden -PassThru
$ready = $false
for ($attempt = 0; $attempt -lt 50; $attempt++) {
    if (Test-NetConnection 127.0.0.1 -Port 1883 -InformationLevel Quiet -WarningAction SilentlyContinue) {
        $ready = $true
        break
    }
    Start-Sleep -Milliseconds 100
}
if (-not $ready) {
    Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
    throw "Mosquitto did not become ready on 127.0.0.1:1883"
}
[pscustomobject]@{ ProcessId = $process.Id; Broker = $broker; Config = $resolvedConfig; Listener = "127.0.0.1:1883" }
