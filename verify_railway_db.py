"""
Verify Railway DB migration — check tables and user data.
Run: python verify_railway_db.py
"""
import psycopg2

CTR_DB     = "postgresql://postgres:OOpPCEdSamtkDjkOTLxCMCxZlbBBBzzS@reseau.proxy.rlwy.net:22848/railway"
SCANNER_DB = "postgresql://postgres:DBDmXSVjWhqlXYSkMhawhaEltmXhJZrl@zephyr.proxy.rlwy.net:58979/railway"

print("=" * 50)
print("Checking ctr_db (users, reports)...")
conn = psycopg2.connect(CTR_DB)
cur  = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [r[0] for r in cur.fetchall()]
print(f"  Tables: {tables}")
cur.execute("SELECT id, username, role, allowed_pages FROM users")
users = cur.fetchall()
print(f"  Users ({len(users)}):")
for u in users:
    print(f"    id={u[0]}  {u[1]:20s}  {u[2]:12s}  {u[3]}")
cur.close()
conn.close()

print()
print("=" * 50)
print("Checking scanner_db...")
conn = psycopg2.connect(SCANNER_DB)
cur  = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [r[0] for r in cur.fetchall()]
print(f"  Tables: {tables}")
cur.close()
conn.close()

print()
print("✅ Railway DB verification complete.")
