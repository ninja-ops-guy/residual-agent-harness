#!/usr/bin/env python3
"""Add Mission Control without changing the M4 trust boundary or evidence schemas."""
from pathlib import Path
import shutil
import sys
from qualify_webvm import replace_once


def patch(text):
    text = replace_once(text, "<script>\n", "<script>\n\timport { mountMissionControl } from './mission-control-world.js';\n")
    text = replace_once(text, 'var residualBridgeBuffer = "";',
                        'var residualWorkbench = null;\n\tvar residualDataDevice = null;\n\tvar residualShellTail = "";\n\tvar residualShellReady = false;\n\tvar residualBridgeBuffer = "";')
    text = replace_once(text, 'const out = residualDecoder.decode(bytes, {stream:true});', '''const out = residualDecoder.decode(bytes, {stream:true});
        residualShellTail = (residualShellTail + out).slice(-2048).replace(/\\x1b\\[[0-9;?]*[A-Za-z]/g, "");
        if (residualShellTail.includes("residual@demo:~/residual-agent-harness$")) residualShellReady = true;
        residualWorkbench?.onOutput(out);''')
    text = replace_once(text, 'var dataDevice = await CheerpX.DataDevice.create();',
                        'var dataDevice = await CheerpX.DataDevice.create();\n\t\tresidualDataDevice = dataDevice;')
    text = replace_once(text, 'term.onData(readData);', '''term.onData(readData);
        residualWorkbench = mountMissionControl({
            ready: () => !!cx && !!residualDataDevice && residualShellReady,
            focus: () => term.focus(),
            mailbox: (path, text) => residualDataDevice.writeFile(path, text),
            run: async (request) => {
                if (!/^m-[a-f0-9]{32}$/.test(request.id)) throw new Error("Invalid mission ID");
                const name = "/" + request.id + ".json";
                await residualDataDevice.writeFile(name, JSON.stringify(request));
                const args = request.mode === "build"
                    ? ["-m", "residual.workbench.conversation_build", "--request", "/data" + name, "--mailbox", "/data", "--root", "/opt/residual", "--output-root", "/opt/residual/runs/missions", "--stream"]
                    : ["-m", "residual.workbench", "run", "--request", "/data" + name, "--mailbox", "/data", "--root", "/opt/residual", "--output-root", "/opt/residual/runs/missions", "--stream"];
                return await cx.run("/usr/bin/python3", args, configObj.opts);
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
    for name in ('mission-control.js', 'mission-control-world.js', 'mission-preview.js', 'provider-session.js'):
        shutil.copyfile(here / name, source.parent / name)
    provider = site / 'provider'; provider.mkdir(parents=True, exist_ok=True)
    for src, dst in [('provider.html', 'index.html'), ('provider.js', 'provider.js'), ('provider-session.js', 'provider-session.js')]:
        shutil.copyfile(here / src, provider / dst)


if __name__ == '__main__':
    install(Path(sys.argv[1]), Path(sys.argv[2]))