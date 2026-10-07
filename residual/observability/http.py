from __future__ import annotations
from .exporter import render_prometheus
class MetricsEndpoint:
    def __init__(self,registry): self.registry=registry
    async def __call__(self,method,path,headers,body):
        if method=="GET" and path=="/metrics": return 200,{"content-type":"text/plain; version=0.0.4; charset=utf-8"},render_prometheus(self.registry).encode()
        return 404,{"content-type":"text/plain"},b"not found\n"
