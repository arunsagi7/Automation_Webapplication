import psycopg2, bcrypt

DB = "postgresql://postgres:OOpPCEdSamtkDjkOTLxCMCxZlbBBBzzS@reseau.proxy.rlwy.net:22848/railway"
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
for username, password in users:
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute("UPDATE users SET hashed_password=%s WHERE username=%s RETURNING id", (pw_hash, username))
    print(f"  reset: {username}")
conn.commit()
cur.close()
conn.close()
print("Done!")
