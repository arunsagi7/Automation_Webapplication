"""
Create QC Checker user in ctr_db.
Run: python create_qc_user.py
"""
import psycopg2, json, bcrypt

DB       = "postgresql://postgres:Arun%40123%24@localhost:5432/ctr_db"
USERNAME = "qc_user"
PASSWORD = "Qc@1234"
PAGES    = ["qc_checker"]

pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

conn = psycopg2.connect(DB)
cur  = conn.cursor()

# Check if already exists
cur.execute("SELECT id FROM users WHERE username = %s", (USERNAME,))
if cur.fetchone():
    print(f"User '{USERNAME}' already exists — updating password & pages.")
    cur.execute(
        "UPDATE users SET hashed_password=%s, allowed_pages=%s WHERE username=%s",
        (pw_hash, json.dumps(PAGES), USERNAME)
    )
else:
    cur.execute(
        """INSERT INTO users (username, hashed_password, role, is_active, allowed_pages, created_at)
           VALUES (%s, %s, 'admin', true, %s, NOW())""",
        (USERNAME, pw_hash, json.dumps(PAGES))
    )
    print(f"✓ Created user: {USERNAME}")

conn.commit()
cur.close()
conn.close()

print(f"\nUsername : {USERNAME}")
print(f"Password : {PASSWORD}")
print(f"Access   : QC Checker only")
