"""
Creates scanner_db and ctr_db if they don't exist.
Run once: python create_databases.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to default 'postgres' DB to create other DBs
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="Arun@123$",
    dbname="postgres"
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

for db_name in ["scanner_db", "ctr_db"]:
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
    exists = cur.fetchone()
    if exists:
        print(f"✅ {db_name} already exists")
    else:
        cur.execute(f"CREATE DATABASE {db_name}")
        print(f"✅ {db_name} created successfully")

cur.close()
conn.close()
print("\nDone! Now run: python run.py")
