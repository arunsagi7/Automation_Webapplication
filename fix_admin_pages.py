"""
Fix admin user allowed_pages — add all pages.
Run: python fix_admin_pages.py
"""
import psycopg2, json

DB  = "postgresql://postgres:Arun%40123%24@localhost:5432/ctr_db"
ALL = ["scanner", "crm_excel", "ppt_store", "final_report", "reach_report"]

conn = psycopg2.connect(DB)
cur  = conn.cursor()

# Show current state
cur.execute("SELECT id, username, role, allowed_pages FROM users;")
rows = cur.fetchall()
print("\nCurrent users:")
for r in rows:
    print(f"  id={r[0]}  username={r[1]}  role={r[2]}  allowed_pages={r[3]}")

# Fix: give every non-super_admin user all pages
updated = []
for row in rows:
    uid, uname, role, pages = row
    if role == 'super_admin':
        continue
    existing = pages if isinstance(pages, list) else (json.loads(pages) if pages else [])
    if sorted(existing) != sorted(ALL):
        cur.execute(
            "UPDATE users SET allowed_pages = %s WHERE id = %s RETURNING username, allowed_pages;",
            (json.dumps(ALL), uid)
        )
        updated.append(cur.fetchone())

conn.commit()

if updated:
    for u in updated:
        print(f"\n✓ Updated: {u[0]} → {u[1]}")
else:
    print("\nAll non-super_admin users already have full access.")

cur.close()
conn.close()
print("\nDone.")
