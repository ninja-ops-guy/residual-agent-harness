param(
    [Parameter(Mandatory=$true)][ValidateSet("F6-A-inside-window","F6-B-outside-window")][string]$Case,
    [Parameter(Mandatory=$true)][string]$CandidateRepo,
    [Parameter(Mandatory=$true)][string]$StationRecord,
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Task,
    [string]$StationData = "$HOME/.residual/station",
    [string]$StationUrl = "http://127.0.0.1:8765",
    [string]$Output = "$PWD/AUD1-F6-EVIDENCE",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Target = "8df77b832b3839ccd2a6944a65760ce3ab10dc9c"
$Collector = Join-Path $PSScriptRoot "f6_case_guard.py"
$Db = Join-Path $StationData "station.sqlite3"
$CaseDir = Join-Path $Output $Case

function Invoke-Collector {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
    & $Python $Collector --output $Output @Args
    if ($LASTEXITCODE -ne 0) { throw "Collector failed with exit code $LASTEXITCODE" }
}

function Capture([string]$Label) {
    Write-Host "Capturing $Label ..." -ForegroundColor Cyan
    Invoke-Collector capture --case $Case --label $Label --candidate-repo $CandidateRepo --station-record $StationRecord --db $Db --project $Project --task $Task --station-url $StationUrl
}

function Note([string]$Kind,[string]$Message) {
    Invoke-Collector note --case $Case --kind $Kind --message $Message
}

function Attach-RequiredRemote([string]$Name,[string]$Prompt) {
    Write-Host ""
    Write-Host $Prompt -ForegroundColor Yellow
    $path = Read-Host "Path to the transferred remote evidence JSON"
    if (-not (Test-Path $path)) { throw "Required remote evidence file not found: $path" }
    Invoke-Collector attach --case $Case --file $path --name $Name
}

Write-Host "AUD-1 F6 physical evidence harness" -ForegroundColor Green
Write-Host "Target candidate: $Target"
Write-Host "Case: $Case"
Write-Host "Station launch witness: $StationRecord"
Write-Host "The collector remains read-only. Case B additionally requires one bounded stale-result rejection probe after reassignment." -ForegroundColor Yellow

if (Test-Path $CaseDir) {
    throw "REFUSE: $CaseDir already exists. Preserve prior attempts and use a new Output directory for this run."
}

$head = (& git -C $CandidateRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $Target) {
    throw "REFUSE: Candidate checkout is $head; expected exact AUD-1 candidate $Target"
}
$dirty = & git -C $CandidateRepo status --porcelain=v1
if ($dirty) { throw "REFUSE: Candidate checkout is dirty. Physical evidence must bind to exact clean bytes." }
if (-not (Test-Path $Db)) { throw "Station DB not found: $Db" }
if (-not (Test-Path $StationRecord)) { throw "Station launch witness not found: $StationRecord" }
if (-not (Test-Path "$StationRecord.sha256")) { throw "Station launch witness digest not found: $StationRecord.sha256" }

Capture "00-preflight"

Write-Host ""
Write-Host "PRECONDITION: a real remote runner must own $Task and be actively generating work." -ForegroundColor Yellow
$confirm = Read-Host "Type OWNED after Mission Control/Station shows the task is owned"
if ($confirm -ne "OWNED") { throw "Aborted before transport manipulation." }
Note "HITL" "Operator confirmed real runner owns $Task before interruption."
Capture "01-owned-before-interrupt"
Attach-RequiredRemote "remote-01-owned-before.json" "Capture f6_remote_probe.ps1 on the task-owning runner while transport is healthy."

Write-Host ""
Write-Host "ACTION REQUIRED: interrupt ONLY the authenticated tunnel/transport for the runner owning $Task." -ForegroundColor Magenta
Write-Host "Do not stop Station, edit the DB, kill the coordinator, rotate credentials, or modify candidate bytes."
$down = Read-Host "After the runner transport is actually unavailable, type DOWN"
if ($down -ne "DOWN") { throw "Aborted; tunnel-down not confirmed." }
$downAt = [DateTimeOffset]::UtcNow
Note "TUNNEL_DOWN" "Operator confirmed authenticated runner transport interrupted."
Capture "02-transport-down"
Attach-RequiredRemote "remote-02-transport-down.json" "Capture f6_remote_probe.ps1 on the same runner while Station TCP reachability is down."

if ($Case -eq "F6-A-inside-window") {
    Write-Host ""
    Write-Host "F6-A: restore connectivity BEFORE the 180-second worker heartbeat grace expires." -ForegroundColor Yellow
    Write-Host "Restore promptly; do not wait near the boundary."
    $up = Read-Host "Restore the SAME tunnel now; once reachable, type UP"
    if ($up -ne "UP") { throw "Aborted; reconnect not confirmed." }
    $upAt = [DateTimeOffset]::UtcNow
    $elapsed = ($upAt - $downAt).TotalSeconds
    if ($elapsed -ge 180) {
        Note "ERROR" ("Inside-window attempt exceeded heartbeat grace: {0:N3}s. Preserve this attempt as failure." -f $elapsed)
        Capture "03-reconnected-inside-window"
        Attach-RequiredRemote "remote-03-reconnected.json" "Capture the runner immediately after the late reconnect so the failed attempt is retained."
        Write-Host "Freezing failed physical attempt..." -ForegroundColor Yellow
        & $Python $Collector --output $Output freeze --case $Case
        & $Python $Collector --output $Output verify --case $Case
        throw "Inside-window timing failed at $elapsed seconds. Bundle retained; do not overwrite it."
    }
    Note "TUNNEL_UP" ("Operator confirmed same authenticated transport restored inside heartbeat grace window after {0:N3}s." -f $elapsed)
    Capture "03-reconnected-inside-window"
    Attach-RequiredRemote "remote-03-reconnected.json" "Capture f6_remote_probe.ps1 on the same runner after connectivity returns."

    Write-Host "Allow the same runner to finish naturally. Do not manually submit or integrate its proposal." -ForegroundColor Yellow
    $done = Read-Host "When Station shows the candidate reached its natural post-run state, type DONE"
    if ($done -ne "DONE") { throw "Aborted before terminal capture." }
    Capture "04-terminal"
    Attach-RequiredRemote "remote-04-terminal.json" "Capture the runner's terminal state/log after the task reaches its natural post-run state."
}
else {
    Write-Host ""
    Write-Host "F6-B: keep the transport DOWN beyond the 180-second worker authority grace." -ForegroundColor Yellow
    Write-Host "The worker should surrender locally and must not submit its eventual proposal."
    Start-Sleep -Seconds 190
    Note "OBSERVATION" "Harness held transport interruption beyond 180-second worker heartbeat grace."
    Capture "03-after-worker-authority-grace"
    Attach-RequiredRemote "remote-03-after-grace.json" "Capture the old runner after authority grace is exceeded; retain WorkerAuthorityLost/no-submit evidence in its log."

    Write-Host ""
    Write-Host "Server lease renewal is 900 seconds. Reassignment must not be forced by DB edits." -ForegroundColor Yellow
    Write-Host "Wait until the retained lease naturally expires/recovery makes it claimable, then let a DIFFERENT valid runner claim it."
    $reassigned = Read-Host "When a different runner owns the recovered/reassigned task, type REASSIGNED"
    if ($reassigned -ne "REASSIGNED") { throw "Aborted before reassignment evidence." }
    Note "REASSIGNMENT" "Operator confirmed recovered task is owned by a different valid runner after old authority expired."
    Capture "04-reassigned"
    Attach-RequiredRemote "remote-04-reassigned.json" "Capture f6_remote_probe.ps1 on the new valid runner now owning the reassigned task."

    Write-Host ""
    Write-Host "Restore the OLD runner's tunnel. Do not grant it a new credential or new claim." -ForegroundColor Magenta
    $up = Read-Host "After the old runner transport is restored, type UP"
    if ($up -ne "UP") { throw "Aborted before stale-return capture." }
    Note "TUNNEL_UP" "Operator restored old runner transport only after reassignment."
    Capture "05-old-runner-returned"
    Attach-RequiredRemote "remote-05-old-returned.json" "Capture the old runner immediately after reconnect; it must not regain ownership."

    Write-Host ""
    Write-Host "Case B now requires an explicit stale-result rejection, not merely local no-submit." -ForegroundColor Yellow
    Write-Host "On the OLD runner, run f6_stale_result_probe.py with its existing RESIDUAL_WORKER_TOKEN, this project/task, and the OLD lease from snapshot 01."
    Write-Host "The probe must produce observed_status=403 and rejected=true. It never writes the credential to evidence."
    $stalePath = Read-Host "Path to the transferred stale-result probe JSON"
    if (-not (Test-Path $stalePath)) { throw "Required stale-result rejection artifact not found: $stalePath" }
    Invoke-Collector attach --case $Case --file $stalePath --name "stale-result-rejection.json"
    $stale = Get-Content $stalePath -Raw | ConvertFrom-Json
    if ($stale.observed_status -ne 403 -or -not $stale.rejected -or $stale.accepted) {
        Note "ERROR" "Explicit stale-result rejection probe did not return the required HTTP 403. Preserve as failure."
    } else {
        Note "STALE_RESULT" "Explicit stale result attempt from the old runner was rejected with HTTP 403 after reassignment."
    }
    Capture "06-stale-result-boundary"
}

Write-Host ""
Write-Host "Freezing immutable evidence manifest..." -ForegroundColor Cyan
& $Python $Collector --output $Output freeze --case $Case
$freezeCode = $LASTEXITCODE
& $Python $Collector --output $Output verify --case $Case
$verifyCode = $LASTEXITCODE
if ($freezeCode -ne 0 -or $verifyCode -ne 0) {
    throw "Physical evidence bundle was retained but did not satisfy the validation contract. Preserve it as a failed attempt."
}

Write-Host ""
Write-Host "Case evidence is sealed and machine-validated. This still does NOT declare AUD-1 FIXED." -ForegroundColor Green
Write-Host "Mason/LEGION must independently classify the retained evidence against F1/F2/F3/F4/F6."
