#!/usr/bin/env python3
"""Patch upstream WebVM for the RESIDUAL public demo.

Kept outside the Pages YAML so upstream anchor changes fail closed without
making the workflow itself unparsable.
"""
from __future__ import annotations

import sys
from pathlib import Path

from harden_serviceworker import harden as harden_serviceworker


def require_once(text: str, needle: str, label: str) -> None:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label} moved: expected 1 occurrence, found {count}")


def patch_source(path: Path) -> None:
    text = path.read_text()

    anchor = "\tvar sideBarPinned = false;"
    require_once(text, anchor, "WebVM state anchor")
    bridge = r'''
	var residualBridgeBuffer = "";
	var residualCloudReady = false;
	var residualCloudLabel = "ENABLE CLOUD ✦";
	var residualCloudSdkPromise = null;
	var residualVmState = "VM BOOTING…";
	const residualGuestGenerationKey = "residual.guest.generation.v1";
	function residualGuestGeneration()
	{
		try
		{
			const value = sessionStorage.getItem(residualGuestGenerationKey);
			return /^[0-9a-f]{16}$/.test(value || "") ? value : "base";
		}
		catch(_)
		{
			return "base";
		}
	}
	function residualRestartGuest()
	{
		const next = crypto.randomUUID().replaceAll("-", "").slice(0, 16);
		try
		{
			sessionStorage.setItem(residualGuestGenerationKey, next);
		}
		catch(_)
		{
			throw new Error("Guest restart storage unavailable");
		}
		residualVmState = "VM RESTARTING · FRESH OVERLAY…";
		location.reload();
	}
	function residualDecode64url(s)
	{
		s=s.replace(/-/g,"+").replace(/_/g,"/");
		while(s.length%4)s+="=";
		const bin=atob(s),bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));
		return new TextDecoder().decode(bytes);
	}
	function residualEncode64url(text)
	{
		const bytes=new TextEncoder().encode(text);let bin="";
		for(const b of bytes)bin+=String.fromCharCode(b);
		return btoa(bin).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
	}
	function residualPuterText(result)
	{
		if(typeof result==="string")return result;
		const c=result?.message?.content;
		if(typeof c==="string")return c;
		if(Array.isArray(c))return c.map(p=>typeof p==="string"?p:(p?.text||p?.content||"")).join("");
		if(typeof result?.text==="string")return result.text;
		if(typeof result?.content==="string")return result.content;
		throw new Error("Puter returned no text content");
	}
	function residualLoadPuterSdk()
	{
		if(window.puter?.auth)return Promise.resolve(window.puter);
		if(residualCloudSdkPromise)return residualCloudSdkPromise;
		residualCloudSdkPromise=new Promise((resolve,reject)=>{
			const script=document.createElement("script");
			script.src="https://js.puter.com/v2/";
			script.async=true;
			script.dataset.residualPuterSdk="1";
			const fail=(message)=>{residualCloudSdkPromise=null;script.remove();reject(new Error(message));};
			const timer=setTimeout(()=>fail("Puter SDK load timed out"),10000);
			script.onload=()=>{
				clearTimeout(timer);
				if(window.puter?.auth)resolve(window.puter);
				else fail("Puter SDK loaded without auth API");
			};
			script.onerror=()=>{clearTimeout(timer);fail("Puter SDK failed to load");};
			document.head.appendChild(script);
		});
		return residualCloudSdkPromise;
	}
	function residualSend(id,obj)
	{
		if(cxReadFunc==null)return;
		const wire=`__RESIDUAL_BROWSER_RESPONSE__:${id}:${residualEncode64url(JSON.stringify(obj))}\n`;
		readData(wire);
	}
	async function residualHandleLine(line)
	{
		const m=line.match(/^__RESIDUAL_BROWSER_REQUEST__:([0-9a-f]+):([A-Za-z0-9_-]+)$/);
		if(!m)return;
		const id=m[1];let req;
		try{req=JSON.parse(residualDecode64url(m[2]));}catch(e){residualSend(id,{ok:false,error:"browser_bridge_invalid_request"});return;}
		if(!residualCloudReady||!window.puter?.ai){residualSend(id,{ok:false,error:"browser_bridge_auth_required"});return;}
		residualVmState="CLOUD INFERENCE…";
		try
		{
			const maxTokens=Number.isInteger(req.max_output_tokens)?Math.max(1,Math.min(req.max_output_tokens,512)):256;
			const result=await window.puter.ai.chat(req.messages,{model:req.model||"gpt-5.6-luna",max_tokens:maxTokens,normalize:true});
			const usage=result?.usage||{};
			residualSend(id,{ok:true,text:residualPuterText(result),finish_reason:result?.finish_reason||result?.message?.finish_reason||"stop",usage:{input_tokens:Number.isInteger(usage.prompt_tokens)?usage.prompt_tokens:(Number.isInteger(usage.input_tokens)?usage.input_tokens:null),output_tokens:Number.isInteger(usage.completion_tokens)?usage.completion_tokens:(Number.isInteger(usage.output_tokens)?usage.output_tokens:null)}});
			residualVmState="VM READY · CLOUD RESPONSE RETURNED";
		}
		catch(e)
		{
			console.warn("Puter inference failed",e);
			residualSend(id,{ok:false,error:"browser_bridge_remote_error"});
			residualVmState="VM READY · CLOUD REQUEST FAILED";
		}
	}
	async function enableResidualCloud()
	{
		residualCloudLabel="LOADING CLOUD…";
		try
		{
			const puterSdk=await residualLoadPuterSdk();
			if(!puterSdk.auth.isSignedIn?.())await puterSdk.auth.signIn({attempt_temp_user_creation:true});
			const user=await puterSdk.auth.getUser();
			residualCloudReady=true;
			residualCloudLabel="CLOUD READY ✓"+(user?.username?` · ${user.username}`:"");
		}
		catch(e)
		{
			console.warn("Puter sign-in unavailable",e);
			residualCloudReady=false;
			residualCloudLabel="ENABLE CLOUD ✦";
		}
	}
'''
    text = text.replace(anchor, anchor + bridge, 1)

    old_write = "\t\tterm.write(new Uint8Array(buf));"
    require_once(text, old_write, "WebVM writeData hook")
    new_write = '''\t\tconst bytes = new Uint8Array(buf);\n\t\tterm.write(bytes);\n\t\tconst out = new TextDecoder().decode(bytes);\n\t\tif(out.includes("RESIDUAL BOOT: guest process attached")) residualVmState = "VM READY · GUEST ATTACHED";\n\t\tresidualBridgeBuffer += out;\n\t\tconst parts = residualBridgeBuffer.split(/\\r?\\n/);\n\t\tresidualBridgeBuffer = parts.pop() || "";\n\t\tfor(const line of parts) residualHandleLine(line.trim());'''
    text = text.replace(old_write, new_write, 1)

    old_init = '''\t\ttry\n\t\t{\n\t\t\tawait initCheerpX();\n\t\t}\n\t\tcatch(e)\n\t\t{\n\t\t\tprintMessage(unexpectedErrorMessage);\n\t\t\tprintMessage([e.toString()]);\n\t\t\treturn;\n\t\t}'''
    require_once(text, old_init, "WebVM init hook")
    new_init = '''\t\ttry\n\t\t{\n\t\t\tresidualVmState = window.crossOriginIsolated ? "VM RUNTIME LOADING…" : "VM WAITING FOR ISOLATION RELOAD…";\n\t\t\tawait initCheerpX();\n\t\t}\n\t\tcatch(e)\n\t\t{\n\t\t\tresidualVmState = "VM RUNTIME ERROR · " + e.toString().slice(0,100);\n\t\t\tprintMessage(unexpectedErrorMessage);\n\t\t\tprintMessage([e.toString()]);\n\t\t\treturn;\n\t\t}'''
    text = text.replace(old_init, new_init, 1)

    console_hook = "\t\tcxReadFunc = cx.setCustomConsole(writeData, term.cols, term.rows);"
    require_once(text, console_hook, "WebVM console hook")
    text = text.replace(console_hook, console_hook + '\n\t\tresidualVmState = "VM CONSOLE ATTACHED · STARTING GUEST…";', 1)

    run_hook = "\t\t\tawait cx.run(configObj.cmd, configObj.args, configObj.opts);"
    require_once(text, run_hook, "WebVM run hook")
    text = text.replace(run_hook, '\t\t\tresidualVmState = "VM GUEST STARTING…";\n' + run_hook, 1)

    main_marker = '<main class="relative w-full h-full">'
    require_once(text, main_marker, "WebVM main marker")
    topbar = '''<main class="relative w-full h-full">\n\t<div style="position:fixed;top:0.35rem;left:15rem;right:24rem;z-index:60;display:flex;align-items:center;gap:0.5rem;pointer-events:none;font-family:monospace;font-size:11px;color:#39ff68">\n\t\t<strong style="letter-spacing:.12em">RESIDUAL / LIVE VM</strong>\n\t\t<span style="opacity:.72">{residualVmState}</span>\n\t\t<button on:click={enableResidualCloud} disabled={residualCloudReady} style="pointer-events:auto;margin-left:auto;border:1px solid #39ff68;background:#031006;color:#39ff68;padding:5px 9px;font-family:monospace;font-size:10px;cursor:pointer">{residualCloudLabel}</button>\n\t</div>'''
    text = text.replace(main_marker, topbar, 1)
    path.write_text(text)


