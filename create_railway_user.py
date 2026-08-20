import bcrypt, psycopg2, json, os, sys

# Read the DB connection string from the environment — never hardcode it.
# e.g. (PowerShell):  $env:CRM_DATABASE_URL = "postgresql://..."   then run this script.
RAILWAY_URL = os.getenv("CRM_DATABASE_URL") or os.getenv("DATABASE_URL")
if not RAILWAY_URL:
    sys.exit("Set CRM_DATABASE_URL (or DATABASE_URL) in your environment before running this script.")

users_to_create = [
    ("report_user", "Pass@123", "admin", ["final_report"]),
]

conn = psycopg2.connect(RAILWAY_URL)
cur  = conn.cursor()

for username, password, role, pages in users_to_create:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute("""
        INSERT INTO users (username, hashed_password, role, allowed_pages, is_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
    """, (username, hashed, role, json.dumps(pages), True))
    print(f"  ✅ {username} created (role={role}, pages={pages})")

conn.commit()
cur.close()
conn.close()
print("Done!")
