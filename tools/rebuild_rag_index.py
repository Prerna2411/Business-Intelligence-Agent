from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.service import BIService


def main() -> None:
    service = BIService()
    uploads_dir = Path(service.settings.uploads_path)
    if not uploads_dir.exists():
        print("No uploads directory found.")
        return

    files = [(path.name, path.read_bytes()) for path in uploads_dir.iterdir() if path.is_file()]
    if not files:
        print("No files available to re-index.")
        return

    for item in service.ingest_documents(files):
        print(item["message"])


if __name__ == "__main__":
    main()
