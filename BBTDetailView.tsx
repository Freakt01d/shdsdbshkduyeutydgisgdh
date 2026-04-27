CREATE INDEX CONCURRENTLY idx_raw_audit_detail_id 
ON redservice.t_raw_audit (detail_id);


ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET checkpoint_timeout = '5min';
ALTER SYSTEM SET work_mem = '128MB';
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
SELECT pg_reload_conf();

import pandas as pd
from pathlib import Path

import duckdb

duckdb.sql("""
    COPY (SELECT * FROM 'input.snappy.parquet')
    TO 'output.csv' (HEADER, DELIMITER ',')
""")


def parquet_to_csv(parquet_path, csv_path=None):
    """Convert a single .snappy.parquet file to CSV."""
    parquet_path = Path(parquet_path)
    if csv_path is None:
        csv_path = parquet_path.with_suffix('.csv')
        if parquet_path.suffixes[-2:] == ['.snappy', '.parquet']:
            csv_path = parquet_path.with_name(parquet_path.stem.replace('.snappy', '') + '.csv')

    df = pd.read_parquet(parquet_path, engine='pyarrow')
    df.to_csv(csv_path, index=False)
    print(f"Converted: {parquet_path} -> {csv_path} ({len(df)} rows)")
    return csv_path


def batch_convert(input_dir, output_dir=None):
    """Convert all .snappy.parquet files in a directory."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list(input_dir.glob('*.snappy.parquet')) + list(input_dir.glob('*.parquet'))
    for f in files:
        out = output_dir / (f.stem.replace('.snappy', '') + '.csv')
        parquet_to_csv(f, out)


if __name__ == '__main__':
    # Single file
    parquet_to_csv('data.snappy.parquet')

    # Or batch convert a folder
    # batch_convert('input_folder', 'output_folder')
