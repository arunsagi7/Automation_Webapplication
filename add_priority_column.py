"""
Add 'priority' column to app_url_reference in Railway ctr_db.
Run: python add_priority_column.py
"""
import psycopg2

DB = "postgresql://postgres:OOpPCEdSamtkDjkOTLxCMCxZlbBBBzzS@reseau.proxy.rlwy.net:22848/railway"

conn = psycopg2.connect(DB)
cur  = conn.cursor()

cur.execute("""
    ALTER TABLE app_url_reference
    ADD COLUMN IF NOT EXISTS priority VARCHAR DEFAULT 'regular'
""")
conn.commit()

# Verify
cur.execute("""
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_name = 'app_url_reference'
    ORDER BY ordinal_position
""")
print("app_url_reference columns:")
for row in cur.fetchall():
    print(f"  {row[0]:20s}  {row[1]:15s}  default={row[2]}")

cur.close()
conn.close()
print("\n✅ Done. Existing rows default to 'regular'. Re-upload Excel to set correct priorities.")
