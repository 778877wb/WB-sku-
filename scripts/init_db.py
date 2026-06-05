"""Initialize the local SQLite database for Phase 1.

Usage from the repository root:
    python scripts/init_db.py

Optional environment variables:
    SQLITE_DB_PATH=data/wb_ops.sqlite3
    DATABASE_URL=sqlite:///data/wb_ops.sqlite3
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wb_ops.db.database import DATABASE_URL, create_db_and_tables  # noqa: E402


def main() -> None:
    """Create all configured database tables."""

    create_db_and_tables()
    print(f"Database initialized: {DATABASE_URL}")


if __name__ == "__main__":
    main()
