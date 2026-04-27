CREATE INDEX CONCURRENTLY idx_raw_audit_detail_id 
ON redservice.t_raw_audit (detail_id);


ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET checkpoint_timeout = '5min';
ALTER SYSTEM SET work_mem = '128MB';
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
SELECT pg_reload_conf();

import duckdb

con = duckdb.connect()

GOLDEN = "path/to/golden.snappy.parquet"
MINE = "path/to/mine.snappy.parquet"

for label, path in [("GOLDEN", GOLDEN), ("MINE", MINE)]:
    print(f"\n=== {label} ===")
    
    # Row count
    count = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
    print(f"Rows: {count}")
    
    # Avg flags per row
    avg_flags = con.execute(f"""
        SELECT AVG(LENGTH(Flags)) FROM '{path}'
    """).fetchone()[0]
    print(f"Avg flags per row: {avg_flags:.2f}")
    
    # Top 5 flag names
    top = con.execute(f"""
        SELECT flag.Name, COUNT(*) 
        FROM '{path}', UNNEST(Flags) AS t(flag)
        WHERE flag.Name IS NOT NULL
        GROUP BY flag.Name 
        ORDER BY COUNT(*) DESC 
        LIMIT 5
    """).fetchall()
    print(f"Top flags: {top}")
    
    # First 3 sample rows of Flags
    samples = con.execute(f"SELECT Flags FROM '{path}' LIMIT 3").fetchall()
    for i, row in enumerate(samples):
        print(f"  Sample {i}: {row[0]}")


import pandas as pd
from pathlib import Path

import duckdb

duckdb.sql("""
    COPY (SELECT * FROM 'input.snappy.parquet')
    TO 'output.csv' (HEADER, DELIMITER ',')
""")

import pyarrow.parquet as pq

table = pq.read_table('path/to/golden.snappy.parquet')

# Check schema - what's the Flags column type?
print("Schema:")
print(table.schema)

# Check first 5 rows of Flags column
print("\nFirst 5 Flags values:")
flags = table.column('Flags')
for i in range(min(5, len(flags))):
    val = flags[i].as_py()
    print(f"  Row {i}: {val!r}  (type: {type(val).__name__})")

 