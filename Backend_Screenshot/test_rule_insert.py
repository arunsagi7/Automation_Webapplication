"""
Non-destructive verification that the campaign_rules unique-index fix worked.

It opens a transaction, inserts TWO campaign-only rows (blank line_item_id) —
exactly what used to fail — confirms both succeed, then ROLLS BACK so nothing
is persisted. No real data is added or changed.

    python test_rule_insert.py
"""
from __future__ import annotations
import os, re, sys
from sqlalchemy import create_engine, text

def read_url(d):
    p = os.path.join(d, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if "=" in line and line.split("=", 1)[0].strip().lower() == "crm_database_url":
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("CRM_DATABASE_URL")

def mask(u): return re.sub(r"://([^:/]+):[^@]+@", r"://\1:***@", u)

url = read_url(os.path.dirname(os.path.abspath(__file__)))
print("Target CRM database:", mask(url))
eng = create_engine(url, connect_args={"connect_timeout": 20} if url.startswith("postgres") else {})

conn = eng.connect()
trans = conn.begin()
try:
    ins = text("INSERT INTO campaign_rules (line_item_id, campaign_name, enabled) "
               "VALUES ('', :c, true)")
    conn.execute(ins, {"c": "__FIXTEST_A__"})
    conn.execute(ins, {"c": "__FIXTEST_B__"})   # 2nd blank-line-item row — used to fail here
    print("PASS: inserted two campaign-only rules (blank Line Item ID) with no unique-key error.")
    ok = True
except Exception as e:
    print("FAIL: still rejected ->", str(e).splitlines()[0])
    ok = False
finally:
    trans.rollback()   # undo everything — nothing is persisted
    conn.close()

print("Rolled back — no data was added or changed.")
print("RESULT:", "TEST PASSED — the fix is working." if ok else "TEST FAILED — index still unique.")
sys.exit(0 if ok else 1)
