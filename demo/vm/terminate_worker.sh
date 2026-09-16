#!/usr/bin/env bash
# Fail-closed recovery for the public WebVM persistent Mission Control worker.
#
# Usage: bash terminate_worker.sh <token> <mission-id-or-empty> <launch-pid-or-empty>
#
# The marker on stdout is the host contract. A nonzero marker status leaves the
# durable poison record in place so a later page cannot silently reuse uncertain
# worker state. The incomplete mission directory is never removed.
set -u

token=${1-}
mission_id=${2-}
launch_pid=${3-}
pid_file=${RESIDUAL_WORKER_PID_FILE:-/tmp/residual-workbench.pid}
fifo=${RESIDUAL_WORKER_FIFO:-/tmp/residual-workbench.fifo}
output_root=${RESIDUAL_WORKER_OUTPUT_ROOT:-/opt/residual/runs/missions}
poison=${RESIDUAL_WORKER_POISON_FILE:-$output_root/.worker-poisoned}
active=$output_root/.active

valid_mid() {
    [[ $1 =~ ^m-[a-f0-9]{32}$ ]]
}

emit() {
    printf '\nRESIDUAL_WORKER_TERMINATED_%s:%s\n' "$token" "$1"
}

process_live() {
    local pid=$1 key value rest
    kill -0 "$pid" 2>/dev/null || return 1
    # A SIGKILLed child can remain as a zombie until its parent shell reaps it.
    # A zombie has no execution authority and is safe to treat as terminated.
    if [[ -r /proc/$pid/status ]]; then
        while read -r key value rest; do
            if [[ $key == State: ]]; then
                [[ $value != Z && $value != X ]]
                return
            fi
        done < "/proc/$pid/status"
    fi
    return 0
}

worker_identity() {
    local pid=$1
    local -a argv=()
    [[ $pid =~ ^[0-9]+$ ]] || return 1
    process_live "$pid" || return 1
    [[ -r /proc/$pid/cmdline ]] || return 1
    mapfile -d '' argv < "/proc/$pid/cmdline" || return 1
    [[ ${argv[1]-} == -m && ${argv[2]-} == residual.workbench.browser_worker ]]
}

if [[ $token != startup ]] && ! valid_mid "$token"; then
    emit 64
    exit 0
fi
if [[ -n $mission_id ]] && ! valid_mid "$mission_id"; then
    emit 64
    exit 0
fi

# The poison marker is written before signaling anything. If the page/VM host
# disappears mid-recovery, the next host fails closed instead of reusing state.
if [[ -L $poison ]] || { [[ -e $poison ]] && { [[ ! -f $poison ]] || [[ ! -O $poison ]]; }; }; then
    emit 8
    exit 0
fi
mkdir -p -- "$output_root"
umask 077
printf '%s\n' "$token" > "$poison" || { emit 8; exit 0; }

worker_pid=''
pid_file_value=''
if [[ -f $pid_file && ! -L $pid_file && -O $pid_file ]] && read -r pid_file_value < "$pid_file" && worker_identity "$pid_file_value"; then
    worker_pid=$pid_file_value
elif [[ $launch_pid =~ ^[0-9]+$ ]] && worker_identity "$launch_pid"; then
    # Covers startup timeout before browser_worker has published its PID file.
    worker_pid=$launch_pid
fi

if [[ -z $worker_pid ]]; then
    # A startup child that already exited has no authority left to fence. There
    # is no mission lock to reconcile in this path.
    if [[ -z $mission_id && $launch_pid =~ ^[0-9]+$ ]] && ! process_live "$launch_pid"; then
        if [[ -f $poison && ! -L $poison && -O $poison ]] && read -r poison_value < "$poison" && [[ $poison_value == "$token" ]]; then
            rm -f -- "$poison"
            emit 0
            exit 0
        fi
    fi
    emit 3
    exit 0
fi

kill -KILL "$worker_pid" 2>/dev/null || true
for _ in $(seq 1 100); do
    process_live "$worker_pid" || break
    sleep 0.05
done
if process_live "$worker_pid"; then
    emit 4
    exit 0
fi

# Remove only control objects still bound to the worker we just killed.
if [[ -f $pid_file && ! -L $pid_file && -O $pid_file ]] && read -r pid_file_value < "$pid_file" && [[ $pid_file_value == "$worker_pid" ]]; then
    rm -f -- "$pid_file"
fi
if [[ -p $fifo && -O $fifo ]]; then
    rm -f -- "$fifo"
fi

# SIGKILL bypasses runner.execute()'s Python finally. Reconcile only the exact
# timed-out mission lock; a different lock is evidence of other work and must
# never be removed by this recovery path.
if [[ -n $mission_id && -f $active && ! -L $active && -O $active ]]; then
    active_mid=''
    if read -r active_mid < "$active" && [[ $active_mid == "$mission_id" ]]; then
        rm -f -- "$active"
    fi
fi

# Clear poison only if it is still the record written by this recovery attempt.
poison_value=''
if [[ -f $poison && ! -L $poison && -O $poison ]] && read -r poison_value < "$poison" && [[ $poison_value == "$token" ]]; then
    rm -f -- "$poison"
    emit 0
    exit 0
fi

emit 6
exit 0
