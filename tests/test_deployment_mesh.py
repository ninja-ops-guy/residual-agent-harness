import asyncio
from dataclasses import asdict
import json
import multiprocessing
import ssl
import tempfile
import time
import unittest
from types import SimpleNamespace
from pathlib import Path

from residual.core import ContractError, canonical
from residual.mesh.node import MeshNode, MeshIdentity, MeshMessageKind
from residual.mesh.discovery import announcement, parse_announcement

try:
    import websockets
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from residual.mesh.wire import DeviceKeys, EnvelopeCodec, PeerKeys
    from residual.mesh.transport import WebSocketMeshTransport, OpaqueMeshRelay
    HAS_MESH = True
except ImportError:
    HAS_MESH = False


def node(name):
    keys = DeviceKeys.generate()
    identity = MeshIdentity(name,name,keys.public.signing_key,('chat',),'',time.time_ns())
    return MeshNode(identity,keys.sign,keys.verify), keys


def pair():
    a,ka=node('a'); b,kb=node('b')
    a.connect_peer(b.identity); b.connect_peer(a.identity)
    ca=EnvelopeCodec(a,ka,{'b':kb.public},room='room'); cb=EnvelopeCodec(b,kb,{'a':ka.public},room='room')
    return a,b,ca,cb


def certificate(directory):
    import datetime, ipaddress
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject=x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME,'localhost')])
    now=datetime.datetime.now(datetime.timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1))
          .not_valid_after(now+datetime.timedelta(hours=1))
          .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1')),x509.DNSName('localhost')]),critical=False)
          .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True).sign(key,hashes.SHA256()))
    certfile=Path(directory)/'test-cert.pem'; keyfile=Path(directory)/'test-key.pem'
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    keyfile.chmod(0o600)
    return str(certfile),str(keyfile)


def peer_process(pipe,peer_identity,peer_public,certfile,keyfile):
    async def run():
        b,kb=node('b'); b.connect_peer(MeshIdentity(**peer_identity))
        codec=EnvelopeCodec(b,kb,{'a':PeerKeys(**peer_public)},room='room')
        transport=WebSocketMeshTransport(codec)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(certfile,keyfile)
        port=await transport.listen(tls=tls)
        pipe.send((port,asdict(b.identity),asdict(kb.public)))
        try:
            incoming=await asyncio.wait_for(transport.messages.get(),10)
            await transport.send(b.send_message(MeshMessageKind.CHAT,content='reply from second process'),'a')
            pipe.send(incoming.content)
            await asyncio.sleep(.1)
        finally: await transport.close()
    try: asyncio.run(run())
    finally: pipe.close()


@unittest.skipUnless(HAS_MESH,'install mesh extra')
class EnvelopeTests(unittest.TestCase):
    def test_e2e_tampering_scope_and_replay(self):
        a,b,ca,cb=pair(); message=a.send_message(MeshMessageKind.CHAT,content='private payload invisible to relay')
        wire=ca.seal(message,'b')
        self.assertNotIn('private payload invisible to relay',wire)
        self.assertTrue(b.receive_message(cb.open(wire)))
        self.assertFalse(b.receive_message(cb.open(wire)))
        for field,value in [('recipient','other'),('sender','other'),('room','other'),('issued_at',0)]:
            bad=json.loads(wire); bad['header'][field]=value
            with self.subTest(field=field),self.assertRaises(ContractError): cb.open(canonical(bad))
        bad=json.loads(wire); bad['ciphertext']='AAAA'+bad['ciphertext'][4:]
        with self.assertRaises(ContractError): cb.open(canonical(bad))
        b.revoke_device('a','ignored')
        with self.assertRaises(ContractError): cb.open(wire)
        with self.assertRaises(ContractError): cb.open('x'*65537)

    def test_discovery_is_advisory_bounded_metadata(self):
        a,keys=node('a'); props=announcement(a.identity)
        info=SimpleNamespace(properties=props,parsed_addresses=lambda:['192.168.1.2'],port=8767)
        parsed=parse_announcement(info)
        self.assertEqual(parsed.capabilities,('chat',)); self.assertEqual(a.peers,{})
        props[b'private_file']=b'secret'
        with self.assertRaises(ContractError): parse_announcement(info)


