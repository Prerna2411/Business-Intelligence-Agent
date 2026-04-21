from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.service import BIService


def main() -> None:
    service = BIService()
    documents = service.list_documents()
    if not documents:
        print("No indexed documents found.")
        return

    for doc in documents:
        print(f"{doc['document_id']}  {doc['file_name']}")


if __name__ == "__main__":
    main()
