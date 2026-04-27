import duckdb

con = duckdb.connect()

GOLDEN = "data_astro_20260423_posttrade_red-azure-blobfeeder-posttrade-XXX.snappy.parquet"
MINE = "your_output_file.snappy.parquet"

for label, path in [("GOLDEN", GOLDEN), ("MINE", MINE)]:
    print(f"\n=== {label} ===")
    
    # Row count
    count = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
    print(f"Rows: {count}")
    
    # Avg flags per row - use array_length, not length
    avg_flags = con.execute(f"""
        SELECT AVG(array_length(Flags)) FROM '{path}'
    """).fetchone()[0]
    print(f"Avg flags per row: {avg_flags:.2f}")
    
    # Top 5 flag names - unnest the list of structs
    top = con.execute(f"""
        SELECT flag.Name, COUNT(*) AS cnt
        FROM '{path}', UNNEST(Flags) AS t(flag)
        WHERE flag.Name IS NOT NULL
        GROUP BY flag.Name 
        ORDER BY cnt DESC 
        LIMIT 5
    """).fetchall()
    print(f"Top flags: {top}")
    
    # First 3 sample rows
    samples = con.execute(f"SELECT Flags FROM '{path}' LIMIT 3").fetchall()
    for i, row in enumerate(samples):
        print(f"  Sample {i}: {row[0]}")
