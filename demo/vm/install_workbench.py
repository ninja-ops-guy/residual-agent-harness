#!/usr/bin/env python3
"""Add Mission Control without changing the M4 trust boundary or evidence schemas."""
from pathlib import Path
import shutil
import sys
from qualify_webvm import replace_once


def patch(text):
    text = replace_once(text, "<script>\n", "<script>\n\timport { mountMissionControl } from './mission-control-world.js';\n")
    text = replace_once(text, 'var residualBridgeBuffer = "";',
                        'var residualWorkbench = null;\n\tvar residualDataDevice = null;\n\tvar residualShellTail = "";\n\tvar residualShellReady = false;\n\tvar residualShellCommandBusy = false;\n\tvar residualShellRun = null;\n\tvar residualBridgeBuffer = "";')
    text = replace_once(text, 'const out = residualDecoder.decode(bytes, {stream:true});', '''const out = residualDecoder.decode(bytes, {stream:true});
        residualShellTail = (residualShellTail + out).slice(-4096).replace(/\\x1b\\[[0-9;?]*[A-Za-z]/g, "");
        if (residualShellTail.includes("residual@demo:~/residual-agent-harness$")) residualShellReady = true;
        // Project authoritative guest frames before resolving a shell-dispatch
        // completion marker that may share the same terminal output chunk.
        residualWorkbench?.onOutput(out);
        if (residualShellRun) {
            const marker = new RegExp("RESIDUAL_HOST_RUN_" + residualShellRun.missionId + ":([0-9]+)");
            const match = residualShellTail.match(marker);
            if (match) {
                const current = residualShellRun;
                residualShellRun = null;
                residualShellCommandBusy = false;
                current.finish({status: Number(match[1])});
            }
        }''')
    text = replace_once(text, 'var dataDevice = await CheerpX.DataDevice.create();',
                        'var dataDevice = await CheerpX.DataDevice.create();\n\t\tresidualDataDevice = dataDevice;')
    text = replace_once(text, 'term.onData(readData);', '''term.onData(data => {
            // Mission Control launches Python as a child of this one long-lived
            // shell. Ignore interactive keystrokes while that bounded child is
            // active so user input cannot splice into the dispatch command.
            if (!residualShellCommandBusy) readData(data);
        });
        residualWorkbench = mountMissionControl({
            ready: () => !!cx && !!residualDataDevice && residualShellReady && !residualShellCommandBusy,
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
                const name = "/" + request.id + ".json";
                await residualDataDevice.writeFile(name, JSON.stringify(request));
                const entry = request.mode === "build"
                    ? "residual.workbench.browser_build"
                    : "residual.workbench.browser_run";
                const verb = request.mode === "build" ? "" : " run";
                const command = `python3 -m ${entry}${verb} --request /data${name} --mailbox /data --root /opt/residual --output-root /opt/residual/runs/missions --stream; __residual_rc=$?; printf '\\nRESIDUAL_HOST_RUN_${request.id}:%s\\n' "$__residual_rc"`;
                residualShellCommandBusy = true;
                residualShellTail = "";
                return await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        if (!residualShellRun || residualShellRun.missionId !== request.id) return;
                        residualShellRun = null;
                        residualShellCommandBusy = false;
                        reject(new Error("Guest shell dispatch timed out"));
                    }, 330000);
                    residualShellRun = {
                        missionId: request.id,
                        finish: value => { clearTimeout(timeout); resolve(value); }
                    };
                    // Do not call cx.run() here. WebVM already owns one
                    // long-lived cx.run() for this interactive shell; launching
                    // the mission as its child keeps process lifecycle inside
                    // the guest instead of re-entering the host run API.
                    readData(command + "\\r");
                });
            }
        });''')
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
