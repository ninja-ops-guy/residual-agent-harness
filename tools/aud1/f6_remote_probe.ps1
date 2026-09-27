param(
    [Parameter(Mandatory=$true)][string]$Label,
    [Parameter(Mandatory=$true)][int]$RunnerPid,
    [string]$StationHost = "127.0.0.1",
    [int]$StationPort = 8765,
    [string]$OutputDir = "$PWD/AUD1-F6-REMOTE",
    [string]$RunnerLog = ""
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("o")

$tcp = @()
try {
    $tcp = Get-NetTCPConnection -ErrorAction Stop |
        Where-Object { $_.OwningProcess -eq $RunnerPid -and ($_.RemotePort -eq $StationPort -or $_.LocalPort -eq $StationPort) } |
        Select-Object State,LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess
} catch {
    $tcp = @(@{ error = $_.Exception.Message })
}

$runnerProcess = $null
try {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $RunnerPid" -ErrorAction Stop
    if ($proc) {
        $runnerProcess = [ordered]@{
            ProcessId = $proc.ProcessId
            Name = $proc.Name
            CreationDate = $proc.CreationDate
            IsResidualWorker = [bool](($proc.Name -match "python") -and ($proc.CommandLine -match "residual\.station\.worker|residual-worker"))
        }
    }
} catch {
    $runnerProcess = @{ error = $_.Exception.Message }
}

$probe = $null
try {
    $probe = Test-NetConnection -ComputerName $StationHost -Port $StationPort -WarningAction SilentlyContinue |
        Select-Object ComputerName,RemoteAddress,RemotePort,SourceAddress,TcpTestSucceeded
} catch {
    $probe = @{ error = $_.Exception.Message }
}

$logEvidence = $null
if ($RunnerLog -and (Test-Path $RunnerLog)) {
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $RunnerLog))
    $sha = [System.Security.Cryptography.SHA256]::HashData($bytes)
    $logEvidence = [ordered]@{
        Path = (Resolve-Path $RunnerLog).Path
        Bytes = $bytes.Length
        SHA256 = [Convert]::ToHexString($sha).ToLowerInvariant()
        Tail = @(Get-Content $RunnerLog -Tail 100)
    }
}

$record = [ordered]@{
    schema = "residual.aud1.f6.remote.v2"
    captured_at = $stamp
    label = $Label
    hostname = $env:COMPUTERNAME
    user = $env:USERNAME
    station_host = $StationHost
    station_port = $StationPort
    runner_pid_requested = $RunnerPid
    runner_process = $runnerProcess
    runner_process_found = [bool]($runnerProcess -and -not $runnerProcess.error)
    runner_has_station_connection = [bool](@($tcp | Where-Object { -not $_.error }).Count -gt 0)
    worker_token_present = [bool]$env:RESIDUAL_WORKER_TOKEN
    runner_api_key_present = [bool]$env:RESIDUAL_RUNNER_API_KEY
    tcp_probe = $probe
    station_connections_for_runner = @($tcp)
    runner_log = $logEvidence
}

$path = Join-Path $OutputDir ("remote-{0}-{1}.json" -f $Label, (Get-Date -Format "yyyyMMddTHHmmss"))
$record | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $path
$hash = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLowerInvariant()
"$hash  $path" | Set-Content -Encoding ASCII "$path.sha256"

Write-Host "Captured: $path"
Write-Host "SHA256: $hash"
Write-Host "Station TCP reachable from host: $($probe.TcpTestSucceeded)"
Write-Host "Bound runner process found: $($record.runner_process_found)"
Write-Host "Bound runner owns Station TCP connection: $($record.runner_has_station_connection)"
