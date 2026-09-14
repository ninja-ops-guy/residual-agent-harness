"""Async direct TLS WebSockets and an optional opaque relay.

Transport acceptance is not receipt verification or execution permission.
The inherited single-head chat rejects divergent concurrent histories rather
than pretending a longest-chain heuristic provides consensus.
"""
from __future__ import annotations

import asyncio
from http import HTTPStatus
import logging
import secrets
import ssl
from urllib.parse import urlsplit

from ..core import ContractError
from .wire import EnvelopeCodec, MAX_WIRE_BYTES, inspect_envelope


def _quiet_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler()); logger.propagate = False
    return logger


def _uri(uri, tls, allow_insecure_loopback):
    url = urlsplit(uri)
    if (not url.hostname or url.username or url.password or url.query or url.fragment
            or url.scheme not in {'wss','ws'}):
        raise ContractError('invalid mesh WebSocket endpoint')
    if url.scheme == 'ws':
        if not allow_insecure_loopback or url.hostname not in {'127.0.0.1','::1','localhost'}:
            raise ContractError('mesh requires TLS; plaintext is test-only loopback')
        return None
    context = tls or ssl.create_default_context()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise ContractError('mesh TLS must verify server certificates and hostnames')
    return context


def _listener(host, tls, allow_insecure_loopback):
    if tls is None and (not allow_insecure_loopback or host not in {'127.0.0.1','::1','localhost'}):
        raise ContractError('mesh listener requires TLS')


class WebSocketMeshTransport:
    def __init__(self, codec: EnvelopeCodec, *, queue_capacity=128, max_connections=32):
        if type(queue_capacity) is not int or not 1 <= queue_capacity <= 4096 or type(max_connections) is not int or not 1 <= max_connections <= 128:
            raise ContractError('invalid transport limits')
        self.codec, self.node = codec, codec.node
        self.messages = asyncio.Queue(maxsize=queue_capacity)
        self.max_connections = max_connections
        self.rejected = 0
        self._server = None; self._connections = {}; self._readers = set()
        self._logger = _quiet_logger('residual.mesh.transport')

    async def listen(self, host='127.0.0.1', port=0, *, tls=None, allow_insecure_loopback=False):
        from websockets.asyncio.server import serve
        _listener(host,tls,allow_insecure_loopback)
        if self._server is not None:
            raise ContractError('mesh listener already started')
        def handshake(connection, request):
            if request.headers.get('Origin') is not None:
                return connection.respond(HTTPStatus.FORBIDDEN,'browser mesh clients are disabled\n')
            if self._server is not None and len(self._server.connections) >= self.max_connections:
                return connection.respond(HTTPStatus.SERVICE_UNAVAILABLE,'connection limit\n')
        self._server = await serve(lambda connection: self._receive(connection, direct=True),host,port,ssl=tls,process_request=handshake,
            max_size=MAX_WIRE_BYTES,max_queue=8,compression=None,open_timeout=5,close_timeout=1,logger=self._logger)
        return self._server.sockets[0].getsockname()[1]

    async def connect(self, uri, *, peer_id=None, relay_token=None, tls=None, allow_insecure_loopback=False):
        from websockets.asyncio.client import connect
        context = _uri(uri,tls,allow_insecure_loopback)
        if peer_id is not None:
            self.codec._peer(peer_id)
        elif not isinstance(relay_token,str) or len(relay_token) < 32:
            raise ContractError('relay connections require an explicit device credential')
        key = peer_id or '@relay'
        if key in self._connections:
            raise ContractError('mesh connection already exists')
        kwargs = {'ssl':context} if context is not None else {}
        connection = await connect(uri,additional_headers={'Authorization':'Bearer '+relay_token} if relay_token else None,
            max_size=MAX_WIRE_BYTES,max_queue=8,compression=None,open_timeout=5,close_timeout=1,proxy=None,logger=self._logger,**kwargs)
        self._connections[key] = connection
        task = asyncio.create_task(self._receive(connection, expected_sender=peer_id),name='residual-mesh-receive')
        self._readers.add(task)
        def finished(task):
            self._readers.discard(task)
            if self._connections.get(key) is connection:
                self._connections.pop(key,None)
        task.add_done_callback(finished)
        return self

    def accept(self, raw):
        try:
            if self.messages.full():
                raise ContractError('incoming mesh queue full')
            message = self.codec.open(raw)
            if not self.node.receive_message(message):
                raise ContractError('signature, revocation, replay or chat chain rejected')
            self.messages.put_nowait(message)
            return True
        except Exception:
            self.rejected += 1
            return False

    async def _receive(self, connection, direct=False, expected_sender=None):
        from websockets.exceptions import ConnectionClosedOK
        sender = None
        try:
            while True:
                # Unauthenticated inbound sockets cannot occupy a slot indefinitely.
                raw = await asyncio.wait_for(connection.recv(),5) if direct and sender is None else await connection.recv()
                if direct or expected_sender is not None:
                    proposed = inspect_envelope(raw)['header']['sender']
                    if (sender is not None and sender != proposed) or (expected_sender is not None and expected_sender != proposed):
                        raise ContractError('direct connection changed sender')
                if not self.accept(raw):
                    await connection.close(code=1008,reason='mesh message rejected')
                    return
                if direct:
                    sender = proposed
                    self._connections.setdefault(sender, connection)
        except ConnectionClosedOK:
            pass
        except Exception:
            self.rejected += 1
            await connection.close(code=1008,reason="mesh connection ended")
        finally:
            if direct and sender and self._connections.get(sender) is connection:
                self._connections.pop(sender, None)

    async def send(self, message, recipient):
        connection = self._connections.get(recipient) or self._connections.get('@relay')
        if connection is None:
            raise ContractError('peer is not connected')
        # Completion means submitted to the wire, NOT remote acceptance/verification.
        await asyncio.wait_for(connection.send(self.codec.seal(message,recipient)),timeout=5)

    async def close(self):
        if self._server is not None:
            self._server.close(); await self._server.wait_closed(); self._server = None
        connections = tuple(self._connections.values()); self._connections.clear()
        await asyncio.gather(*(c.close() for c in connections),return_exceptions=True)
        readers = tuple(self._readers)
        for task in readers: task.cancel()
        await asyncio.gather(*readers,return_exceptions=True)

    async def cancel(self, timeout_s=5.0):
        await asyncio.wait_for(self.close(),timeout=min(float(timeout_s),5.0))


