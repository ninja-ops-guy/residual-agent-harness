const MODEL=/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}$/;

const HELP=[
  "/help                         show this command reference",
  "/status                       show guest, mission and chat state",
  "/tab chat|activity|evidence|files|terminal",
  "/mode build|live|audit        change execution mode",
  "/budget 1|2|3                 set bounded provider-call budget",
  "/model <id>                   select provider model",
  "/tokens <256..8192>           set output-token ceiling",
  "/new                          start a new browser-local conversation",
  "/detach                       next build starts a fresh artifact lineage",
  "/history                       list recent browser-local conversations",
  "/clear                         clear visible/browser-local transcript only",
  "/stop                          request cancellation of the active mission",
  "/restart                       restart a poisoned idle guest",
  "/connect                       open guided provider setup",
  "/mesh status                  show mesh attachment/control boundary",
  "/experiment distributed       show native distributed benchmark command",
  "/experiment mesh              show native mesh benchmark command",
  "/experiment pipeline          show dependency-DAG benchmark command",
  "/experiment recovery          show fail-closed repair benchmark command",
  "/terminal                      alias for /tab terminal"
].join("\n");

function tokens(input){
  const value=String(input??"").trim();
  if(!value.startsWith("/")||value.startsWith("//"))return null;
  const parts=value.slice(1).trim().split(/\s+/).filter(Boolean);
  return parts.length?parts:null;
}

function asText(value){
  if(typeof value==="string")return value;
  return JSON.stringify(value,null,2);
}

export async function executeMissionCommand(input,api){
  const parts=tokens(input);
  if(!parts)return {handled:false};
  const command=parts[0].toLowerCase(),args=parts.slice(1);
  const result=text=>({handled:true,text});

  if(command==="help"||command==="commands")return result(HELP);
  if(command==="terminal"){await api.tab("terminal");return result("Terminal view selected.");}
  if(command==="status")return result(asText(await api.status()));

  if(command==="tab"){
    const tab=(args[0]||"").toLowerCase();
    if(!["chat","activity","evidence","files","terminal"].includes(tab))return result("Usage: /tab chat|activity|evidence|files|terminal");
    await api.tab(tab);return result(`View switched to ${tab}.`);
  }
  if(command==="mode"){
    const mode=(args[0]||"").toLowerCase();
    if(!["build","live","audit"].includes(mode))return result("Usage: /mode build|live|audit");
    const selected=await api.mode(mode);return result(`Execution mode: ${selected}.`);
  }
  if(command==="budget"){
    const value=Number(args[0]);
    if(!Number.isInteger(value)||value<1||value>3)return result("Usage: /budget 1|2|3");
    await api.budget(value);return result(`Provider-call budget: ${value}.`);
  }
  if(command==="model"){
    const model=args.join(" ");
    if(!MODEL.test(model))return result("Usage: /model <provider/model-id>");
    await api.model(model);return result(`Model selected: ${model}.`);
  }
  if(command==="tokens"){
    const value=Number(args[0]);
    if(!Number.isInteger(value)||value<256||value>8192)return result("Usage: /tokens <256..8192>");
    const selected=await api.outputTokens(value);
    return result(`Output-token ceiling: ${selected}.`);
  }
  if(command==="new"){
    if(await api.busy())return result("A mission is active. Stop or finish it before starting a new chat.");
    await api.newChat();return result("Started a new browser-local conversation. Guest evidence from earlier runs is unchanged.");
  }
  if(command==="detach"){
    if(await api.busy())return result("A mission is active. Detach after it reaches a terminal state.");
    const changed=await api.detach();
    return result(changed?"Next build starts a fresh artifact lineage.":"No accepted artifact is attached to this conversation.");
  }
  if(command==="history"){
    const items=await api.history();
    return result(items.length?items.map((x,i)=>`${i+1}. ${x.title} · ${x.id}`).join("\n"):"No saved browser-local conversations.");
  }
  if(command==="clear"){
    if(await api.busy())return result("A mission is active. Visible history is not cleared mid-run.");
    await api.clear();return result("Visible/browser-local transcript cleared. Guest traces and artifacts were not deleted.");
  }
  if(command==="stop"){
    const requested=await api.stop();return result(requested?"Stop requested. Already-dispatched provider work may still incur usage.":"No active mission to stop.");
  }
  if(command==="restart"){
    const restarted=await api.restart();return result(restarted?"Guest restart requested.":"Guest restart is unavailable unless the runtime is poisoned and idle.");
  }
  if(command==="connect"){
    await api.connect();return result("Guided provider setup opened. No prompt was sent.");
  }
  if(command==="mesh"){
    if(args.length&&args[0].toLowerCase()!=="status")return result("Usage: /mesh status");
    return result(asText(await api.meshStatus()));
  }
  if(command==="experiment"){
    const kind=(args[0]||"").toLowerCase();
    if(kind==="distributed")return result("Native benchmark: residual experiment distributed --workers 1 2 4 --tasks 8 --work-ms 40 --repeats 3 --output runs/distributed.json");
    if(kind==="mesh")return result("Native benchmark: residual experiment mesh --messages 1000 --peers 4 --repeats 3 --output runs/mesh.json");
    if(kind==="pipeline")return result("Native benchmark: residual experiment pipeline --workers 1 2 4 --width 4 --depth 2 --work-ms 40 --repeats 3 --output runs/pipeline.json");
    if(kind==="recovery")return result("Native benchmark: residual experiment recovery --bad-ms 20 --good-ms 40 --repeats 3 --output runs/recovery.json");
    return result("Usage: /experiment distributed|mesh|pipeline|recovery");
  }
  return result(`Unknown command: /${command}\n\n${HELP}`);
}

export function missionCommandHelp(){return HELP;}
