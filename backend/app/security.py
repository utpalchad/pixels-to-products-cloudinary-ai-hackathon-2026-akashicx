from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import Settings

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class RateRule:
    limit: int
    window_seconds: int


class InMemoryRateLimiter:
    """Small single-instance limiter for the current Render deployment.

    This protects expensive endpoints from basic abuse. If the service is
    scaled horizontally, replace this with a shared Redis-backed limiter.
    """

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, bucket: str, client_ip: str, rule: RateRule) -> tuple[bool, int]:
        now = time.monotonic()
        key = (bucket, client_ip)

        async with self._lock:
            queue = self._hits.setdefault(key, deque())
            cutoff = now - rule.window_seconds

            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= rule.limit:
                retry_after = max(1, int(rule.window_seconds - (now - queue[0])))
                return False, retry_after

            queue.append(now)

            # Bound memory if an attacker rotates IP addresses.
            if len(self._hits) > 10_000:
                for stale_key in list(self._hits.keys())[:2_000]:
                    if stale_key != key:
                        self._hits.pop(stale_key, None)

            return True, 0


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    candidates = [part.strip() for part in forwarded.split(",") if part.strip()]

    # Render appends the connecting client. Prefer the last syntactically valid
    # address so an attacker-supplied first X-Forwarded-For value cannot bypass
    # a per-IP limiter.
    for candidate in reversed(candidates):
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue

    if request.client:
        try:
            return str(ipaddress.ip_address(request.client.host))
        except ValueError:
            return request.client.host

    return "unknown"


def _rate_rule(request: Request) -> tuple[str, RateRule] | None:
    path = request.url.path
    method = request.method.upper()

    if method == "POST" and path == "/api/v1/ai3d/generate":
        return "ai3d-generate", RateRule(limit=6, window_seconds=600)

    if method == "POST" and path == "/api/v1/analysis/image":
        return "image-analysis", RateRule(limit=24, window_seconds=600)

    if method == "POST" and path == "/api/v1/convert/local":
        return "local-convert", RateRule(limit=20, window_seconds=600)

    if method == "GET" and path.startswith("/api/v1/jobs/"):
        if path.endswith("/download") or path.endswith("/download-stl"):
            return "job-download", RateRule(limit=60, window_seconds=600)
        return "job-poll", RateRule(limit=240, window_seconds=600)

    if method == "GET" and path.startswith("/api/v1/download/"):
        return "local-download", RateRule(limit=60, window_seconds=600)

    return None


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.allowed_origins = {
            origin.rstrip("/").lower()
            for origin in settings.cors_origin_list
        }
        self.rate_limiter = InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id

        method = request.method.upper()
        path = request.url.path

        # Browser-side CSRF/cross-site abuse protection. Pixel Forge currently
        # has no cookie-authenticated state, but these checks also prevent
        # malicious sites from silently triggering expensive POST operations.
        if method not in SAFE_METHODS and path.startswith("/api/"):
            origin = request.headers.get("origin")
            fetch_site = request.headers.get("sec-fetch-site", "").lower()

            if origin and origin.rstrip("/").lower() not in self.allowed_origins:
                return self._blocked(
                    403,
                    "Cross-origin request blocked.",
                    request_id,
                )

            if fetch_site == "cross-site":
                return self._blocked(
                    403,
                    "Cross-site request blocked.",
                    request_id,
                )

        rule = _rate_rule(request)
        if rule is not None:
            bucket, limit = rule
            allowed, retry_after = await self.rate_limiter.allow(
                bucket,
                _client_ip(request),
                limit,
            )
            if not allowed:
                response = self._blocked(
                    429,
                    "Too many requests. Please retry later.",
                    request_id,
                )
                response.headers["Retry-After"] = str(retry_after)
                return response

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error request_id=%s", request_id)
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "request_id": request_id,
                },
            )

        self._apply_security_headers(response, request_id)
        return response

    def _blocked(self, status_code: int, detail: str, request_id: str) -> JSONResponse:
        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail, "request_id": request_id},
        )
        self._apply_security_headers(response, request_id)
        return response

    def _apply_security_headers(self, response: Response, request_id: str) -> None:
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )

        if self.settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        if not response.headers.get("Cache-Control"):
            response.headers["Cache-Control"] = "no-store"