@unittest.skipUnless(HAS_MESH,'install mesh extra')
class WireTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_two_process_tls_roundtrip(self):
        a,ka=node('a')
        with tempfile.TemporaryDirectory() as directory:
            cert,key=certificate(directory)
            parent,child=multiprocessing.get_context('spawn').Pipe()
            process=multiprocessing.get_context('spawn').Process(target=peer_process,args=(child,asdict(a.identity),asdict(ka.public),cert,key))
            process.start(); child.close()
            transport=None
            try:
                self.assertTrue(await asyncio.to_thread(parent.poll,10),'peer did not start')
                port,identity,public=parent.recv(); a.connect_peer(MeshIdentity(**identity))
                codec=EnvelopeCodec(a,ka,{'b':PeerKeys(**public)},room='room')
                transport=WebSocketMeshTransport(codec)
                tls=ssl.create_default_context(cafile=cert)
                await transport.connect(f'wss://127.0.0.1:{port}',peer_id='b',tls=tls)
                await transport.send(a.send_message(MeshMessageKind.CHAT,content='hello across processes'),'b')
                reply=await asyncio.wait_for(transport.messages.get(),10)
                self.assertEqual(reply.content,'reply from second process')
                self.assertTrue(a.chat.verify())
                self.assertTrue(await asyncio.to_thread(parent.poll,5)); self.assertEqual(parent.recv(),'hello across processes')
            finally:
                if transport: await transport.close()
                await asyncio.to_thread(process.join,5)
                if process.is_alive(): process.terminate(); process.join(2)
                parent.close()
            self.assertEqual(process.exitcode,0)

    async def test_opaque_relay_real_websockets(self):
        a,b,ca,cb=pair(); ta,tb=WebSocketMeshTransport(ca),WebSocketMeshTransport(cb)
        relay=OpaqueMeshRelay({'a':'a'*32,'b':'b'*32})
        port=await relay.start(allow_insecure_loopback=True)
        try:
            await ta.connect(f'ws://127.0.0.1:{port}/mesh/a',relay_token='a'*32,allow_insecure_loopback=True)
            await tb.connect(f'ws://127.0.0.1:{port}/mesh/b',relay_token='b'*32,allow_insecure_loopback=True)
            await ta.send(a.send_message(MeshMessageKind.CHAT,content='relay exchange'),'b')
            self.assertEqual((await asyncio.wait_for(tb.messages.get(),5)).content,'relay exchange')
            await tb.send(b.send_message(MeshMessageKind.CHAT,content='response'),'a')
            self.assertEqual((await asyncio.wait_for(ta.messages.get(),5)).content,'response')
            self.assertFalse(hasattr(relay,'keys'))
            with self.assertRaises(Exception):
                await WebSocketMeshTransport(ca).connect(f'ws://127.0.0.1:{port}/mesh/a',relay_token='wrong'*8,allow_insecure_loopback=True)
        finally:
            await ta.close(); await tb.close(); await relay.close()

    async def test_plaintext_and_unverified_tls_refused(self):
        a,b,ca,cb=pair(); transport=WebSocketMeshTransport(ca)
        with self.assertRaises(ContractError): await transport.connect('ws://127.0.0.1:8767',peer_id='b')
        with self.assertRaises(ContractError): await transport.connect('ws://192.168.1.2:8767',peer_id='b',allow_insecure_loopback=True)
        with self.assertRaises(ContractError): await transport.listen(host='0.0.0.0',allow_insecure_loopback=True)
        tls=ssl._create_unverified_context()
        with self.assertRaises(ContractError): await transport.connect('wss://localhost:8767',peer_id='b',tls=tls)
