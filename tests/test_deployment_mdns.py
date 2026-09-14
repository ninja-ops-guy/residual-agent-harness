"""Opt-in real multicast test; CI selects an explicit loopback interface."""
import asyncio
import os
import time
import unittest

from residual.mesh import MeshIdentity
from residual.mesh.discovery import MDNSDiscovery

try:
    import zeroconf
    HAS_ZEROCONF=True
except ImportError:
    HAS_ZEROCONF=False


@unittest.skipUnless(HAS_ZEROCONF and os.environ.get('RESIDUAL_MDNS_TEST_INTERFACE'),
                     'install mesh extra and set RESIDUAL_MDNS_TEST_INTERFACE for multicast test')
class MulticastTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_mdns_discovery_and_cleanup(self):
        interface=os.environ['RESIDUAL_MDNS_TEST_INTERFACE']
        suffix=str(time.time_ns()); observed=asyncio.Event(); candidates=[]
        first=MeshIdentity('first-'+suffix,'first','a'*64,('chat',),'',time.time_ns())
        second=MeshIdentity('second-'+suffix,'second','b'*64,('chat',),'',time.time_ns())
        def seen(peer):
            candidates.append(peer)
            if peer.device_id==second.device_id: observed.set()
        a=MDNSDiscovery(first,address=interface,port=18767,on_candidate=seen)
        b=MDNSDiscovery(second,address=interface,port=18768,on_candidate=lambda p:None)
        try:
            await a.start(); await b.start()
            await asyncio.wait_for(observed.wait(),10)
            self.assertTrue(any(p.port==18768 and p.capabilities==('chat',) for p in candidates))
        finally:
            await b.close(); await a.close()
        self.assertFalse(a._tasks); self.assertIsNone(a._zc)
