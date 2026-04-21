from __future__ import annotations

from functools import lru_cache

from services.service import BIService


@lru_cache(maxsize=1)
def get_bi_service() -> BIService:
    return BIService()
