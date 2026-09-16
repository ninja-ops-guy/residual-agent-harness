#!/usr/bin/env python3
"""Add Mission Control without changing the M4 trust boundary or evidence schemas."""
from pathlib import Path
import shutil
import sys
from qualify_webvm import replace_once


def patch(text):
    text = replace_once(text, "<script>\n", "<script>\n\timport { mountMissionControl } from './mission-control-world.js';\n")
    text = replace_once(text, 'var residualBridgeBuffer = "";',
                        'var residualWorkbench = null;\n\tvar residualDataDevice = null;\n\tvar residualShellTail = "";\n\tvar residualShellReady = false;\n\tvar residualShellCommandBusy = false;\n\tvar residualShellRun = null;\n\tvar residualShellInputBuffer = "";\n\tvar residualWorkerReady = false;\n\tvar residualWorkerPoisoned = false;\n\tvar residualWorkerStart = null;\n\tvar residualBridgeBuffer = "";')
    text = replace_once(text, 'const out = residualDecoder.decode(bytes, {stream:true});', """const out = residualDecoder.decode(bytes, {stream:true});
        residualShellTail = (residualShellTail + out).slice(-4096).replace(/\\x1b\\[[0-9;?]*[A-Za-z]/g, "");
        if (residualShellTail.includes("residual@demo:~/residual-agent-harness$")) residualShellReady = true;
        // Project authoritative guest frames before resolving worker lifecycle
        // markers that may share the same terminal output chunk.
        residualWorkbench?.onOutput(out);
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
        function terminateResidualWorker() {
            // A host-side timeout means the worker did not honor its own bounded
            // mission lifecycle. Never leave that interpreter available for a
            // page reload to rediscover. Signal only a PID whose file ownership,
            // liveness and /proc argv still prove the expected worker identity.
            const command = `if [ -f /tmp/residual-workbench.pid ] && [ ! -L /tmp/residual-workbench.pid ] && [ -O /tmp/residual-workbench.pid ] && read -r residual_worker_pid < /tmp/residual-workbench.pid && [[ "$residual_worker_pid" =~ ^[0-9]+$ ]] && kill -0 "$residual_worker_pid" 2>/dev/null && mapfile -d '' residual_worker_argv < "/proc/$residual_worker_pid/cmdline" && [ "\${residual_worker_argv[1]-}" = "-m" ] && [ "\${residual_worker_argv[2]-}" = "residual.workbench.browser_worker" ]; then kill -KILL "$residual_worker_pid" 2>/dev/null || true; fi`;
            readData(command + "\\r");
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
            const timeout = setTimeout(() => {
                if (!residualWorkerStart) return;
                terminateResidualWorker();
                residualWorkerStart = null;
                residualWorkerReady = false;
                residualWorkerPoisoned = true;
                residualShellCommandBusy = false;
                residualShellInputBuffer = "";
                rejectStart(new Error("Persistent guest worker did not become ready"));
            }, 60000);
            residualWorkerStart = {
                promise,
                finish: () => { clearTimeout(timeout); resolveStart(); }
            };
            // Reuse only a surviving worker whose PID file, FIFO, process,
            // and /proc argv all identify the expected long-lived module. This
            // prevents a stale/reused PID from being accepted as worker identity.
            // The two \${...} expressions are intentionally escaped through
            // this JavaScript template literal so Bash, not JavaScript, expands them.
            const command = `if [ -f /tmp/residual-workbench.pid ] && [ ! -L /tmp/residual-workbench.pid ] && [ -O /tmp/residual-workbench.pid ] && [ -p /tmp/residual-workbench.fifo ] && read -r residual_worker_pid < /tmp/residual-workbench.pid && [[ "$residual_worker_pid" =~ ^[0-9]+$ ]] && kill -0 "$residual_worker_pid" 2>/dev/null && mapfile -d '' residual_worker_argv < "/proc/$residual_worker_pid/cmdline" && [ "\${residual_worker_argv[1]-}" = "-m" ] && [ "\${residual_worker_argv[2]-}" = "residual.workbench.browser_worker" ]; then echo RESIDUAL_WORKER_READY; else python3 -m residual.workbench.browser_worker --fifo /tmp/residual-workbench.fifo --pid-file /tmp/residual-workbench.pid --mailbox /data --root /opt/residual --output-root /opt/residual/runs/missions & fi`;
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
                    const timeout = setTimeout(() => {
                        if (!residualShellRun || residualShellRun.missionId !== request.id) return;
                        terminateResidualWorker();
                        residualShellRun = null;
                        residualWorkerReady = false;
                        residualWorkerPoisoned = true;
                        residualShellCommandBusy = false;
                        residualShellInputBuffer = "";
                        reject(new Error("Persistent guest mission timed out; restart required"));
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