def patch_app(path: Path) -> None:
    text = path.read_text()
    plausible = '<script data-domain="webvm.io" src="https://plausible.leaningtech.com/js/script.js"></script>'
    require_once(text, plausible, "WebVM Plausible script")
    path.write_text(text.replace(plausible, '', 1))


def patch_index(path: Path) -> None:
    text = path.read_text()
    if "plausible.leaningtech.com" in text:
        raise SystemExit("Plausible analytics survived the app patch")
    if "js.puter.com/v2" in text:
        raise SystemExit("unexpected eager Puter SDK reference in built index")
    marker = "<head>"
    require_once(text, marker, "WebVM built index head marker")
    if 'name="theme-color"' not in text:
        text = text.replace(marker, '<head>\n<meta name="theme-color" content="#000000">', 1)
    path.write_text(text)


def patch_serviceworker(path: Path) -> None:
    text = path.read_text()
    old = '''\tcatch (e) {\n\t\tconsole.error(e)\n\t}\n\tif (r.status === 0) {'''
    require_once(text, old, "WebVM service-worker fetch failure hook")
    new = '''\tcatch (e) {\n\t\tconsole.warn("Serviceworker fetch failed:", request.url, e);\n\t\treturn Response.error();\n\t}\n\tif (r.status === 0) {'''
    path.write_text(text.replace(old, new, 1))
    harden_serviceworker(path)


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"source", "app", "index", "serviceworker"}:
        raise SystemExit("usage: patch_webvm.py {source|app|index|serviceworker} PATH")
    path = Path(sys.argv[2])
    if sys.argv[1] == "source":
        patch_source(path)
    elif sys.argv[1] == "app":
        patch_app(path)
    elif sys.argv[1] == "index":
        patch_index(path)
    else:
        patch_serviceworker(path)


if __name__ == "__main__":
    main()