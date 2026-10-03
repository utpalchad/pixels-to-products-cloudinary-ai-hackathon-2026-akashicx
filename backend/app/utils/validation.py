from __future__ import annotations

import math
import unicodedata

from fastapi import HTTPException


def clean_user_text(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> str:
    """Normalize user text and reject control characters/oversized input.

    We deliberately validate instead of trying to remove arbitrary "bad"
    substrings. Context-aware output escaping is handled by React/CSP.
    """

    normalized = unicodedata.normalize("NFKC", value or "").strip()

    if len(normalized) > max_length:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} is too long.",
        )

    for char in normalized:
        codepoint = ord(char)
        if codepoint < 32 and char not in {"\n", "\r", "\t"}:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} contains invalid control characters.",
            )

    return normalized


def require_finite_number(value: float, *, field_name: str) -> float:
    if not math.isfinite(value):
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a finite number.",
        )
    return value
