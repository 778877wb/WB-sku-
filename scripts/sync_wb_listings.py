"""Synchronize WB product cards into local listing records.

Usage:
    python scripts/sync_wb_listings.py

Before running, copy ``config/wb_tokens.example.json`` to
``config/wb_tokens.json`` and configure one or more store tokens. Tokens may be
stored in environment variables referenced by ``api_token_env``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wb_ops.db.database import get_db  # noqa: E402
from wb_ops.integrations.wb.config import load_wb_config  # noqa: E402
from wb_ops.services.wb_listing_sync_service import WbListingSyncService  # noqa: E402


def main() -> None:
    """Run listing synchronization for all enabled stores."""

    config = load_wb_config()
    with get_db() as db:
        result = WbListingSyncService(db=db, config=config).sync_all_stores()

    for store in result.stores:
        print(
            f"{store.shop_name}: fetched={store.fetched_cards}, matched={store.matched_cards}, "
            f"created={store.created_listings}, updated={store.updated_listings}, "
            f"delisted={store.delisted_listings}, skipped={store.skipped_cards}"
        )
    print(
        f"TOTAL: fetched={result.fetched_cards}, matched={result.matched_cards}, "
        f"created={result.created_listings}, updated={result.updated_listings}"
    )


if __name__ == "__main__":
    main()
