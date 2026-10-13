param(
    [string]$EnvironmentPath = "E:\Anaconda\envs\edge-ecg-tf215"
)

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $EnvironmentPath "python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found at $python"
}

Push-Location $projectRoot
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $projectRoot "src"
$broker = $null
try {
    & $python -c "import paho.mqtt.client; import tensorflow as tf; assert tf.__version__ == '2.15.1'"
    if ($LASTEXITCODE -ne 0) { throw "Frozen runtime dependency check failed" }
    $broker = & (Join-Path $PSScriptRoot "start_local_mqtt.ps1") -EnvironmentPath $EnvironmentPath
    & $python "src\38_experiment8a_service_loop.py"
    if ($LASTEXITCODE -ne 0) { throw "Experiment 8A failed" }
    & $python "src\39_experiment7_runtime_benchmark.py"
    if ($LASTEXITCODE -ne 0) { throw "Experiment 7 failed" }
    & $python "src\40_gate_v_software_loop_validation.py"
    if ($LASTEXITCODE -ne 0) { throw "Gate V did not pass" }
}
finally {
    if ($null -ne $broker -and $null -ne $broker.ProcessId) {
        Stop-Process -Id $broker.ProcessId -ErrorAction SilentlyContinue
    }
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
