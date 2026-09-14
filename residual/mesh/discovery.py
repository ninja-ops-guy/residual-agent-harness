"""Opt-in LAN mDNS discovery. Discovery is never key admission or execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import ipaddress
from typing import Callable

from ..core import ContractError, canonical, strict_json

SERVICE = '_residual._tcp.local.'


@dataclass(frozen=True)
class DiscoveredPeer:
    device_id: str
    addresses: tuple[str, ...]
    port: int
    signing_fingerprint: str
    capabilities: tuple[str, ...]


def announcement(identity) -> dict[bytes,bytes]:
    caps = tuple(identity.capabilities)
    if len(caps) > 8 or any(not isinstance(x,str) or not 1 <= len(x.encode()) <= 24 for x in caps):
        raise ContractError('mDNS supports at most eight short capability labels')
    properties = {b'version':b'1', b'id':identity.device_id.encode(),
        b'signing_fingerprint':hashlib.sha256(bytes.fromhex(identity.public_key)).hexdigest().encode(),
        b'capabilities':canonical(caps).encode()}
    if any(len(k)+len(v)+1 > 255 for k,v in properties.items()):
        raise ContractError('mDNS TXT field too large')
    return properties


def parse_announcement(info) -> DiscoveredPeer:
    try:
        props = info.properties
        if (set(props) != {b'version',b'id',b'signing_fingerprint',b'capabilities'}
                or any(not isinstance(k,bytes) or not isinstance(v,bytes) or len(k)+len(v)+1 > 255 for k,v in props.items())
                or props[b'version'] != b'1'):
            raise ValueError()
        device = props[b'id'].decode('ascii')
        if not 1 <= len(device) <= 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in device):
            raise ValueError()
        fp = props[b'signing_fingerprint'].decode('ascii')
        if len(fp) != 64 or bytes.fromhex(fp).hex() != fp:
            raise ValueError()
        caps = strict_json(props[b'capabilities'].decode('utf-8'))
        if not isinstance(caps,list) or len(caps)>8 or any(not isinstance(c,str) or not 1<=len(c.encode())<=24 for c in caps):
            raise ValueError()
        addresses = tuple(sorted(set(info.parsed_addresses())))
        if not addresses or len(addresses)>8 or type(info.port) is not int or not 1<=info.port<=65535:
            raise ValueError()
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_multicast or ip.is_unspecified or not (ip.is_private or ip.is_link_local or ip.is_loopback):
                raise ValueError()
        return DiscoveredPeer(device,addresses,info.port,fp,tuple(caps))
    except Exception:
        raise ContractError('invalid mDNS candidate') from None


class MDNSDiscovery:
    def __init__(self, identity, *, address: str, port: int,
                 on_candidate: Callable, on_removed: Callable | None = None):
        ip = ipaddress.ip_address(address)
        if ip.is_unspecified or ip.is_multicast or not (ip.is_private or ip.is_link_local or ip.is_loopback):
            raise ContractError('mDNS requires a LAN interface address')
        if type(port) is not int or not 1 <= port <= 65535 or not callable(on_candidate):
            raise ContractError('invalid discovery listener')
        self.identity,self.address,self.port = identity,address,port
        self.on_candidate,self.on_removed = on_candidate,on_removed
        self._properties = announcement(identity)
        self._zc = self._browser = self._info = None
        self._tasks = set(); self._pending = {}; self._candidates = {}; self.rejected = 0

    async def start(self):
        from zeroconf import ServiceInfo
        from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser
        if self._zc is not None: raise ContractError('discovery already started')
        self._zc = AsyncZeroconf(interfaces=[self.address])
        name = hashlib.sha256(self.identity.device_id.encode()).hexdigest()[:32]
        self._info = ServiceInfo(SERVICE,name+'.'+SERVICE,
            addresses=[ipaddress.ip_address(self.address).packed],port=self.port,
            properties=self._properties,server=name+'.local.')
        try:
            await self._zc.async_register_service(self._info)
            self._browser = AsyncServiceBrowser(self._zc.zeroconf,SERVICE,handlers=[self._changed])
        except BaseException:
            await self.close(); raise
        return self

    def _changed(self, zeroconf, service_type, name, state_change):
        from zeroconf import ServiceStateChange
        if name == self._info.name: return
        previous = self._pending.pop(name,None)
        if previous is not None: previous.cancel()
        if state_change == ServiceStateChange.Removed:
            peer = self._candidates.pop(name,None)
            if peer and self.on_removed:
                try: self.on_removed(peer)
                except Exception: self.rejected += 1
            return
        if len(self._tasks) >= 32 or len(self._candidates) >= 128:
            self.rejected += 1; return
        task = asyncio.create_task(self._resolve(zeroconf,service_type,name))
        self._tasks.add(task); self._pending[name] = task
        def done(completed):
            self._tasks.discard(completed)
            if self._pending.get(name) is completed: self._pending.pop(name,None)
        task.add_done_callback(done)

    async def _resolve(self, zeroconf, service_type, name):
        from zeroconf.asyncio import AsyncServiceInfo
        try:
            info = AsyncServiceInfo(service_type,name)
            if not await info.async_request(zeroconf,2000): return
            peer = parse_announcement(info)
            if peer.device_id == self.identity.device_id: return
            if self._candidates.get(name) != peer:
                self._candidates[name] = peer
                self.on_candidate(peer)  # Advisory; the host still pins keys and certificates.
        except Exception:
            self.rejected += 1

    async def close(self):
        if self._browser is not None:
            await self._browser.async_cancel(); self._browser = None
        tasks = tuple(self._tasks)
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        if self._zc is not None:
            try:
                if self._info is not None: await self._zc.async_unregister_service(self._info)
            finally:
                await self._zc.async_close(); self._zc=None

    async def cancel(self,timeout_s=5.0):
        await asyncio.wait_for(self.close(),timeout=min(float(timeout_s),5.0))
