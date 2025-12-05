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
        cursor.execute("ALTER SESSION SET COMMIT_WRITE = 'BATCH,NOWAIT'")
        cursor.execute("ALTER SESSION ENABLE PARALLEL DML")
        cursor.execute("ALTER SESSION SET PARALLEL_DEGREE_POLICY = AUTO")
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

def direct_partition_transfer(args):
    """Direct transfer of partitions from source to destination"""
    process_id, partition_names, table_name, schema, columns, progress_queue = args
    
    try:
        # Create connections
        src_conn, src_cursor = create_source_connection()
        dest_conn, dest_cursor = create_dest_connection()
        
        total_rows = 0
        process_start_time = time.time()
        
        # Build INSERT statement with bind variables
        placeholders = ', '.join([f':{i+1}' for i in range(len(columns))])
        insert_sql = f"""
            INSERT /*+ APPEND_VALUES PARALLEL(8) */ 
            INTO {table_name} ({', '.join(columns)}) 
            VALUES ({placeholders})
        """
        
        for idx, partition_name in enumerate(partition_names, 1):
            partition_start = time.time()
            partition_rows = 0
            
            try:
                print(f"Process {process_id}: Starting partition {partition_name} ({idx}/{len(partition_names)})")
                
                # Build SELECT query
                columns_str = ", ".join(columns)
                select_sql = f"""
                    SELECT /*+ PARALLEL(8) */ {columns_str} 
                    FROM {schema}.{table_name} PARTITION ({partition_name})
                """
                
                # Execute source query
                src_cursor.execute(select_sql)
                
                # Transfer data in batches
                while True:
                    # Fetch batch from source
                    rows = src_cursor.fetchmany(FETCH_BATCH_SIZE)
                    if not rows:
                        break
                    
                    # Process in smaller insert batches for better memory management
                    for i in range(0, len(rows), INSERT_BATCH_SIZE):
                        batch = rows[i:i + INSERT_BATCH_SIZE]
                        
                        try:
                            # Bulk insert with error handling
                            dest_cursor.executemany(insert_sql, batch, batcherrors=True)
                            
                            # Check for errors
                            errors = dest_cursor.getbatcherrors()
                            if errors:
                                print(f"Process {process_id}: {len(errors)} errors in batch")
                                for error in errors[:5]:  # Show first 5 errors
                                    print(f"  Error at row {error.offset}: {error.message}")
                            
                            partition_rows += len(batch)
                            total_rows += len(batch)
                            
                            # Commit at intervals to avoid huge transactions
                            if total_rows % COMMIT_INTERVAL == 0:
                                dest_conn.commit()
                                elapsed = time.time() - partition_start
                                speed = partition_rows / elapsed if elapsed > 0 else 0
                                print(f"  Process {process_id}: {partition_rows:,} rows, {speed:,.0f} rows/s")
                                
                        except Exception as e:
                            print(f"Process {process_id}: Insert error - {e}")
                            # Try to continue with next batch
                            continue
                    
                    # Free memory periodically
                    if partition_rows % (FETCH_BATCH_SIZE * 10) == 0:
                        gc.collect()
                
                # Final commit for partition
                dest_conn.commit()
                
                partition_time = time.time() - partition_start
                speed = partition_rows / partition_time if partition_time > 0 else 0
                print(f"Process {process_id}: Completed {partition_name} - {partition_rows:,} rows in {format_elapsed_time(partition_time)} ({speed:,.0f} rows/s)")
                
                # Report progress
                progress_queue.put((process_id, partition_name, partition_rows, partition_time))
                
                # Calculate and display ETA
                if idx < len(partition_names):
                    avg_time = (time.time() - process_start_time) / idx
                    eta_seconds = avg_time * (len(partition_names) - idx)
                    print(f"  Process {process_id}: ETA: {format_elapsed_time(eta_seconds)}")
                    
            except Exception as e:
                print(f"Process {process_id}: Error processing partition {partition_name} - {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Close connections
        src_cursor.close()
        src_conn.close()
        dest_cursor.close()
        dest_conn.close()
        
        total_time = time.time() - process_start_time
        print(f"Process {process_id}: Finished - {total_rows:,} rows in {format_elapsed_time(total_time)}")
        
        return process_id, total_rows, total_time
        
    except Exception as e:
        print(f"Process {process_id}: Fatal error - {e}")
        import traceback
        traceback.print_exc()
        return process_id, 0, 0

def progress_monitor(progress_queue, total_partitions):
    """Monitor progress across all processes"""
    completed = 0
    start_time = time.time()
    
    while completed < total_partitions:
        try:
            # Get progress update (with timeout to avoid hanging)
            process_id, partition_name, rows, time_taken = progress_queue.get(timeout=60)
            completed += 1
            
            elapsed = time.time() - start_time
            percent = (completed / total_partitions) * 100
            
            print(f"\n=== PROGRESS: {completed}/{total_partitions} partitions ({percent:.1f}%) ===")
            print(f"Total elapsed: {format_elapsed_time(elapsed)}")
            
            if completed < total_partitions:
                avg_time_per_partition = elapsed / completed
                eta = avg_time_per_partition * (total_partitions - completed)
                print(f"Overall ETA: {format_elapsed_time(eta)}")
            print("=" * 50 + "\n")
            
        except:
            # Timeout or error, continue monitoring
            continue

def transfer_table_parallel(table_name, schema=SCHEMA, columns=None):
    """
    Direct parallel transfer from source to destination without intermediate files
    """
    start_time = time.time()
    
    print(f"Starting DIRECT parallel database transfer with {NUM_PROCESSES} processes...")
    print(f"Table: {table_name}")
    print(f"Source: {hostname}:{port}/{service_name}")
    print(f"Destination: {dest_hostname}:{dest_port}/{dest_sid}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get partition information
    print("Analyzing partitions...")
    partitions = get_partition_list(table_name, schema)
    partition_names = [p[0] for p in partitions]
    total_estimated_rows = sum(p[1] for p in partitions)
    
    print(f"Found {len(partitions)} partitions")
    print(f"Estimated total rows: {total_estimated_rows:,}\n")
    
    if not partitions:
        print("ERROR: No partitions found!")
        return None, None, None
    
    # Truncate destination table
    try:
        truncate_destination_table(table_name)
    except Exception:
        print("Halting execution due to truncation error.")
        return None, None, None
    
    # Create progress queue
    manager = Manager()
    progress_queue = manager.Queue()
    
    # Distribute partitions across processes
    partitions_per_process = len(partition_names) // NUM_PROCESSES
    process_args = []
    
    for i in range(NUM_PROCESSES):
        start_idx = i * partitions_per_process
        end_idx = len(partition_names) if i == NUM_PROCESSES - 1 else (i + 1) * partitions_per_process
        
        process_partitions = partition_names[start_idx:end_idx]
        if process_partitions:  # Only add if there are partitions to process
            process_args.append((i, process_partitions, table_name, schema, columns, progress_queue))
            print(f"Process {i}: Assigned {len(process_partitions)} partitions")
    
    print(f"\nStarting {len(process_args)} parallel transfer processes...\n")
    
    # Start progress monitor in separate thread
    import threading
    monitor_thread = threading.Thread(target=progress_monitor, args=(progress_queue, len(partition_names)))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Execute parallel transfer
    with Pool(processes=len(process_args), initializer=init_worker) as pool:
        results = pool.map(direct_partition_transfer, process_args)
    
    # Calculate totals
    total_rows = sum(r[1] for r in results)
    total_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print("DIRECT TRANSFER COMPLETE!")
    print(f"{'='*80}")
    print(f"  Total rows transferred: {total_rows:,}")
    print(f"  Total partitions: {len(partitions)}")
    print(f"  Total time: {format_elapsed_time(total_time)}")
    print(f"  Average speed: {total_rows/total_time:,.0f} rows/second")
    print(f"  Parallel processes: {NUM_PROCESSES}")
    print(f"  Network throughput: ~{(total_rows * 200) / (total_time * 1024 * 1024):.1f} MB/s")  # Assuming ~200 bytes per row
    print(f"  Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    return total_rows, 0, total_time

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
    print("DIRECT DATABASE TRANSFER - No Intermediate Files!")
    print("Optimized for: 256 GB RAM, Intel Xeon Platinum, 10 Gbps Network")
    print("="*80 + "\n")
    
    # Initialize Oracle Client in main process
    try:
        init_worker()
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Oracle client - {e}")
        print("Please ensure Oracle Instant Client is installed and configured.")
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
            print(f"\nTotal execution time: {format_elapsed_time(time.time() - overall_start)}")
            
            # Optional: Verify the transfer
            print("\nDo you want to verify the transfer? (This will count all rows)")
            # Comment out the input line for automated runs
            # if input("Enter 'y' to verify: ").lower() == 'y':
            #     verify_transfer(table_name)
            
    except KeyboardInterrupt:
        print("\n\nTransfer interrupted by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
