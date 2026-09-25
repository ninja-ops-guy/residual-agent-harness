"""Qualification guard inherited by Python children; allow numeric loopback only."""
import ipaddress
import socket
import sys


def loopback(host):
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_loopback


def network_guard(event, args):
    if event in {'socket.connect', 'socket.bind'}:
        sock, address = args
        if sock.family not in {socket.AF_INET, socket.AF_INET6}:
            raise PermissionError('qualification permits only IP loopback sockets')
        if not loopback(address[0]):
            raise PermissionError('qualification blocked non-loopback address')
    elif event == 'socket.getaddrinfo':
        if not loopback(args[0]):
            raise PermissionError('qualification blocked external name resolution')
    elif event in {'socket.gethostbyname', 'socket.gethostbyaddr'}:
        if not loopback(args[0]):
            raise PermissionError('qualification blocked external name resolution')
    elif event == 'socket.sendto':
        if not loopback(args[-1][0]):
            raise PermissionError('qualification blocked non-loopback datagram')

sys.addaudithook(network_guard)
