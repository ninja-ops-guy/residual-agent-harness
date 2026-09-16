#!/usr/bin/env python3
"""Small, fail-closed UI/runtime patches applied after patch_webvm.py source.

No verifier or harness security policy is modified. The per-image overlay
namespace prevents a regenerated filesystem from inheriting unrelated blocks.
"""
from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"WebVM qualification anchor changed: {old[:80]!r}")
    return text.replace(old, new, 1)


def qualify(text: str) -> str:
    text = replace_once(text, 'new Terminal({cursorBlink:true,',
                        'new Terminal({screenReaderMode:true, theme:{background:"#000000",foreground:"#39ff68"}, cursorBlink:true,')
    text = replace_once(text, 'var residualBridgeBuffer = "";',
                        'var residualBridgeBuffer = "";\n\tconst residualDecoder = new TextDecoder();')
    text = replace_once(text, 'const out = new TextDecoder().decode(bytes);',
                        'const out = residualDecoder.decode(bytes, {stream:true});')
    old = '\t\tif(out.includes("RESIDUAL BOOT: guest process attached")) residualVmState = "VM READY · GUEST ATTACHED";\n\t\tresidualBridgeBuffer += out;'
    new = '\t\tresidualBridgeBuffer += out;\n\t\tif(residualBridgeBuffer.includes("RESIDUAL BOOT: guest process attached")) residualVmState = "VM READY · GUEST ATTACHED";\n\t\tif(residualBridgeBuffer.length > 1048576) { residualBridgeBuffer = ""; residualVmState = "VM BRIDGE ERROR · console line too large"; return; }'
    text = replace_once(text, old, new)
    text = replace_once(text, 'CheerpX.IDBDevice.create(cacheId)',
                        'CheerpX.IDBDevice.create(configObj.residualCacheId || cacheId)')
    old_bar = 'position:fixed;top:0.35rem;left:15rem;right:24rem;z-index:60;display:flex;align-items:center;gap:0.5rem;pointer-events:none;font-family:monospace;font-size:11px;color:#39ff68'
    new_bar = 'position:fixed;box-sizing:border-box;top:2.5rem;left:0;right:0;z-index:60;display:flex;flex-wrap:wrap;align-items:center;gap:0.5rem;padding:0.5rem;background:#000;border-bottom:1px solid #39ff68;pointer-events:none;font-family:monospace;font-size:11px;color:#39ff68'
    text = replace_once(text, old_bar, new_bar)
    text = replace_once(text, '<span style="opacity:.72">{residualVmState}</span>',
                        '<span role="status" style="opacity:.85;flex-basis:100%;order:1;overflow-wrap:anywhere">{residualVmState}</span>')
    text = replace_once(text, '<div class="absolute top-10 bottom-0 left-0 right-0">',
                        '<div class="absolute top-[7.5rem] bottom-0 left-0 right-0">')
    return text


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: qualify_webvm.py PATH_TO_PATCHED_WEBVM_SVELTE')
    path = Path(sys.argv[1])
    path.write_text(qualify(path.read_text()))
