param(
    [Parameter(Mandatory=$true)][string]$Label,
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
        Where-Object { $_.RemotePort -eq $StationPort -or $_.LocalPort -eq $StationPort } |
        Select-Object State,LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess
} catch {
    $tcp = @(@{ error = $_.Exception.Message })
}

$runnerProcesses = @()
try {
    $runnerProcesses = Get-CimInstance Win32_Process |
        Where-Object {
            ($_.Name -match "python") -and
            ($_.CommandLine -match "residual\.station\.worker|residual-worker")
        } |
        ForEach-Object {
            # Do not retain the command line: future CLI changes could put sensitive material there.
            [ordered]@{
                ProcessId = $_.ProcessId
                Name = $_.Name
                CreationDate = $_.CreationDate
            }
        }
} catch {
    $runnerProcesses = @(@{ error = $_.Exception.Message })
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
    schema = "residual.aud1.f6.remote.v1"
    captured_at = $stamp
    label = $Label
    hostname = $env:COMPUTERNAME
    user = $env:USERNAME
    station_host = $StationHost
    station_port = $StationPort
    worker_token_present = [bool]$env:RESIDUAL_WORKER_TOKEN
    runner_api_key_present = [bool]$env:RESIDUAL_RUNNER_API_KEY
    tcp_probe = $probe
    station_connections = @($tcp)
    runner_processes = @($runnerProcesses)
    runner_log = $logEvidence
}

$path = Join-Path $OutputDir ("remote-{0}-{1}.json" -f $Label, (Get-Date -Format "yyyyMMddTHHmmss"))
$record | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $path
$hash = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLowerInvariant()
"$hash  $path" | Set-Content -Encoding ASCII "$path.sha256"

Write-Host "Captured: $path"
Write-Host "SHA256: $hash"
Write-Host "Station TCP reachable: $($probe.TcpTestSucceeded)"
Write-Host "Runner processes observed: $(@($runnerProcesses).Count)"
