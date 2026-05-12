"""Fix alembic_version table — remove old head, keep only n4i5j6k7l8m9."""
import os
import psycopg2

url = os.environ["DATABASE_PUBLIC_URL"]
conn = psycopg2.connect(url)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT version_num FROM alembic_version")
rows = cur.fetchall()
print("Current versions:", rows)

cur.execute("DELETE FROM alembic_version WHERE version_num = 'm3h4i5j6k7l8'")
cur.execute("INSERT INTO alembic_version (version_num) VALUES ('n4i5j6k7l8m9') ON CONFLICT DO NOTHING")

cur.execute("SELECT version_num FROM alembic_version")
rows = cur.fetchall()
print("Fixed versions:", rows)

cur.close()
conn.close()
