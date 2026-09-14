"""TLS-only opaque relay launcher. Device credentials come from a private JSON file."""
from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
import os
import ssl
import stat
from ..core import ContractError, strict_json
from .transport import OpaqueMeshRelay


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials',required=True,help='Private device-id to distinct random token mapping')
    parser.add_argument('--tls-cert',required=True)
    parser.add_argument('--tls-key',required=True)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8767)
    args=parser.parse_args(argv)
    try:
        path=Path(args.credentials)
        if path.stat().st_size>32768 or (os.name=='posix' and stat.S_IMODE(path.stat().st_mode)&0o077):
            raise ContractError('relay credential file must be private and bounded')
        credentials=strict_json(path.read_text(encoding='utf-8'))
        if not isinstance(credentials,dict) or not 1<=args.port<=65535:
            raise ContractError('invalid relay configuration')
        relay=OpaqueMeshRelay(credentials)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.minimum_version=ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(args.tls_cert,args.tls_key)
        async def serve():
            await relay.start(args.host,args.port,tls=tls)
            try: await asyncio.Event().wait()
            finally: await relay.close()
        asyncio.run(serve())
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError,ValueError,ImportError):
        parser.exit(1,'mesh relay: invalid credentials, TLS or listener configuration\n')


if __name__=='__main__': raise SystemExit(main())
