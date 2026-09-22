param(
    [Parameter(Mandatory=$true)][ValidateSet("F6-A-inside-window","F6-B-outside-window")][string]$Case,
    [Parameter(Mandatory=$true)][string]$CandidateRepo,
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Task,
    [string]$StationData = "$HOME/.residual/station",
    [string]$StationUrl = "http://127.0.0.1:8765",
    [string]$Output = "$PWD/AUD1-F6-EVIDENCE",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Target = "8df77b832b3839ccd2a6944a65760ce3ab10dc9c"
$Collector = Join-Path $PSScriptRoot "f6_collect.py"
$Db = Join-Path $StationData "station.sqlite3"

function Invoke-Collector {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
    & $Python $Collector --output $Output @Args
    if ($LASTEXITCODE -ne 0) { throw "Collector failed with exit code $LASTEXITCODE" }
}

function Capture([string]$Label) {
    Write-Host "Capturing $Label ..." -ForegroundColor Cyan
    Invoke-Collector capture --case $Case --label $Label --candidate-repo $CandidateRepo --db $Db --project $Project --task $Task --station-url $StationUrl
}

function Note([string]$Kind,[string]$Message) {
    Invoke-Collector note --case $Case --kind $Kind --message $Message
}

Write-Host "AUD-1 F6 physical evidence harness" -ForegroundColor Green
Write-Host "Target candidate: $Target"
Write-Host "Case: $Case"
Write-Host "This harness NEVER disables/enables tunnels itself and never mutates Station state."
Write-Host "It only captures read-only Station/database/network evidence around actions you perform." -ForegroundColor Yellow

$head = (& git -C $CandidateRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $Target) {
    throw "REFUSE: Candidate checkout is $head; expected exact AUD-1 candidate $Target"
}
$dirty = & git -C $CandidateRepo status --porcelain=v1
if ($dirty) { throw "REFUSE: Candidate checkout is dirty. Physical evidence must bind to exact clean bytes." }
if (-not (Test-Path $Db)) { throw "Station DB not found: $Db" }

Capture "00-preflight"

Write-Host ""
Write-Host "PRECONDITION: a real remote runner must own $Task and be actively generating work." -ForegroundColor Yellow
$confirm = Read-Host "Type OWNED after Mission Control/Station shows the task is owned"
if ($confirm -ne "OWNED") { throw "Aborted before transport manipulation." }
Note "HITL" "Operator confirmed real runner owns $Task before interruption."
Capture "01-owned-before-interrupt"

Write-Host ""
Write-Host "ACTION REQUIRED: interrupt ONLY the authenticated tunnel/transport for the runner owning $Task." -ForegroundColor Magenta
Write-Host "Do not stop Station, edit the DB, kill the coordinator, rotate credentials, or modify candidate bytes."
$down = Read-Host "After the runner transport is actually unavailable, type DOWN"
if ($down -ne "DOWN") { throw "Aborted; tunnel-down not confirmed." }
Note "TUNNEL_DOWN" "Operator confirmed authenticated runner transport interrupted."
Capture "02-transport-down"

if ($Case -eq "F6-A-inside-window") {
    Write-Host ""
    Write-Host "F6-A: restore connectivity BEFORE the 180-second worker heartbeat grace expires." -ForegroundColor Yellow
    Write-Host "Restore promptly; do not wait near the boundary."
    $up = Read-Host "Restore the SAME tunnel now; once reachable, type UP"
    if ($up -ne "UP") { throw "Aborted; reconnect not confirmed." }
    Note "TUNNEL_UP" "Operator confirmed same authenticated transport restored inside heartbeat grace window."
    Capture "03-reconnected-inside-window"

    Write-Host "Allow the same runner to finish naturally. Do not manually submit or integrate its proposal." -ForegroundColor Yellow
    $done = Read-Host "When Station shows the candidate reached its natural post-run state, type DONE"
    if ($done -ne "DONE") { throw "Aborted before terminal capture." }
    Capture "04-terminal"
}
else {
    Write-Host ""
    Write-Host "F6-B: keep the transport DOWN beyond the 180-second worker authority grace." -ForegroundColor Yellow
    Write-Host "The worker should surrender locally and must not submit its eventual proposal."
    Start-Sleep -Seconds 190
    Note "OBSERVATION" "Harness held transport interruption beyond 180-second worker heartbeat grace."
    Capture "03-after-worker-authority-grace"

    Write-Host ""
    Write-Host "Server lease renewal is 900 seconds. Reassignment must not be forced by DB edits." -ForegroundColor Yellow
    Write-Host "Wait until the task's retained lease expires/recovery makes it claimable, then let a DIFFERENT valid runner claim it."
    $reassigned = Read-Host "When a different runner owns the recovered/reassigned task, type REASSIGNED"
    if ($reassigned -ne "REASSIGNED") { throw "Aborted before reassignment evidence." }
    Note "REASSIGNMENT" "Operator confirmed recovered task is owned by a different valid runner after old authority expired."
    Capture "04-reassigned"

    Write-Host ""
    Write-Host "Restore the OLD runner's tunnel. Do not grant it a new credential or new claim." -ForegroundColor Magenta
    $up = Read-Host "After the old runner transport is restored, type UP"
    if ($up -ne "UP") { throw "Aborted before stale-return capture." }
    Note "TUNNEL_UP" "Operator restored old runner transport only after reassignment."
    Capture "05-old-runner-returned"

    Write-Host ""
    Write-Host "The old runner/result must remain rejected. Capture the runner terminal/log showing rejection or no submission." -ForegroundColor Yellow
    Write-Host "Use f6_remote_probe.ps1 on that host to retain its local process/log/network evidence."
    $stale = Read-Host "After stale-authority behavior is observable, type REJECTED if rejected/no-submit was proven, otherwise type FAIL"
    if ($stale -eq "REJECTED") {
        Note "STALE_RESULT" "Operator observed old runner authority/result remained rejected or proposal submission was suppressed."
    } else {
        Note "ERROR" "Expected stale-authority rejection was not demonstrated; preserve as failure."
    }
    Capture "06-stale-result-boundary"
}

Write-Host ""
Write-Host "Freezing immutable evidence manifest..." -ForegroundColor Cyan
Invoke-Collector freeze --case $Case
Invoke-Collector verify --case $Case

Write-Host ""
Write-Host "Case collection complete. This harness does NOT declare PASS." -ForegroundColor Green
Write-Host "Mason/reviewer must classify the retained evidence against AUD-1 F6."
