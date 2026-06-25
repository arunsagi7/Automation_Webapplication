"""
Restore proper per-user page permissions.
Run: python restore_permissions.py
"""
import psycopg2, json

DB = "postgresql://postgres:Arun%40123%24@localhost:5432/ctr_db"
conn = psycopg2.connect(DB)
cur  = conn.cursor()

updates = [
    (2, ['crm_excel']),      # crm_admin   → CRM Excel only
    (3, ['final_report']),   # report_admin → Final Report only
    (4, ['reach_report']),   # reach_user   → Reach Report only
    (5, ['final_report']),   # report_user  → Final Report only
]

for uid, pages in updates:
    cur.execute(
        "UPDATE users SET allowed_pages = %s WHERE id = %s RETURNING username, allowed_pages",
        (json.dumps(pages), uid)
    )
    row = cur.fetchone()
    if row:
        print(f"✓ {row[0]:20s} → {row[1]}")

conn.commit()
cur.close()
conn.close()
print("\nDone. Re-login required for changes to take effect.")
