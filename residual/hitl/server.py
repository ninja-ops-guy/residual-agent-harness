"""Optional aiohttp operator-review UI; no cookie authentication or implicit resume."""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import ssl
from urllib.parse import urlsplit

from ..core import ContractError, canonical, strict_json
from .auth import OIDCAuthenticator
from .gateway import HITLEscalationGateway


def create_app(gateway: HITLEscalationGateway, authenticator: OIDCAuthenticator, *, origin: str):
    from aiohttp import web
    url = urlsplit(origin)
    if (url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password
            or url.path or url.query or url.fragment
            or (url.scheme != "https" and url.hostname not in {"localhost", "127.0.0.1", "::1"})):
        raise ContractError("review origin must be HTTPS or a loopback HTTP origin")
    if gateway._authenticate is not authenticator:
        raise ContractError("review UI and gateway must use the same authenticator")

    @web.middleware
    async def security(request, handler):
        try:
            if (request.host != url.netloc or request.headers.get("Origin", origin) != origin
                    or request.headers.get("Sec-Fetch-Site") == "cross-site"):
                raise web.HTTPForbidden(text="request origin denied")
            if request.path.startswith("/api/"):
                tokens = request.headers.getall("Authorization", [])
                if len(tokens) != 1 or not tokens[0].startswith("Bearer "):
                    raise web.HTTPUnauthorized(text="bearer credential required")
                token = tokens[0][7:]
                # Crypto and SQLite stay off the event loop. No network in principal().
                principal = await asyncio.to_thread(authenticator.principal, token)
                request["principal"], request["access_token"] = principal, token
            async with asyncio.timeout(10):
                response = await handler(request)
        except web.HTTPException as exc:
            response = web.Response(status=exc.status, text=exc.text)
        except PermissionError:
            response = web.Response(status=401, text="operator authentication failed")
        except (ValueError, TypeError, KeyError, ContractError):
            response = web.Response(status=400, text="invalid review request")
        except TimeoutError:
            response = web.Response(status=503, text="review request timed out; inspect challenge status before retrying")
        except Exception:
            response = web.Response(status=500, text="review request failed")
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "Content-Security-Policy":
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        return response

    app = web.Application(middlewares=[security], client_max_size=32_768)
    static = Path(__file__).with_name("static")

    async def index(request):
        return web.Response(body=(static / "index.html").read_bytes(), content_type="text/html")

    async def asset(request):
        name = request.match_info["name"]
        if name not in {"app.js", "style.css"}:
            raise web.HTTPNotFound()
        return web.Response(body=(static / name).read_bytes(),
                            content_type="text/javascript" if name.endswith(".js") else "text/css")

    async def listing(request):
        page = await asyncio.to_thread(gateway.list_challenges, tuple(request["principal"].roles),
                                       after=request.query.get("after", ""))
        page["operator_roles"] = sorted(request["principal"].roles)
        return web.Response(text=canonical(page), content_type="application/json")

    async def decision(request):
        if request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType(text="JSON required")
        data = strict_json(await request.text())
        if not isinstance(data, dict) or set(data) != {"decision", "challenge_signature", "role"}:
            raise ContractError("invalid decision")
        cid, principal = request.match_info["challenge_id"], request["principal"]
        if data["role"] not in principal.roles:
            raise web.HTTPForbidden(text="role denied")
        response = canonical({"access_token": request["access_token"], "challenge_id": cid,
            "challenge_signature": data["challenge_signature"], "decision": data["decision"]})
        consumed, status = await asyncio.to_thread(gateway.submit_decision, cid, response,
            data["role"], tuple(principal.roles), decision=data["decision"])
        return web.json_response({"consumed": consumed, "status": status.value,
                                  "execution_resumed": False}, status=200 if consumed else 409)

    app.router.add_get("/", index)
    app.router.add_get("/assets/{name}", asset)
    app.router.add_get("/api/challenges", listing)
    app.router.add_post("/api/challenges/{challenge_id}/decision", decision)
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description="Residual authenticated operator review")
    parser.add_argument("--data", required=True, help="Same challenge directory as the host HITL module")
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--audience", required=True)
    parser.add_argument("--jwks", required=True, help="Host-verified local JWKS; reload on rotation")
    parser.add_argument("--role", action="append", dest="roles", required=True)
    parser.add_argument("--role-claim", default="roles")
    parser.add_argument("--scope", default="residual:review")
    parser.add_argument("--origin", default="http://127.0.0.1:8766")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args(argv)
    try:
        import base64
        from aiohttp import web
        key = base64.b64decode(os.environ["RESIDUAL_HITL_SIGNING_KEY"], validate=True)
        jwks_path = Path(args.jwks)
        if jwks_path.stat().st_size > 65536:
            raise ContractError("JWKS too large")
        auth = OIDCAuthenticator(issuer=args.issuer, audience=args.audience,
            jwks=strict_json(jwks_path.read_text()), allowed_roles=tuple(args.roles),
            role_claim=args.role_claim, required_scope=args.scope)
        gateway = HITLEscalationGateway(key, args.data, authenticate=auth)
        tls = None
        if args.tls_cert and args.tls_key:
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.minimum_version = ssl.TLSVersion.TLSv1_2
            tls.load_cert_chain(args.tls_cert, args.tls_key)
        if args.host not in {"127.0.0.1", "::1", "localhost"} and tls is None:
            raise ContractError("non-loopback review listeners require TLS")
        if bool(tls) != (urlsplit(args.origin).scheme == "https"):
            raise ContractError("origin scheme must match listener TLS")
        web.run_app(create_app(gateway, auth, origin=args.origin), host=args.host,
                    port=args.port, ssl_context=tls, access_log=None, print=None)
        return 0
    except (ValueError, KeyError, OSError, ImportError, ContractError):
        parser.exit(1, "review server: invalid identity, key or listener configuration\n")


if __name__ == "__main__":
    raise SystemExit(main())
