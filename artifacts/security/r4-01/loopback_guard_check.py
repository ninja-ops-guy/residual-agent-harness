import socket

for address in [('192.0.2.1',80),('10.0.0.1',80),('169.254.169.254',80)]:
    with socket.socket() as sock:
        try:
            sock.connect(address)
        except PermissionError as exc:
            assert 'qualification blocked' in str(exc)
        else:
            raise AssertionError('external connection was not blocked')
try:
    socket.getaddrinfo('outside.invalid',80)
except PermissionError as exc:
    assert 'qualification blocked' in str(exc)
else:
    raise AssertionError('external DNS was not blocked')
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));sock.listen(1)
    assert sock.getsockname()[0]=='127.0.0.1'
print('PASS: 3 external connects and external DNS blocked; loopback listen allowed')
