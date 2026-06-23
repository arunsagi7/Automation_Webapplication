"""
Quick DB connection check — run from Backend_Screenshot/ folder.
  python check_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from core.config import get_settings

settings = get_settings()

print("=" * 55)
print("DB Connection Check")
print("=" * 55)

# ── scanner_db ────────────────────────────────────────────
print("\n[1] scanner_db")
print(f"    URL : {settings.database_url}")
try:
    from database.db import engine
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), version()"))
        db_name, version = result.fetchone()
        print(f"    ✅ Connected  → db: {db_name}")
        print(f"    PG version   : {version.split(',')[0]}")

        tables = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )).fetchall()
        print(f"    Tables       : {[t[0] for t in tables]}")
except Exception as e:
    print(f"    ❌ FAILED: {e}")

# ── ctr_db ────────────────────────────────────────────────
print("\n[2] ctr_db")
print(f"    URL : {settings.crm_database_url}")
try:
    from database.crm_db import crm_engine
    with crm_engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), version()"))
        db_name, version = result.fetchone()
        print(f"    ✅ Connected  → db: {db_name}")
        print(f"    PG version   : {version.split(',')[0]}")

        tables = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )).fetchall()
        print(f"    Tables       : {[t[0] for t in tables]}")

        # Check users table
        if any(t[0] == 'users' for t in tables):
            users = conn.execute(text(
                "SELECT id, username, role, is_active, created_at FROM users ORDER BY id"
            )).fetchall()
            print(f"\n    users table ({len(users)} rows):")
            for u in users:
                print(f"      id={u[0]}  username={u[1]}  role={u[2]}  active={u[3]}  created_at={u[4]}")
        else:
            print("    ⚠️  users table NOT found in ctr_db")
except Exception as e:
    print(f"    ❌ FAILED: {e}")

print("\n" + "=" * 55)
