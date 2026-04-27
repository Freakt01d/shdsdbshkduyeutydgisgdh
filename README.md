import duckdb

con = duckdb.connect()

GOLDEN = "data_astro_20260423_posttrade_red-azure-blobfeeder-XXX.snappy.parquet"

# Just show the schema first
print("=== Schema ===")
schema = con.execute(f"DESCRIBE SELECT * FROM '{GOLDEN}'").fetchall()
for col_name, col_type, *rest in schema:
    print(f"  {col_name:25s} {col_type}")

# Show first 5 Flags values raw
print("\n=== First 5 Flags ===")
result = con.execute(f"SELECT Flags FROM '{GOLDEN}' LIMIT 5").fetchall()
for i, row in enumerate(result):
    print(f"  Row {i}: {row[0]}")
