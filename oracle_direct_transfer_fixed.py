import oracledb
import os
from datetime import datetime
import time
import multiprocessing
from multiprocessing import Pool, Manager, Queue
import gc

# --- Thick Mode Initialization ---
def init_worker():
    """Initializes the Oracle client for thick mode in worker processes."""
    try:
        oracledb.init_oracle_client()
    except Exception as e:
        print(f"Error initializing Oracle client in worker: {e}")
        raise

# Database connection details
SCHEMA = "placeholder"
username = SCHEMA
password = "placeholder"
hostname = "placeholder.fr.world"
port = "placeholder"
service_name = "placeholder"

# Create connection string
dsn = oracledb.makedsn(hostname, port, service_name=service_name)
connection_string = f"{username}/{password}@{dsn}"

# Destination database connection details
dest_username = SCHEMA
dest_password = "placeholder"
dest_hostname = "placeholder.ocp.cloud"
dest_port = "placeholder"
dest_sid = "placeholder"

# Create destination connection string
dest_dsn = oracledb.makedsn(dest_hostname, dest_port, sid=dest_sid)
dest_connection_string = f"{dest_username}/{dest_password}@{dest_dsn}"

# HIGH PERFORMANCE Configuration - Optimized for 256 GB RAM and 10 Gbps network
FETCH_BATCH_SIZE = 50000      # Rows to fetch at once from source
INSERT_BATCH_SIZE = 25000     # Rows to insert at once to destination
NUM_PROCESSES = 20             # Intel Xeon Platinum 8260 has 24 cores x 2 = 48 threads, use 20 for balance
COMMIT_INTERVAL = 100000      # Commit every 100K rows to avoid long transactions

# Connection pool settings
POOL_MIN = 2
POOL_MAX = 5
POOL_INCREMENT = 1

