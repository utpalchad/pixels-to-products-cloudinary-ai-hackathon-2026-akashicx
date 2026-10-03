from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException


def _is_forbidden_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


async def _validate_public_https_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(
            status_code=502,
            detail="External model URL is invalid.",
        )

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            parsed.hostname,
            parsed.port or 443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=502,
            detail="External model host could not be resolved.",
        ) from exc

    addresses = {item[4][0] for item in infos}
    if not addresses or any(_is_forbidden_ip(address) for address in addresses):
        raise HTTPException(
            status_code=502,
            detail="External model host is not allowed.",
        )


async def fetch_public_binary(
    url: str,
    *,
    max_bytes: int,
    timeout_seconds: float = 180.0,
    max_redirects: int = 3,
) -> bytes:
    """Fetch provider output while blocking SSRF and oversized responses."""

    current = url

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "Pixel-Forge/1.0"},
    ) as client:
        for _ in range(max_redirects + 1):
            await _validate_public_https_url(current)

            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise HTTPException(
                            status_code=502,
                            detail="External model redirect is invalid.",
                        )
                    current = urljoin(current, location)
                    continue

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail="Could not fetch the generated model.",
                    )

                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > max_bytes:
                            raise HTTPException(
                                status_code=413,
                                detail="Generated model exceeds the download limit.",
                            )
                    except ValueError:
                        pass

                chunks: list[bytes] = []
                total = 0

                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail="Generated model exceeds the download limit.",
                        )
                    chunks.append(chunk)

                return b"".join(chunks)

    raise HTTPException(
        status_code=502,
        detail="Too many redirects while fetching the generated model.",
    )
