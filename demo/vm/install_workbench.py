#!/usr/bin/env python3
"""Add Mission Control without changing the M4 trust boundary or evidence schemas."""
from pathlib import Path
import shutil
import sys
from qualify_webvm import replace_once
from residual.workbench.host_recovery import build_recovery_command


def _javascript_shell_template(command: str) -> str:
    """Escape Bash syntax through a JavaScript template literal."""
    return command.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')


def patch(text):
    recovery = build_recovery_command(
        pid_file='/tmp/residual-workbench.pid',
        fifo='/tmp/residual-workbench.fifo',
        poison_file='/tmp/residual-workbench.poison',
        active_lock='/opt/residual/runs/missions/.active',
        mission_id='__RESIDUAL_MISSION_ID__',
        marker='__RESIDUAL_RECOVERY_MARKER__',
    )
    recovery_js = _javascript_shell_template(recovery)

    text = replace_once(text, "<script>\n", "<script>\n\timport { mountMissionControl } from './mission-control-world.js';\n")
    text = replace_once(text, 'var residualBridgeBuffer = "";',
                        'var residualWorkbench = null;\n\tvar residualDataDevice = null;\n\tvar residualShellTail = "";\n\tvar residualShellReady = false;\n\tvar residualShellCommandBusy = false;\n\tvar residualShellRun = null;\n\tvar residualShellInputBuffer = "";\n\tvar residualWorkerReady = false;\n\tvar residualWorkerPoisoned = false;\n\tvar residualWorkerStart = null;\n\tvar residualWorkerRecovery = null;\n\tvar residualWorkerRecoverySeq = 0;\n\tvar residualBridgeBuffer = "";')
    output_patch = """const out = residualDecoder.decode(bytes, {stream:true});
        residualShellTail = (residualShellTail + out).slice(-4096).replace(/\\x1b\\[[0-9;?]*[A-Za-z]/g, "");
        if (residualShellTail.includes("residual@demo:~/residual-agent-harness$")) residualShellReady = true;
        // Project authoritative guest frames before resolving worker lifecycle
        // markers that may share the same terminal output chunk.
        residualWorkbench?.onOutput(out);
        if (residualWorkerRecovery) {
            const recoveryMatch = residualShellTail.match(new RegExp(residualWorkerRecovery.marker + ":([0-9]+)"));
            if (recoveryMatch) {
                const current = residualWorkerRecovery;
                residualWorkerRecovery = null;
                current.finish(Number(recoveryMatch[1]));
            }
        }
        if (residualShellTail.includes("RESIDUAL_WORKER_POISONED")) {
            residualWorkerReady = false;
            residualWorkerPoisoned = true;
            if (residualWorkerStart) {
                const current = residualWorkerStart;
                residualWorkerStart = null;
                residualShellCommandBusy = false;
                residualShellInputBuffer = "";
                current.fail(new Error("Guest worker is durably poisoned; reset guest before retry"));
            }
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
                if (fatalMatch) {
                    // A fatal runtime signal poisons the guest durably before the
                    // mission promise settles, so page reload cannot silently
                    // create/reuse another worker in the same suspect guest.
                    residualWorkerReady = false;
                    residualWorkerPoisoned = true;
                    (async () => {
                        try { await terminateResidualWorker(current.missionId); } catch (_) {}
                        residualShellCommandBusy = false;
                        residualShellInputBuffer = "";
                        current.finish({status: Number(match[1]), fatal: true});
                    })();
                } else {
                    residualShellCommandBusy = false;
                    const queuedInput = residualShellInputBuffer;
                    residualShellInputBuffer = "";
                    if (queuedInput) readData(queuedInput);
                    current.finish({status: Number(match[1]), fatal: false});
                }
            }
        }"""
    text = replace_once(text, 'const out = residualDecoder.decode(bytes, {stream:true});', output_patch)
    text = replace_once(text, 'var dataDevice = await CheerpX.DataDevice.create();',
                        'var dataDevice = await CheerpX.DataDevice.create();\n\t\tresidualDataDevice = dataDevice;')
    wiring = """term.onData(data => {
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
        async function terminateResidualWorker(missionId) {
            if (residualWorkerRecovery) return await residualWorkerRecovery.promise;
            residualWorkerReady = false;
            residualWorkerPoisoned = true;
            const marker = "RESIDUAL_WORKER_RECOVERY_" + (++residualWorkerRecoverySeq);
            let resolveRecovery, rejectRecovery;
            const promise = new Promise((resolve, reject) => { resolveRecovery = resolve; rejectRecovery = reject; });
            const timeout = setTimeout(() => {
                if (!residualWorkerRecovery || residualWorkerRecovery.marker !== marker) return;
                residualWorkerRecovery = null;
                rejectRecovery(new Error("Persistent guest worker recovery did not complete"));
            }, 15000);
            residualWorkerRecovery = {
                marker,
                promise,
                finish: status => {
                    clearTimeout(timeout);
                    if (status === 0) resolveRecovery(status);
                    else rejectRecovery(new Error("Persistent guest worker recovery failed closed"));
                }
            };
            const command = `__RECOVERY_COMMAND__`
                .replaceAll("__RESIDUAL_MISSION_ID__", missionId || "")
                .replaceAll("__RESIDUAL_RECOVERY_MARKER__", marker);
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
            const timeout = setTimeout(() => {
                if (!residualWorkerStart) return;
                const current = residualWorkerStart;
                residualWorkerStart = null;
                residualWorkerReady = false;
                residualWorkerPoisoned = true;
                (async () => {
                    try { await terminateResidualWorker(null); } catch (_) {}
                    residualShellCommandBusy = false;
                    residualShellInputBuffer = "";
                    current.fail(new Error("Persistent guest worker did not become ready; reset guest before retry"));
                })();
            }, 60000);
            residualWorkerStart = {
                promise,
                finish: () => { clearTimeout(timeout); resolveStart(); },
                fail: error => { clearTimeout(timeout); rejectStart(error); }
            };
            // A durable poison record always wins over reuse/start. Reuse only a
            // surviving worker whose PID file, FIFO, process and /proc argv all
            // identify the expected long-lived module.
            const command = `if [ -e /tmp/residual-workbench.poison ] || [ -L /tmp/residual-workbench.poison ]; then printf 'RESIDUAL_WORKER_%s\\n' POISONED; elif [ -f /tmp/residual-workbench.pid ] && [ ! -L /tmp/residual-workbench.pid ] && [ -O /tmp/residual-workbench.pid ] && [ -p /tmp/residual-workbench.fifo ] && read -r residual_worker_pid < /tmp/residual-workbench.pid && [[ "$residual_worker_pid" =~ ^[0-9]+$ ]] && kill -0 "$residual_worker_pid" 2>/dev/null && mapfile -d '' residual_worker_argv < "/proc/$residual_worker_pid/cmdline" && [ "\${residual_worker_argv[1]-}" = "-m" ] && [ "\${residual_worker_argv[2]-}" = "residual.workbench.browser_worker" ]; then echo RESIDUAL_WORKER_READY; else python3 -m residual.workbench.browser_worker --fifo /tmp/residual-workbench.fifo --pid-file /tmp/residual-workbench.pid --poison-file /tmp/residual-workbench.poison --mailbox /data --root /opt/residual --output-root /opt/residual/runs/missions & fi`;
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
                        const current = residualShellRun;
                        residualShellRun = null;
                        residualWorkerReady = false;
                        residualWorkerPoisoned = true;
                        (async () => {
                            try { await terminateResidualWorker(request.id); } catch (_) {}
                            residualShellCommandBusy = false;
                            residualShellInputBuffer = "";
                            current.fail(new Error("Persistent guest mission timed out; reset guest before retry"));
                        })();
                    }, 330000);
                    residualShellRun = {
                        missionId: request.id,
                        finish: value => { clearTimeout(timeout); resolve(value); },
                        fail: error => { clearTimeout(timeout); reject(error); }
                    };
                    // The shell writes only a validated mission id and mode to a
                    // FIFO using its builtin printf. Prompt/source data remains
                    // in the DataDevice request file and is never shell-expanded.
                    const command = `printf '%s\\n' '${request.id} ${request.mode}' > /tmp/residual-workbench.fifo`;
                    readData(command + "\\r");
                });
            }
        });""".replace('__RECOVERY_COMMAND__', recovery_js)
    text = replace_once(text, 'term.onData(readData);', wiring)
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