def format_elapsed_time(seconds):
    """Format elapsed time"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def create_source_connection():
    """Create optimized source connection"""
    try:
        connection = oracledb.connect(connection_string)
        cursor = connection.cursor()
        # Optimize for reading
        cursor.arraysize = FETCH_BATCH_SIZE
        cursor.prefetchrows = FETCH_BATCH_SIZE * 2
        cursor.execute("ALTER SESSION SET OPTIMIZER_MODE = FIRST_ROWS_1000")
        cursor.execute("ALTER SESSION SET STATISTICS_LEVEL = BASIC")
        return connection, cursor
    except Exception as e:
        print(f"Source connection error: {e}")
        raise

def create_dest_connection():
    """Create optimized destination connection"""
    try:
        connection = oracledb.connect(dest_connection_string)
        cursor = connection.cursor()
        # Optimize for bulk inserts
        cursor.arraysize = INSERT_BATCH_SIZE  # Match our insert batch size
        cursor.execute("ALTER SESSION SET COMMIT_WRITE = 'BATCH,NOWAIT'")
        # Additional optimizations for bulk operations
        cursor.execute("ALTER SESSION SET RECYCLEBIN = OFF")
        cursor.execute("ALTER SESSION SET \"_OPTIMIZER_USE_FEEDBACK\" = FALSE")
        # Note: Not enabling PARALLEL DML as it conflicts with batcherrors=True
        return connection, cursor
    except Exception as e:
        print(f"Destination connection error: {e}")
        raise

def get_partition_list(table_name, schema):
    """Get list of partitions for parallel processing"""
    connection, cursor = create_source_connection()
    
    query = f"""
        SELECT partition_name, num_rows
        FROM all_tab_partitions 
        WHERE table_owner = '{schema}' 
        AND table_name = '{table_name}'
        ORDER BY partition_position
    """
    
    cursor.execute(query)
    partitions = [(row[0], row[1] if row[1] else 0) for row in cursor.fetchall()]
    
    cursor.close()
    connection.close()
    
    return partitions

def truncate_destination_table(table_name):
    """Truncates the destination table."""
    try:
        print(f"\nTruncating destination table {table_name}...")
        dest_connection, dest_cursor = create_dest_connection()
        
        truncate_sql = f"TRUNCATE TABLE {table_name}"
        dest_cursor.execute(truncate_sql)
        print(f"Table {table_name} truncated successfully.\n")
        
        dest_cursor.close()
        dest_connection.close()
    except Exception as e:
        print(f"ERROR: Failed to truncate destination table {table_name} - {e}")
        raise

def _log_partition_progress(process_id, partition_rows, partition_start):
    """Logs the progress of a partition export - KEEPING ORIGINAL FORMAT"""
    elapsed = time.time() - partition_start
    speed = partition_rows / elapsed if elapsed > 0 else 0
    print(f"    Process {process_id}: {partition_rows:,} rows, {speed:,.0f} rows/s")

def _log_partition_completion(process_id, partition_name, partition_rows, partition_time, process_start_time, partition_idx, total_partitions):
    """Logs the completion of a partition export and calculates ETA - KEEPING ORIGINAL FORMAT"""
    print(f"  Process {process_id}: Partition {partition_name} - {partition_rows:,} rows in {format_elapsed_time(partition_time)}")
    remaining_partitions = total_partitions - partition_idx
    if remaining_partitions > 0:
        avg_time_per_partition = (time.time() - process_start_time) / partition_idx
        eta_seconds = avg_time_per_partition * remaining_partitions
        print(f"    Process {process_id}: ETA for remaining {remaining_partitions} partitions: {format_elapsed_time(eta_seconds)}")

def direct_partition_transfer(args):
    """Direct transfer of partitions from source to destination - WITH ORIGINAL LOGGING STYLE"""
    process_id, partition_names, table_name, schema, columns, progress_queue = args
    
    try:
        # Create connections
        src_conn, src_cursor = create_source_connection()
        dest_conn, dest_cursor = create_dest_connection()
        
        total_rows = 0
        process_start_time = time.time()
        total_partitions = len(partition_names)
        
        # Build INSERT statement with proper date handling
        # Date columns need special handling
        date_columns = ['REF_DATE', 'CREATED_DATE', 'MODIFIED_DATE']
        column_binds = []
        for i, col in enumerate(columns):
            if col in date_columns:
                # Use TO_DATE for date columns
                column_binds.append(f"TO_DATE(:{i+1}, 'YYYY-MM-DD HH24:MI:SS')")
            else:
                column_binds.append(f":{i+1}")
        
        columns_str_insert = ", ".join(column_binds)
        # Remove PARALLEL hint as it conflicts with batcherrors=True
        insert_sql = f"""
            INSERT /*+ APPEND_VALUES */ 
            INTO {table_name} ({', '.join(columns)}) 
            VALUES ({columns_str_insert})
        """
        
        for partition_idx, partition_name in enumerate(partition_names, 1):
            partition_start = time.time()
            partition_rows = 0
            
            print(f"  Process {process_id}: Exporting partition {partition_name} ({partition_idx}/{total_partitions})")
            
            try:
                # Build SELECT query with date conversion (as in original)
                select_cols = []
                for col in columns:
                    if col in date_columns:
                        select_cols.append(f"TO_CHAR({col}, 'YYYY-MM-DD HH24:MI:SS') as {col}")
                    else:
                        select_cols.append(col)
                
                columns_str = ", ".join(select_cols)
                query = f"SELECT {columns_str} FROM {schema}.{table_name} PARTITION ({partition_name})"
                
                try:
                    src_cursor.execute(query)
                except Exception as e:
                    print(f"  Process {process_id}: ERROR executing query for {partition_name}: {e}")
                    continue
                
                batch_count = 0
                while True:
                    try:
                        # Fetch batch from source
                        rows = src_cursor.fetchmany(FETCH_BATCH_SIZE)
                        if not rows:
                            break
                        
                        # Convert rows to handle NULL values properly (as in original)
                        converted_rows = []
                        for row in rows:
                            # Handle both empty strings and None values
                            converted_row = tuple(
                                None if (val == '' or val is None) else val 
                                for val in row
                            )
                            converted_rows.append(converted_row)
                        
                        # Direct insert in smaller chunks (replacing CSV write)
                        for i in range(0, len(converted_rows), INSERT_BATCH_SIZE):
                            batch = converted_rows[i:i + INSERT_BATCH_SIZE]
                            
                            # Bulk insert with error handling
                            dest_cursor.executemany(insert_sql, batch, batcherrors=True)
                            
                            # Check for errors (but don't spam the log)
                            errors = dest_cursor.getbatcherrors()
                            if errors:
                                for error in errors[:10]:  # Only show first 10 errors
                                    print(f"  Process {process_id}: Error at row {error.offset}: {error.message}")
                                if len(errors) > 10:
                                    print(f"  Process {process_id}: ... and {len(errors) - 10} more errors")
                            
                            partition_rows += len(batch)
                            total_rows += len(batch)
                        
                        batch_count += 1
                        
                        # Log progress similar to original (every 10 batches)
                        if batch_count % 10 == 0:
                            dest_conn.commit()  # Commit periodically
                            _log_partition_progress(process_id, partition_rows, partition_start)
                            
                    except MemoryError:
                        print(f"  Process {process_id}: MEMORY ERROR during fetch - flushing and continuing")
                        dest_conn.commit()
                        break
                
                # Final commit for partition
                dest_conn.commit()
                
                partition_time = time.time() - partition_start
                _log_partition_completion(process_id, partition_name, partition_rows, partition_time, 
                                         process_start_time, partition_idx, total_partitions)
                
                # Force garbage collection to free memory (as in original)
                gc.collect()
                
            except Exception as e:
                print(f"  Process {process_id}: Error processing partition {partition_name} - {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Close connections
        src_cursor.close()
        src_conn.close()
        dest_cursor.close()
        dest_conn.close()
        
        print(f"  Process {process_id}: ✔ All partitions completed - {total_rows:,} total rows")
        return process_id, total_rows, 0
        
    except Exception as e:
        print(f"  Process {process_id}: Error - {e}")
        import traceback
        traceback.print_exc()
        return process_id, 0, 0

def transfer_table_parallel(table_name, schema=SCHEMA, columns=None, total_rows=2566858507):
    """
    Direct parallel transfer from source to destination without intermediate files
    KEEPING ORIGINAL LOGGING FORMAT
    """
    start_time = time.time()
    
    print(f"Starting PIPELINED parallel export/import with {NUM_PROCESSES} processes...")
    print(f"Table: {table_name}")
    print(f"Expected total rows: {total_rows:,}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get list of partitions (same as original)
    print("Fetching partition list...")
    partitions = get_partition_list(table_name, schema)
    print(f"Found {len(partitions):,} partitions\n")
    
    if not partitions:
        print("ERROR: No partitions found! Table may not be partitioned.")
        print("Falling back to single-threaded export...")
        return None, None, None
    
    # Truncate the destination table before starting (same as original)
    try:
        truncate_destination_table(table_name)
    except Exception:
        print("Halting execution due to error during table truncation.")
        return None, None, None
    
    # Create output directory (keeping for compatibility even though we don't use files)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.getcwd(), f"export_parallel_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Output directory: {output_dir}\n")
    
    # Create a manager for shared objects
    manager = Manager()
    progress_queue = manager.Queue()
    
    # Distribute partitions across processes (same distribution as original)
    partition_names = [p[0] for p in partitions]
    partitions_per_process = len(partition_names) // NUM_PROCESSES
    export_chunks = []
    
    for i in range(NUM_PROCESSES):
        start_idx = i * partitions_per_process
        end_idx = len(partition_names) if i == NUM_PROCESSES - 1 else (i + 1) * partitions_per_process
        
        process_partitions = partition_names[start_idx:end_idx]
        export_chunks.append((i, process_partitions, table_name, schema, columns, progress_queue))
        
        print(f"  Export Process {i}: Assigned {len(process_partitions):,} partitions")
    
    print(f"\nLaunching {NUM_PROCESSES} parallel export processes...\n")
    
    # Execute parallel transfer
    with Pool(processes=NUM_PROCESSES, initializer=init_worker) as pool:
        export_results = pool.map(direct_partition_transfer, export_chunks)
    
    total_exported = sum(rows for _, rows, _ in export_results)
    
    total_time = time.time() - start_time
    
    # Keep exact same output format as original
    print(f"\n{'='*80}")
    print("✔ PIPELINED EXPORT/IMPORT COMPLETE!")
    print(f"{'='*80}")
    print(f"  Total rows exported and imported: {total_exported:,}")
    print(f"  Partitions processed: {len(partitions):,}")
    print(f"  Total time: {format_elapsed_time(total_time)}")
    print(f"  Parallel processes (Export/Import): {NUM_PROCESSES}/{NUM_PROCESSES//2}")
    print(f"  Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    return total_exported, 0, total_time  # size is 0 as we don't use files

def verify_transfer(table_name):
    """Verify row counts match between source and destination"""
    print("\nVerifying transfer...")
    
    # Get source count
    src_conn, src_cursor = create_source_connection()
    src_cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table_name}")
    src_count = src_cursor.fetchone()[0]
    src_cursor.close()
    src_conn.close()
    
    # Get destination count
    dest_conn, dest_cursor = create_dest_connection()
    dest_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    dest_count = dest_cursor.fetchone()[0]
    dest_cursor.close()
    dest_conn.close()
    
    print(f"Source rows: {src_count:,}")
    print(f"Destination rows: {dest_count:,}")
    
    if src_count == dest_count:
        print("✓ Verification PASSED - counts match!")
    else:
        diff = src_count - dest_count
        print(f"✗ Verification FAILED - missing {diff:,} rows")
    
    return src_count, dest_count

# Main execution
if __name__ == "__main__":
    print("="*80)
    print("PARTITION-BASED PARALLEL EXPORT - Maximum Speed!")
    print("="*80 + "\n")

    # Initialize Oracle Client in the main process for thick mode
    try:
        init_worker()
    except Exception as e:
        print(f"✗ CRITICAL: Failed to initialize Oracle client in main process. - {e}")
        print("  Please ensure Oracle Instant Client is installed and configured correctly.")
        exit(1)

    # Table configuration
    table_name = 'EDS_IDX_COMP_ITEM'
    columns = [
        'INDEX_COMPOSITION_ITEM_ID',
        'INDEX_ID',
        'REF_DATE',
        'CURRENCY_ID',
        'MARKET_ID',
        'BO_CODE',
        'BO_MNEMO',
        'UNDERLYING_ID',
        'UNDERLYING_TYPE',
        'WEIGHTING',
        'COMPANY_ID',
        'NB_ISSUED',
        'MARKET_PRODUCT_ID',
        'CREATED_DATE',
        'MODIFIED_DATE'
    ]
    
    overall_start = time.time()
    
    try:
        rows, _, elapsed = transfer_table_parallel(table_name, columns=columns)
        if rows:
            print(f"\nTotal time: {format_elapsed_time(time.time() - overall_start)}")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
