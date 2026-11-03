"""Disposable HTTP checks: exact assets only; no added authority endpoint."""
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from residual.station.server import Server, STATIC
from residual.station.service import Station

class PreparationAssetsTests(unittest.TestCase):
    def test_assets_are_exact_bytes_and_do_not_change_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            station = Station(directory)
            before = station.store.settings()
            server = Server(('127.0.0.1', 0), station)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            origin = f'http://127.0.0.1:{server.server_port}'
            try:
                for name, mime in [('agent-preparation-model.mjs','text/javascript'),
                                   ('agent-preparation-view.mjs','text/javascript'),
                                   ('agent-preparation.css','text/css')]:
                    with urllib.request.urlopen(origin+'/'+name) as response:
                        self.assertEqual(response.headers.get_content_type(), mime)
                        self.assertEqual(response.read(), (STATIC/name).read_bytes())
                for route in ['/agent-preparation.json','/agent-preparation/','/tests/fixtures/agent-preparation.html']:
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(origin+route)
                    self.assertEqual(error.exception.code,404)
                self.assertEqual(before,station.store.settings())
            finally:
                server.shutdown(); server.server_close(); thread.join()