class OpaqueMeshRelay:
    """Route ciphertext only. Credentials map fixed paths to preprovisioned devices.

    The relay learns routing metadata and can drop/reorder traffic; it has no
    device decryption keys. E2E signatures protect against forged relay output.
    """
    def __init__(self, credentials: dict[str,str]):
        if not credentials or len(credentials) > 128:
            raise ContractError('relay requires 1..128 explicitly provisioned peers')
        for device,token in credentials.items():
            if (not isinstance(device,str) or not 1 <= len(device) <= 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in device)
                    or not isinstance(token,str) or len(token) < 32):
                raise ContractError('invalid relay identity or credential')
        if len(set(credentials.values())) != len(credentials):
            raise ContractError('each relay identity needs a distinct credential')
        self._credentials = dict(credentials); self._clients = {}; self._server = None
        self.rejected = 0
        self._logger = _quiet_logger('residual.mesh.relay')

    async def start(self,host='127.0.0.1',port=0,*,tls=None,allow_insecure_loopback=False):
        from websockets.asyncio.server import serve
        _listener(host,tls,allow_insecure_loopback)
        if self._server is not None: raise ContractError("relay already started")
        def handshake(connection,request):
            device = request.path.removeprefix('/mesh/')
            token = self._credentials.get(device)
            provided = request.headers.get_all('Authorization')
            if (request.path != '/mesh/'+device or request.headers.get('Origin') is not None
                    or token is None or len(provided) != 1 or not secrets.compare_digest(provided[0],'Bearer '+token)):
                return connection.respond(HTTPStatus.UNAUTHORIZED,'relay authentication failed\n')
        self._server = await serve(self._route,host,port,ssl=tls,process_request=handshake,
            max_size=MAX_WIRE_BYTES,max_queue=8,compression=None,open_timeout=5,close_timeout=1,logger=self._logger)
        return self._server.sockets[0].getsockname()[1]

    async def _route(self,connection):
        device = connection.request.path.removeprefix('/mesh/')
        if device in self._clients:
            await connection.close(code=1008,reason='device already connected'); return
        self._clients[device] = connection
        try:
            async for raw in connection:
                envelope = inspect_envelope(raw)
                if envelope['header']['sender'] != device:
                    raise ContractError('relay sender mismatch')
                target = self._clients.get(envelope['header']['recipient'])
                if target is None:
                    await connection.close(code=1013,reason='recipient offline'); return
                await asyncio.wait_for(target.send(raw),5)
        except Exception:
            self.rejected += 1
            await connection.close(code=1008,reason='relay message rejected')
        finally:
            if self._clients.get(device) is connection: self._clients.pop(device,None)

    async def close(self):
        if self._server is not None:
            self._server.close(); await self._server.wait_closed(); self._server=None
