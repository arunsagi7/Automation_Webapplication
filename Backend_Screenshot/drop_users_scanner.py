"""
Drops the users table from scanner_db (moved to ctr_db).
Run once: python drop_users_scanner.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database.db import engine

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    conn.commit()
    print("✅ users table dropped from scanner_db")

    tables = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )).fetchall()
    print(f"   Remaining tables: {[t[0] for t in tables]}")
