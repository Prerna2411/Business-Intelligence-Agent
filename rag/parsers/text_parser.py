from __future__ import annotations


def parse_text(file_bytes: bytes) -> list[dict]:
    return [{"page_number": 1, "text": file_bytes.decode("utf-8", errors="ignore")}]
