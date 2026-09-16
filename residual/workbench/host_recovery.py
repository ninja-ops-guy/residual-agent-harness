"""Build the bounded shell recovery command used by the WebVM host.

The public browser owns one long-lived interactive Bash shell. When the host
loses confidence in the persistent Python worker, recovery must happen through
that shell without trusting the worker itself. This module only builds the
command; it is used by the site patcher and executable regressions so the tested
recovery semantics cannot drift from the shipped command.
"""
from __future__ import annotations

from pathlib import Path
import re
import shlex

MISSION_ID = re.compile(r"m-[0-9a-f]{32}\Z")
MARKER = re.compile(r"[A-Z0-9_]{1,96}\Z")
WORKER_MODULE = "residual.workbench.browser_worker"
MISSION_TEMPLATE = "__RESIDUAL_MISSION_ID__"
MARKER_TEMPLATE = "__RESIDUAL_RECOVERY_MARKER__"


def _q(value: str | Path) -> str:
    return shlex.quote(str(value))


def build_recovery_command(
    *,
    pid_file: str | Path,
    control_file: str | Path,
    busy_file: str | Path,
    poison_file: str | Path,
    active_lock: str | Path,
    mission_id: str | None,
    marker: str,
) -> str:
    """Return one fail-closed Bash command for a poisoned worker generation.

    ``mission_id`` is optional for worker-start timeout. When supplied, both the
    private worker busy marker and the authoritative workspace lock are removed
    only if they contain that exact mission ID. Mission output folders are never
    deleted by recovery.

    The DataDevice-backed control record is a reserved dispatch queue slot. Once
    the worker identity is dead it is safe to remove only when it is a regular,
    owner-controlled singleton; this prevents a queued command from replaying
    after an explicit guest reset. Unexpected file types leave recovery poisoned.
    """
    if (
        mission_id is not None
        and mission_id != MISSION_TEMPLATE
        and not MISSION_ID.fullmatch(mission_id)
    ):
        raise ValueError("invalid recovery mission id")
    if marker != MARKER_TEMPLATE and not MARKER.fullmatch(marker):
        raise ValueError("invalid recovery marker")

    pid = _q(pid_file)
    control = _q(control_file)
    busy = _q(busy_file)
    poison = _q(poison_file)
    active = _q(active_lock)
    mission = (
        f"'{MISSION_TEMPLATE}'"
        if mission_id == MISSION_TEMPLATE
        else _q(mission_id or "")
    )
    marker_q = (
        f"'{MARKER_TEMPLATE}'"
        if marker == MARKER_TEMPLATE
        else _q(marker)
    )
    module = _q(WORKER_MODULE)

    # Poison first. Page loss after this point cannot silently permit reuse.
    return " ".join([
        "residual_recovery_status=0;",
        f"residual_poison_tmp=$(mktemp {poison}.tmp.XXXXXX) || residual_recovery_status=70;",
        "if [ \"$residual_recovery_status\" -eq 0 ]; then",
        f"printf '%s\\n' {mission} > \"$residual_poison_tmp\" || residual_recovery_status=70;",
        "chmod 600 \"$residual_poison_tmp\" 2>/dev/null || residual_recovery_status=70;",
        f"mv -f -- \"$residual_poison_tmp\" {poison} 2>/dev/null || residual_recovery_status=70;",
        "fi;",
        "residual_target_pid='';",
        f"if [ -f {pid} ] && [ ! -L {pid} ] && [ -O {pid} ] && [ \"$(stat -c %h {pid} 2>/dev/null)\" = 1 ] && read -r residual_pid < {pid} && [[ \"$residual_pid\" =~ ^[0-9]+$ ]]; then",
        "if [ -r \"/proc/$residual_pid/cmdline\" ]; then",
        "residual_worker_argv=(); mapfile -d '' residual_worker_argv < \"/proc/$residual_pid/cmdline\" 2>/dev/null || true;",
        f"if [ \"${{residual_worker_argv[1]-}}\" = '-m' ] && [ \"${{residual_worker_argv[2]-}}\" = {module} ]; then residual_target_pid=\"$residual_pid\"; fi;",
        "fi; fi;",
        # Startup timeout can precede PID-file publication. Give a bounded chance
        # to publish identity; the poison record independently fences late start.
        "if [ -z \"$residual_target_pid\" ]; then",
        "for residual_wait in {1..50}; do",
        f"if [ -f {pid} ] && [ ! -L {pid} ] && [ -O {pid} ] && [ \"$(stat -c %h {pid} 2>/dev/null)\" = 1 ] && read -r residual_pid < {pid} && [[ \"$residual_pid\" =~ ^[0-9]+$ ]] && [ -r \"/proc/$residual_pid/cmdline\" ]; then",
        "residual_worker_argv=(); mapfile -d '' residual_worker_argv < \"/proc/$residual_pid/cmdline\" 2>/dev/null || true;",
        f"if [ \"${{residual_worker_argv[1]-}}\" = '-m' ] && [ \"${{residual_worker_argv[2]-}}\" = {module} ]; then residual_target_pid=\"$residual_pid\"; break; fi;",
        "fi; sleep 0.05; done; fi;",
        "if [ -n \"$residual_target_pid\" ]; then",
        "kill -KILL \"$residual_target_pid\" 2>/dev/null || true;",
        "wait \"$residual_target_pid\" 2>/dev/null || true;",
        "fi;",
        # Prove there is no matching persistent worker, including a late process
        # that never published the expected PID file.
        "residual_worker_live=0;",
        "for residual_cmdline in /proc/[0-9]*/cmdline; do",
        "[ -r \"$residual_cmdline\" ] || continue; residual_scan_argv=();",
        "mapfile -d '' residual_scan_argv < \"$residual_cmdline\" 2>/dev/null || continue;",
        f"if [ \"${{residual_scan_argv[1]-}}\" = '-m' ] && [ \"${{residual_scan_argv[2]-}}\" = {module} ]; then residual_worker_live=1; break; fi;",
        "done;",
        "if [ \"$residual_worker_live\" -ne 0 ]; then residual_recovery_status=70; fi;",
        "if [ \"$residual_recovery_status\" -eq 0 ]; then",
        f"if [ -e {pid} ] || [ -L {pid} ]; then if [ -f {pid} ] && [ ! -L {pid} ] && [ -O {pid} ] && [ \"$(stat -c %h {pid} 2>/dev/null)\" = 1 ]; then rm -f -- {pid}; else residual_recovery_status=70; fi; fi;",
        # A queued control record must never replay after reset. It is reserved
        # solely for this worker generation, so remove any safe regular singleton
        # after worker death; unexpected types keep recovery fail-closed.
        f"if [ -e {control} ] || [ -L {control} ]; then if [ -f {control} ] && [ ! -L {control} ] && [ -O {control} ] && [ \"$(stat -c %h {control} 2>/dev/null)\" = 1 ]; then rm -f -- {control}; else residual_recovery_status=70; fi; fi;",
        "fi;",
        # Busy identity belongs to the admitted mission. Never clear a different
        # mission's busy marker merely to obtain a green recovery result.
        f"if [ \"$residual_recovery_status\" -eq 0 ] && [ -e {busy} ]; then",
        f"if [ -n {mission} ] && [ -f {busy} ] && [ ! -L {busy} ] && [ -O {busy} ] && [ \"$(stat -c %h {busy} 2>/dev/null)\" = 1 ] && [ \"$(stat -c %s {busy} 2>/dev/null)\" = 34 ]; then residual_busy_id=$(cat -- {busy} 2>/dev/null) || residual_busy_id=''; if [ \"$residual_busy_id\" = {mission} ]; then rm -f -- {busy}; else residual_recovery_status=70; fi; else residual_recovery_status=70; fi;",
        "fi;",
        # runner.execute writes the mission ID without a trailing newline.
        f"if [ \"$residual_recovery_status\" -eq 0 ] && [ -n {mission} ] && [ -e {active} ]; then",
        f"if [ -f {active} ] && [ ! -L {active} ] && [ -O {active} ] && [ \"$(stat -c %h {active} 2>/dev/null)\" = 1 ] && [ \"$(stat -c %s {active} 2>/dev/null)\" = 34 ]; then residual_active_id=$(cat -- {active} 2>/dev/null) || residual_active_id=''; if [ \"$residual_active_id\" = {mission} ]; then rm -f -- {active}; else residual_recovery_status=70; fi; else residual_recovery_status=70; fi;",
        "fi;",
        f"printf '%s:%s\\n' {marker_q} \"$residual_recovery_status\";",
    ])
