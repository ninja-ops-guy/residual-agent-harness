// External controller client; never import this into the OpenClaw plugin runtime.
import { signCommand, PROTOCOL, requireThat, MAX_WIRE_BYTES, ControlError } from './protocol.mjs';
import { randomUUID, createPrivateKey } from 'node:crypto';
import { readFileSync, lstatSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { ROUTE } from './route.mjs';

function exactObject(value, required, optional = []) {
  requireThat(value && typeof value === 'object' && !Array.isArray(value), 'CONFIG_INVALID');
  requireThat(required.every(k => Object.hasOwn(value,k)) &&
    Object.keys(value).every(k => required.includes(k) || optional.includes(k)), 'CONFIG_INVALID');
}

export function readControllerConfig(configPath) {
  const stat=lstatSync(configPath);
  requireThat(stat.isFile() && !stat.isSymbolicLink(),'UNSAFE_CONFIG_PATH');
  const cfg=JSON.parse(readFileSync(configPath,'utf8'));
  exactObject(cfg,['endpoint','tokenEnv','keyId'],['privateKeyFile']);
  requireThat(typeof cfg.endpoint==='string' && typeof cfg.tokenEnv==='string' && /^[A-Z_][A-Z0-9_]{0,127}$/.test(cfg.tokenEnv),'CONFIG_INVALID');
  requireThat(typeof cfg.keyId==='string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(cfg.keyId),'CONFIG_INVALID');
  if(Object.hasOwn(cfg,'privateKeyFile')) requireThat(typeof cfg.privateKeyFile==='string' && cfg.privateKeyFile.length>0,'CONFIG_INVALID');
  return cfg;
}

export function loadPrivateKey(path) {
  requireThat(typeof path==='string' && path.length>0,'PRIVATE_KEY_REQUIRED');
  const stat=lstatSync(path);
  requireThat(stat.isFile() && !stat.isSymbolicLink() &&
    (process.platform==='win32' || (stat.mode & 0o077)===0),'UNSAFE_KEY_PERMISSIONS');
  const privateKey=createPrivateKey(readFileSync(path));
  requireThat(privateKey.asymmetricKeyType==='ed25519','KEY_TYPE_INVALID');
  return privateKey;
}

export class ControllerClient {
  constructor({endpoint,token,privateKey,keyId,fetchImpl=fetch}) {
    const u=new URL(endpoint);
    requireThat(u.protocol==='http:' && ['127.0.0.1','[::1]'].includes(u.hostname) &&
      !u.username && !u.password && !u.search && !u.hash && (u.pathname==='/' || u.pathname===''),'ENDPOINT_DENIED');
    requireThat(typeof token==='string' && token.length>=16 && !/[\r\n]/.test(token),'TOKEN_REQUIRED');
    requireThat(keyId===undefined || (typeof keyId==='string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(keyId)),'INVALID_KEY_ID');
    this.url=u.origin+ROUTE;this.token=token;this.privateKey=privateKey;this.keyId=keyId;this.fetch=fetchImpl;
  }
  async request(method,envelope){
    const response=await this.fetch(this.url,{method,redirect:'error',signal:AbortSignal.timeout(10000),
      headers:{Authorization:`Bearer ${this.token}`,'Content-Type':'application/json'},
      body:envelope?JSON.stringify(envelope):undefined});
    requireThat(response.status===200,'CONTROL_REQUEST_FAILED');
    requireThat(response.body && typeof response.body.getReader==='function','CONTROL_RESPONSE_INVALID');
    const reader=response.body.getReader();let size=0;const parts=[];
    for(;;){const {value,done}=await reader.read();if(done)break;size+=value.length;
      if(size>1024*1024){await reader.cancel();throw new ControlError('RESPONSE_TOO_LARGE');}parts.push(Buffer.from(value));}
    let parsed;try{parsed=JSON.parse(Buffer.concat(parts).toString('utf8'));}catch{throw new ControlError('CONTROL_RESPONSE_INVALID');}
    return parsed;
  }
  async inspect(){return (await this.request('GET')).identity;}
  async command(action,body,options={}){
    requireThat(this.privateKey && this.keyId,'SIGNING_AUTHORITY_REQUIRED');
    const i=options.identity || await this.inspect();const now=Date.now();
    const command={protocol:PROTOCOL,operation_id:options.operationId || randomUUID(),runtime_id:i.runtime_id,
      instance_id:i.instance_id,config_digest:i.config_digest,issued_at_ms:now,expires_at_ms:now+20000,action,body};
    const envelope=signCommand(command,this.privateKey,this.keyId);
    requireThat(Buffer.byteLength(JSON.stringify(envelope))<=MAX_WIRE_BYTES,'REQUEST_TOO_LARGE');
    return (await this.request('POST',envelope)).result;
  }
}

export function createControllerClientFromFile(configPath,{requirePrivateKey=true,fetchImpl=fetch}={}) {
  const cfg=readControllerConfig(configPath);
  const token=process.env[cfg.tokenEnv];
  const privateKey=requirePrivateKey ? loadPrivateKey(cfg.privateKeyFile) : undefined;
  return new ControllerClient({endpoint:cfg.endpoint,token,privateKey,keyId:cfg.keyId,fetchImpl});
}

async function main(){
  // Arguments contain only paths/operation names. Tokens never appear in argv or output.
  const [action,configPath,bodyPath]=process.argv.slice(2);
  requireThat(action && configPath,'USAGE: node client.mjs ACTION CONTROLLER_CONFIG [BODY_JSON]');
  const client=createControllerClientFromFile(configPath,{requirePrivateKey:action!=='inspect'});
  if(action==='inspect'){console.log(JSON.stringify(await client.inspect(),null,2));return;}
  console.log(JSON.stringify(await client.command(action,bodyPath?JSON.parse(readFileSync(bodyPath,'utf8')):{}),null,2));
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) main().catch(error=>{
  console.error(error instanceof ControlError?error.code:'CLIENT_FAILURE');process.exitCode=1;
});
