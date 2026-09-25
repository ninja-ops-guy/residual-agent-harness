"""Authority tests: urllib handlers emulate every target; no socket is opened."""
import io
import json
import socket
from email.message import Message
from urllib import error, request, response

import pytest
from demo.cloud_gateway import server as gateway
from scripts import qualification_active_http_soak as soak

TARGETS = [
    'http://127.0.0.1/private', 'http://10.0.0.1/private',
    'http://172.16.0.1/private', 'http://192.168.1.1/private',
    'http://169.254.169.254/private', 'http://[::1]/private',
    'http://[::ffff:127.0.0.1]/private', 'http://private.invalid/private',
    'file:///tmp/private', 'ftp://private.invalid/private',
    'http://2130706433/private', 'http://0x7f000001/private',
    'http://127.1/private', 'http://%31%32%37.0.0.1/private',
    'http://allowed.invalid@127.0.0.1/private',
]

@pytest.mark.parametrize('target', TARGETS)
def test_request_data_cannot_select_gateway_authority(monkeypatch, target):
    seen = []
    monkeypatch.setattr(gateway, 'FREELLM', 'https://allowed.invalid:8443/base')
    monkeypatch.setattr(gateway, '_reserve', lambda *a: ('fixture', 20))
    def capture(req, **kwargs):
        seen.append(req)
        return response.addinfourl(io.BytesIO(b'{}'), Message(), req.full_url, 200)
    monkeypatch.setattr(request, 'urlopen', capture)
    # Also intercept explicit openers after redirect confinement is installed.
    class Opener:
        open = staticmethod(capture)
    monkeypatch.setattr(request, 'build_opener', lambda *a: Opener())
    payload = {'model':'auto', 'messages':[{'role':'user','content':target}],
               'url':target,'base_url':target,'host':target,'path':target,'port':1}
    code, _ = gateway._route('POST','/v1/chat/completions',
                            {'authorization':'Bearer fixture','host':target},json.dumps(payload).encode())
    assert code == 200
    assert len(seen) == 1
    assert seen[0].full_url == 'https://allowed.invalid:8443/base/v1/chat/completions'
    assert json.loads(seen[0].data)['url'] == target

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("real network forbidden")
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

@pytest.fixture
def transport(monkeypatch):
    seen = []
    state = {'redirect':None}
    class HTTP(request.HTTPHandler):
        def http_open(self, req):
            seen.append(req.full_url)
            headers = Message()
            redirect = state['redirect'] if len(seen) == 1 else None
            if redirect:
                headers['Location'] = redirect
            out = response.addinfourl(io.BytesIO(b'{}'),headers,req.full_url,302 if redirect else 200)
            out.msg = 'Found' if redirect else 'OK'
            return out
    class HTTPS(HTTP, request.HTTPSHandler):
        https_open = HTTP.http_open
    class FTP(request.FTPHandler):
        ftp_open = HTTP.http_open
    build = request.build_opener
    def fixture_build(*handlers):
        return build(request.ProxyHandler({}),HTTP(),HTTPS(),FTP(),*handlers)
    monkeypatch.setattr(request,'_opener',fixture_build())
    monkeypatch.setattr(request,'build_opener',fixture_build)
    return state, seen

@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('helper', ['json','form','soak'])
def test_redirect_cannot_delegate_destination(transport, target, helper):
    state, seen = transport
    state['redirect'] = target
    with pytest.raises(error.HTTPError):
        if helper == 'json': gateway._json('https://allowed.invalid/api')
        elif helper == 'form': gateway._form('https://allowed.invalid/api',{'fixture':'x'})
        else: soak.request('http://127.0.0.1:8893','/api/bootstrap')
    assert len(seen) == 1

@pytest.mark.parametrize('helper', ['json','form','soak'])
def test_successful_response_still_works(transport, helper):
    if helper == 'json': assert gateway._json('https://allowed.invalid/api')[2] == {}
    elif helper == 'form': assert gateway._form('https://allowed.invalid/api',{'fixture':'x'}) == {}
    else: assert soak.request('http://127.0.0.1:8893','/api/bootstrap') == {}
    assert len(transport[1]) == 1
