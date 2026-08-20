"""
Self-contained, idempotent repair for ctr_db.campaign_rules.

WHY
---
`campaign_rules.line_item_id` is declared in the ORM model as a NON-unique
index (`index=True`). The live database still carries a UNIQUE index (or unique
constraint) on that column from an earlier model version. Because the API
stores a blank Line Item ID as "", the second campaign-only rule collides and
the insert fails with:

    duplicate key value violates unique constraint "ix_campaign_rules_line_item_id"

This script removes any UNIQUE index/constraint that covers exactly
(line_item_id) and ensures a plain (non-unique) index remains. It only touches
that index — it reads and writes NO table rows. Safe to run repeatedly.

It reads the CRM database URL straight from Backend_Screenshot/.env, so it does
NOT depend on the app's settings/imports — only SQLAlchemy plus the Postgres
driver the app already uses.

USAGE
-----
    python fix_campaign_rules_index.py
"""
from __future__ import annotations

import logging
import os
import re
import sys

from sqlalchemy import create_engine, inspect, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fix_campaign_rules_index")

TABLE = "campaign_rules"
INDEX = "ix_campaign_rules_line_item_id"
COLUMN = "line_item_id"


def _read_env_url(script_dir: str) -> str:
    """Read crm_database_url from a .env next to this script (fallback: env var)."""
    env_path = os.path.join(script_dir, ".env")
    url = None
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                if key.strip().lower() == "crm_database_url":
                    url = val.strip().strip('"').strip("'")
                    break
    url = url or os.environ.get("CRM_DATABASE_URL")
    if not url:
        raise SystemExit("Could not find crm_database_url in .env or CRM_DATABASE_URL env var.")
    return url


def _mask(url: str) -> str:
    return re.sub(r"://([^:/]+):[^@]+@", r"://\1:***@", url)


def _unique_things_on_column(conn):
    """Return (constraint_names, unique_index_names) that cover exactly (line_item_id) on Postgres."""
    con_rows = conn.execute(text("""
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = :t AND con.contype = 'u'
          AND (
            SELECT array_agg(att.attname ORDER BY att.attnum)
            FROM unnest(con.conkey) AS k
            JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = k
          ) = ARRAY[:c]::name[]
    """), {"t": TABLE, "c": COLUMN}).fetchall()

    idx_rows = conn.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = :t
    """), {"t": TABLE}).fetchall()
    unique_idx = [
        name for (name, ddef) in idx_rows
        if "UNIQUE" in ddef.upper() and re.search(r"\(\s*%s\s*\)" % re.escape(COLUMN), ddef)
    ]
    return [r[0] for r in con_rows], unique_idx


def _report(conn):
    rows = conn.execute(text("""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE tablename = :t ORDER BY indexname
    """), {"t": TABLE}).fetchall()
    log.info("Current indexes on %s:", TABLE)
    for name, ddef in rows:
        flag = "UNIQUE" if "UNIQUE" in ddef.upper() else "non-unique"
        log.info("  - %-40s %s", name, flag)


def upgrade_postgres(engine) -> None:
    with engine.begin() as conn:
        _report(conn)
        constraints, unique_idx = _unique_things_on_column(conn)

        if not constraints and not unique_idx:
            log.info("No UNIQUE index/constraint on (%s). Nothing to remove.", COLUMN)
        for cn in constraints:
            log.info("Dropping UNIQUE constraint %s ...", cn)
            conn.execute(text(f'ALTER TABLE {TABLE} DROP CONSTRAINT "{cn}"'))
        for ix in unique_idx:
            log.info("Dropping UNIQUE index %s ...", ix)
            conn.execute(text(f'DROP INDEX IF EXISTS "{ix}"'))

        # Ensure a plain, non-unique index remains for fast lookups.
        conn.execute(text(f'CREATE INDEX IF NOT EXISTS {INDEX} ON {TABLE} ({COLUMN})'))

        log.info("After repair:")
        _report(conn)


def upgrade_generic(engine) -> None:
    """Fallback for non-Postgres (e.g. local SQLite) using the inspector."""
    insp = inspect(engine)
    unique = None
    for ix in insp.get_indexes(TABLE):
        if ix.get("name") == INDEX:
            unique = bool(ix.get("unique"))
    with engine.begin() as conn:
        if unique:
            log.info("Index %s is UNIQUE; rebuilding non-unique.", INDEX)
            conn.execute(text(f'DROP INDEX IF EXISTS {INDEX}'))
        conn.execute(text(f'CREATE INDEX IF NOT EXISTS {INDEX} ON {TABLE} ({COLUMN})'))


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    url = _read_env_url(script_dir)
    log.info("Target CRM database: %s", _mask(url))
    engine = create_engine(url, connect_args={"connect_timeout": 20} if url.startswith("postgres") else {})
    try:
        if engine.dialect.name == "postgresql":
            upgrade_postgres(engine)
        else:
            upgrade_generic(engine)
    except Exception:  # noqa: BLE001
        log.exception("Repair FAILED")
        return 1
    log.info("SUCCESS: campaign_rules.%s is now non-unique. Campaign-only rules can coexist.", COLUMN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
