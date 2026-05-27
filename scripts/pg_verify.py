import os
import psycopg2

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise SystemExit('DATABASE_URL not set')

conn = psycopg2.connect(db_url)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
tables = [r[0] for r in cur.fetchall()]
print('tables:', tables)

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='payments_payment' ORDER BY ordinal_position;")
cols = cur.fetchall()
print('payments_payment columns:')
for c in cols:
    print(' -', c[0], c[1])

cur.close()
conn.close()
