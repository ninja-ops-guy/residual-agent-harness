#!/usr/bin/env python3
"""Add Mission Control without changing the M4 trust boundary or evidence schemas."""
from pathlib import Path
import shutil
import sys
from qualify_webvm import replace_once


def patch(text):
    text = replace_once(text, "<script>\n", "<script>\n\timport { mountMissionControl } from './mission-control-world.js';\n")
    text = replace_once(text, 'var residualBridgeBuffer = "";',
                        'var residualWorkbench = null;\n\tvar residualDataDevice = null;\n\tvar residualShellTail = "";\n\tvar residualShellReady = false;\n\tvar residualShellCommandBusy = false;\n\tvar residualShellRun = null;\n\tvar residualShellInputBuffer = "";\n\tvar residualWorkerReady = false;\n\tvar residualWorkerPoisoned = false;\n\tvar residualWorkerStart = null;\n\tvar residualWorkerTermination = null;\n\tvar residualBridgeBuffer = "";')
    text = replace_once(text, 'const out = residualDecoder.decode(bytes, {stream:true});', """const out = residualDecoder.decode(bytes, {stream:true});
        residualShellTail = (residualShellTail + out).slice(-4096).replace(/\\x1b\\[[0-9;?]*[A-Za-z]/g, "");
        if (residualShellTail.includes("residual@demo:~/residual-agent-harness$")) residualShellReady = true;
        // Project authoritative guest frames before resolving worker lifecycle
        // markers that may share the same terminal output chunk.
        residualWorkbench?.onOutput(out);
        if (residualWorkerTermination) {
            const marker = new RegExp("RESIDUAL_WORKER_TERMINATED_" + residualWorkerTermination.token + ":([0-9]+)");
            const match = residualShellTail.match(marker);
            if (match) {
                const current = residualWorkerTermination;
                residualWorkerTermination = null;
                current.finish(Number(match[1]));
            }
        }
        if (residualWorkerStart && residualShellTail.includes("RESIDUAL_WORKER_POISONED")) {
            const current = residualWorkerStart;
            residualWorkerStart = null;
            residualWorkerReady = false;
            residualWorkerPoisoned = true;
            residualShellCommandBusy = false;
            residualShellInputBuffer = "";
            current.fail(new Error("Persistent guest worker is durably poisoned; reset required"));
        }
        if (!residualWorkerPoisoned && residualShellTail.includes("RESIDUAL_WORKER_READY")) {
            residualWorkerReady = true;
            if (residualWorkerStart) {
                const current = residualWorkerStart;
                residualWorkerStart = null;
                residualShellCommandBusy = false;
                const queuedInput = residualShellInputBuffer;
                residualShellInputBuffer = "";
                if (queuedInput) readData(queuedInput);
                current.finish();
            }
        }
        if (residualShellRun) {
            const normal = new RegExp("RESIDUAL_WORKER_RUN_" + residualShellRun.missionId + ":([0-9]+)");
            const fatal = new RegExp("RESIDUAL_WORKER_FATAL_" + residualShellRun.missionId + ":([0-9]+)");
            const fatalMatch = residualShellTail.match(fatal);
            const match = fatalMatch || residualShellTail.match(normal);
            if (match) {
                const current = residualShellRun;
                residualShellRun = null;
                residualShellCommandBusy = false;
                if (fatalMatch) {
                    // The persistent interpreter itself reported an unexpected
                    // failure. Do not dispatch another mission into that runtime;
                    // a page/guest restart is required.
                    residualWorkerReady = false;
                    residualWorkerPoisoned = true;
                }
                const queuedInput = residualShellInputBuffer;
                residualShellInputBuffer = "";
                if (queuedInput) readData(queuedInput);
                current.finish({status: Number(match[1]), fatal: !!fatalMatch});
            }
        }""")
    text = replace_once(text, 'var dataDevice = await CheerpX.DataDevice.create();',
                        'var dataDevice = await CheerpX.DataDevice.create();\n\t\tresidualDataDevice = dataDevice;')
    text = replace_once(text, 'term.onData(readData);', """term.onData(data => {
            // User/automation terminal input is queued while Mission Control is
            // starting or using its persistent worker. The worker itself runs in
            // the background; queuing prevents shell commands from racing its
            // FIFO dispatch while preserving every keystroke for later replay.
            if (residualShellCommandBusy) {
                residualShellInputBuffer += data;
                return;
            }
            readData(data);
        });
        async function terminateResidualWorker(missionId = "") {
            if (residualWorkerTermination) return await residualWorkerTermination.promise;
            const token = missionId || "startup";
            let resolveTermination;
            const promise = new Promise(resolve => { resolveTermination = resolve; });
            const timer = setTimeout(() => {
                if (!residualWorkerTermination || residualWorkerTermination.token !== token) return;
                residualWorkerTermination = null;
                resolveTermination(9);
            }, 15000);
            residualWorkerTermination = {
                token,
                promise,
                finish: status => { clearTimeout(timer); resolveTermination(status); }
            };
            // Write a durable poison marker first.  If the page disappears while
            // termination is in progress, the next host refuses worker reuse.
            // The marker is removed only after an identity-validated worker is
            // proven dead and any matching workspace lock is reconciled.
            const command = `residual_poison=/opt/residual/runs/missions/.worker-poisoned; residual_worker_status=3; residual_worker_pid=""; if [ -L "$residual_poison" ] || { [ -e "$residual_poison" ] && { [ ! -f "$residual_poison" ] || [ ! -O "$residual_poison" ]; }; }; then residual_worker_status=8; else umask 077; printf '%s\\n' '${token}' > "$residual_poison"; if [ -f /tmp/residual-workbench.pid ] && [ ! -L /tmp/residual-workbench.pid ] && [ -O /tmp/residual-workbench.pid ] && read -r residual_pid_file_value < /tmp/residual-workbench.pid && [[ "$residual_pid_file_value" =~ ^[0-9]+$ ]] && kill -0 "$residual_pid_file_value" 2>/dev/null && mapfile -d '' residual_worker_argv < "/proc/$residual_pid_file_value/cmdline" && [ "\${residual_worker_argv[1]-}" = "-m" ] && [ "\${residual_worker_argv[2]-}" = "residual.workbench.browser_worker" ]; then residual_worker_pid="$residual_pid_file_value"; elif [[ "\${residual_worker_launch_pid-}" =~ ^[0-9]+$ ]] && kill -0 "$residual_worker_launch_pid" 2>/dev/null && mapfile -d '' residual_worker_argv < "/proc/$residual_worker_launch_pid/cmdline" && [ "\${residual_worker_argv[1]-}" = "-m" ] && [ "\${residual_worker_argv[2]-}" = "residual.workbench.browser_worker" ]; then residual_worker_pid="$residual_worker_launch_pid"; fi; if [ -n "$residual_worker_pid" ]; then kill -KILL "$residual_worker_pid" 2>/dev/null || true; wait "$residual_worker_pid" 2>/dev/null || true; for residual_wait_i in {1..100}; do kill -0 "$residual_worker_pid" 2>/dev/null || break; sleep 0.05; done; if ! kill -0 "$residual_worker_pid" 2>/dev/null; then residual_worker_status=0; if [ -f /tmp/residual-workbench.pid ] && [ ! -L /tmp/residual-workbench.pid ] && [ -O /tmp/residual-workbench.pid ] && read -r residual_pid_file_value < /tmp/residual-workbench.pid && [ "$residual_pid_file_value" = "$residual_worker_pid" ]; then rm -f -- /tmp/residual-workbench.pid; fi; if [ -p /tmp/residual-workbench.fifo ] && [ -O /tmp/residual-workbench.fifo ]; then rm -f -- /tmp/residual-workbench.fifo; fi; if [ -n '${missionId}' ] && [ -f /opt/residual/runs/missions/.active ] && [ ! -L /opt/residual/runs/missions/.active ] && [ -O /opt/residual/runs/missions/.active ] && read -r residual_active_mid < /opt/residual/runs/missions/.active && [ "$residual_active_mid" = '${missionId}' ]; then rm -f -- /opt/residual/runs/missions/.active; fi; rm -f -- "$residual_poison"; unset residual_worker_launch_pid; fi; elif [ -z '${missionId}' ] && [[ "\${residual_worker_launch_pid-}" =~ ^[0-9]+$ ]] && ! kill -0 "$residual_worker_launch_pid" 2>/dev/null; then residual_worker_status=0; rm -f -- "$residual_poison"; unset residual_worker_launch_pid; fi; fi; printf '\\nRESIDUAL_WORKER_TERMINATED_${token}:%s\\n' "$residual_worker_status"`;
            readData(command + "\\r");
            return await promise;
        }
        async function ensureResidualWorker() {
            if (residualWorkerPoisoned) throw new Error("Guest worker requires restart");
            if (residualWorkerReady) return;
            if (residualWorkerStart) return await residualWorkerStart.promise;
            residualShellCommandBusy = true;
            residualShellTail = "";
            residualShellInputBuffer = "";
            let resolveStart, rejectStart;
            const promise = new Promise((resolve, reject) => { resolveStart = resolve; rejectStart = reject; });
            const timeout = setTimeout(async () => {
                if (!residualWorkerStart) return;
                residualWorkerPoisoned = true;
                residualWorkerReady = false;
                const current = residualWorkerStart;
                residualWorkerStart = null;
                const terminationStatus = await terminateResidualWorker("");
                residualShellCommandBusy = false;
                residualShellInputBuffer = "";
                current.fail(new Error("Persistent guest worker did not become ready; termination status " + terminationStatus));
            }, 60000);
            residualWorkerStart = {
                promise,
                finish: () => { clearTimeout(timeout); resolveStart(); },
                fail: error => { clearTimeout(timeout); rejectStart(error); }
            };
            // A durable poison marker means a previous timeout could not prove
            // cleanup.  Refuse reuse instead of silently reviving that generation.
            const command = `if [ -e /opt/residual/runs/missions/.worker-poisoned ] || [ -L /opt/residual/runs/missions/.worker-poisoned ]; then echo RESIDUAL_WORKER_POISONED; elif [ -f /tmp/residual-workbench.pid ] && [ ! -L /tmp/residual-workbench.pid ] && [ -O /tmp/residual-workbench.pid ] && [ -p /tmp/residual-workbench.fifo ] && read -r residual_worker_pid < /tmp/residual-workbench.pid && [[ "$residual_worker_pid" =~ ^[0-9]+$ ]] && kill -0 "$residual_worker_pid" 2>/dev/null && mapfile -d '' residual_worker_argv < "/proc/$residual_worker_pid/cmdline" && [ "\${residual_worker_argv[1]-}" = "-m" ] && [ "\${residual_worker_argv[2]-}" = "residual.workbench.browser_worker" ]; then echo RESIDUAL_WORKER_READY; else python3 -m residual.workbench.browser_worker --fifo /tmp/residual-workbench.fifo --pid-file /tmp/residual-workbench.pid --mailbox /data --root /opt/residual --output-root /opt/residual/runs/missions & residual_worker_launch_pid=$!; fi`;
            readData(command + "\\r");
            return await promise;
        }
        residualWorkbench = mountMissionControl({
            ready: () => !!cx && !!residualDataDevice && residualShellReady && !residualShellCommandBusy && !residualWorkerPoisoned,
            focus: () => term.focus(),
            mailbox: async (path, text) => {
                const response = /^\\/m-[a-f0-9]{32}-[a-f0-9]{32}\\.json$/.test(path);
                const cancel = /^\\/m-[a-f0-9]{32}-cancel\\.json$/.test(path);
                if (!response && !cancel) throw new Error("Invalid mailbox path");
                // Publish provider responses in two phases. Cancellation is a
                // one-file signal and therefore does not need a ready marker.
                await residualDataDevice.writeFile(path, text);
                if (response) await residualDataDevice.writeFile(path + ".ready", "1");
            },
            run: async (request) => {
                if (!/^m-[a-f0-9]{32}$/.test(request.id)) throw new Error("Invalid mission ID");
                if (!["audit", "live", "build"].includes(request.mode)) throw new Error("Invalid mission mode");
                if (residualShellCommandBusy || residualShellRun) throw new Error("Guest command already active");
                await ensureResidualWorker();
                if (residualWorkerPoisoned || !residualWorkerReady || residualShellCommandBusy || residualShellRun) throw new Error("Guest worker unavailable");
                const name = "/" + request.id + ".json";
                await residualDataDevice.writeFile(name, JSON.stringify(request));
                residualShellCommandBusy = true;
                residualShellTail = "";
                residualShellInputBuffer = "";
                return await new Promise((resolve, reject) => {
                    const timeout = setTimeout(async () => {
                        if (!residualShellRun || residualShellRun.missionId !== request.id) return;
                        residualWorkerReady = false;
                        residualWorkerPoisoned = true;
                        residualShellRun = null;
                        const terminationStatus = await terminateResidualWorker(request.id);
                        residualShellCommandBusy = false;
                        residualShellInputBuffer = "";
                        reject(new Error("Persistent guest mission timed out; termination status " + terminationStatus + "; restart required"));
                    }, 330000);
                    residualShellRun = {
                        missionId: request.id,
                        finish: value => { clearTimeout(timeout); resolve(value); }
                    };
                    // The shell writes only a validated mission id and mode to a
                    // FIFO using its builtin printf. Prompt/source data remains
                    // in the DataDevice request file and is never shell-expanded.
                    const command = `printf '%s\\n' '${request.id} ${request.mode}' > /tmp/residual-workbench.fifo`;
                    readData(command + "\\r");
                });
            }
        });""")
    start = text.index('\tasync function enableResidualCloud()')
    end = text.index('\n\tfunction writeData(', start)
    text = text[:start] + '\tfunction enableResidualCloud() { residualWorkbench?.connectProvider(); }\n' + text[end:]
    text = text.replace('var residualCloudLabel = "ENABLE CLOUD ✦";', 'var residualCloudLabel = "Connect provider";')
    old = '\t\t<button on:click={enableResidualCloud}'
    if text.count(old) != 1:
        raise ValueError('Legacy cloud button anchor changed')
    start = text.index(old); end = text.index('</button>', start) + len('</button>')
    text = text[:start] + text[end:]
    return text


def install(source: Path, site: Path):
    source.write_text(patch(source.read_text()))
    here = Path(__file__).resolve().parent
    for name in ('mission-control.js', 'mission-control-engineer.js', 'mission-control-world.js', 'mission-preview.js', 'provider-session.js'):
        shutil.copyfile(here / name, source.parent / name)
    provider = site / 'provider'; provider.mkdir(parents=True, exist_ok=True)
    for src, dst in [('provider.html', 'index.html'), ('provider.js', 'provider.js'), ('provider-session.js', 'provider-session.js')]:
        shutil.copyfile(here / src, provider / dst)


if __name__ == '__main__':
    install(Path(sys.argv[1]), Path(sys.argv[2]))
