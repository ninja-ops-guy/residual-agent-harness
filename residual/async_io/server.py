from __future__ import annotations
import asyncio
class AsyncHTTPServer:
    def __init__(self,handler,host="127.0.0.1",port=8765): self.handler,self.host,self.port=handler,host,int(port); self._server=None
    async def start(self): self._server=await asyncio.start_server(self._handle,self.host,self.port); return self
    async def close(self):
        if self._server: self._server.close(); await self._server.wait_closed()
    async def _handle(self,reader,writer):
        try:
            head=await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"),5); lines=head.decode("latin1").split("\r\n"); method,path,_=lines[0].split(" ",2); headers={k.strip().lower():v.strip() for line in lines[1:] if ":" in line for k,v in [line.split(":",1)]}; length=min(int(headers.get("content-length","0") or 0),1048576); body=await reader.readexactly(length) if length else b""; status,out_headers,payload=await self.handler(method,path,headers,body); reason={200:"OK",201:"Created",202:"Accepted",400:"Bad Request",404:"Not Found",409:"Conflict",500:"Internal Server Error"}.get(status,"OK"); out_headers={**out_headers,"content-length":str(len(payload)),"connection":"close"}; writer.write((f"HTTP/1.1 {status} {reason}\r\n"+"".join(f"{k}: {v}\r\n" for k,v in out_headers.items())+"\r\n").encode("latin1")+payload); await writer.drain()
        except Exception: pass
        finally: writer.close(); await writer.wait_closed()
