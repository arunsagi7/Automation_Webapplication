"""
Reset passwords for all users.
Run: python reset_passwords.py
"""
import psycopg2, bcrypt

DB = "postgresql://postgres:Arun%40123%24@localhost:5432/ctr_db"

users = [
    ("admin",        "Admin@1234"),
    ("crm_admin",    "Crm@1234"),
    ("report_admin", "Report@1234"),
    ("report_user",  "Report@1234"),
    ("reach_user",   "Reach@1234"),
    ("qc_user",      "Qc@1234"),
]

conn = psycopg2.connect(DB)
cur  = conn.cursor()

print("Resetting passwords...\n")
for username, password in users:
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute(
        "UPDATE users SET hashed_password=%s WHERE username=%s RETURNING id",
        (pw_hash, username)
    )
    if cur.fetchone():
        print(f"  ✓ {username:20s} → {password}")
    else:
        print(f"  ✗ {username} not found")

conn.commit()
cur.close()
conn.close()
print("\nDone.")
