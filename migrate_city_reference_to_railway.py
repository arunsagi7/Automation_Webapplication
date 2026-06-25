"""
migrate_city_reference_to_railway.py
=====================================
Copies city_reference table from local ctr_db → Railway PostgreSQL DB.
Run: python migrate_city_reference_to_railway.py
"""
import psycopg2
from psycopg2.extras import execute_values

LOCAL_URL   = "postgresql://postgres:Arun%40123%24@localhost:5432/ctr_db"
RAILWAY_URL = "postgresql://postgres:imGiWkhxTvTjtEGvcgyaPUKpJVrrDWjP@reseau.proxy.rlwy.net:56754/railway"

print("Connecting to local ctr_db...")
local_conn = psycopg2.connect(LOCAL_URL)
local_cur  = local_conn.cursor()

print("Connecting to Railway DB...")
rail_conn  = psycopg2.connect(RAILWAY_URL)
rail_cur   = rail_conn.cursor()

# Create table in Railway if not exists
print("\nCreating city_reference table in Railway...")
rail_cur.execute("""
CREATE TABLE IF NOT EXISTS city_reference (
    id                    SERIAL PRIMARY KEY,
    sheet_name            VARCHAR(150)  NOT NULL,
    row_number            INTEGER,
    city_name             VARCHAR(255)  NOT NULL,
    country               VARCHAR(10),
    state_region          VARCHAR(150),
    potential_impressions BIGINT,
    unique_cookies        BIGINT
);
CREATE INDEX IF NOT EXISTS idx_city_ref_sheet ON city_reference (sheet_name);
CREATE INDEX IF NOT EXISTS idx_city_ref_name  ON city_reference (LOWER(city_name));
""")
rail_conn.commit()
print("  ✅ Table created")

# Fetch all rows from local
print("\nFetching city_reference from local ctr_db...")
local_cur.execute("""
    SELECT sheet_name, row_number, city_name, country, state_region,
           potential_impressions, unique_cookies
    FROM city_reference
    ORDER BY id
""")
rows = local_cur.fetchall()
print(f"  Found {len(rows)} rows")

# Check how many already in Railway
rail_cur.execute("SELECT COUNT(*) FROM city_reference")
existing = rail_cur.fetchone()[0]
print(f"  Railway already has {existing} rows")

if existing > 0:
    print("  Truncating existing data...")
    rail_cur.execute("TRUNCATE TABLE city_reference RESTART IDENTITY;")
    rail_conn.commit()

# Insert in batches
print("\nInserting into Railway...")
execute_values(
    rail_cur,
    """
    INSERT INTO city_reference
        (sheet_name, row_number, city_name, country, state_region,
         potential_impressions, unique_cookies)
    VALUES %s
    """,
    rows,
    page_size=500
)
rail_conn.commit()

# Summary
rail_cur.execute("SELECT sheet_name, COUNT(*) FROM city_reference GROUP BY sheet_name ORDER BY sheet_name")
sheets = rail_cur.fetchall()
print(f"\n  ✅ {len(rows)} rows inserted across {len(sheets)} sheets:")
for sheet, cnt in sheets:
    print(f"     {sheet}: {cnt}")

local_cur.close(); local_conn.close()
rail_cur.close();  rail_conn.close()
print("\nDone!")
