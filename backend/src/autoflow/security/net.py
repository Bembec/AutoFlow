"""
Outbound request safety (server-side request forgery protection).

Workflows may call any public API, but never addresses inside our own
network: loopback, private ranges, link-local (including cloud metadata
at 169.254.169.254), multicast or reserved addresses. Redirects are not
followed automatically, so a public URL cannot bounce a request inside.
"""

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURL(Exception):
    """The URL points somewhere workflows are not allowed to reach."""


def _blocked(ip):
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def check_public_url(url):
    """Raise UnsafeURL unless every address the host resolves to is public."""

    parts = urlsplit(url)

    if parts.scheme not in ("http", "https"):
        raise UnsafeURL("Only http and https URLs are allowed.")

    if not parts.hostname:
        raise UnsafeURL("The URL has no host.")

    if parts.username or parts.password:
        raise UnsafeURL("Credentials inside URLs are not allowed; use a connection.")

    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise UnsafeURL(f"The host {parts.hostname} cannot be resolved.") from error

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0].split("%")[0])

        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        if _blocked(ip):
            raise UnsafeURL(f"The host {parts.hostname} points to a non-public address.")

    return url
