"""
Parquet Pipeline - Historical Migration
Downloads pg dumps, restores locally, JOINs tables, parses XML flags,
writes Snappy parquet matching BlobFeeder format, uploads to Data Lake.

Performance: parallel downloads, parallel restores, parallel parquet,
async uploads. Disk-safe with sub-batching for large systems.

OUTPUT FORMAT (unchanged):
- Snappy compressed .parquet
- 1000-row row groups
- Target ~100MB file size
- Same SCHEMA as BlobFeeder
"""

import subprocess
import os
import time
import uuid
import socket
import logging
import requests
import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ============ CONFIG ============
API_BASE = "https://api-datalake.red.prd.euw.gbis.sg-azure.com"
DOWNLOAD_API = f"{API_BASE}/fileshare/get-file"
UPLOAD_API = f"{API_BASE}/datalake/upload-file"
UPLOAD_STREAM_API = f"{API_BASE}/datalake/upload-file-stream"
LIST_FILES_API = f"{API_BASE}/list-files"

LOCAL_PG_HOST = "localhost"
LOCAL_PG_PORT = "5432"
LOCAL_PG_USER = "postgres"
LOCAL_PG_PASS = "redadmin"
LOCAL_PG_DB = "audit"

LOCAL_TEMP = r"D:\parquet_temp"
LOG_DIR = r"D:\parquet_logs"
HOSTNAME = socket.gethostname()

# Performance
DOWNLOAD_BATCH = 5
PARALLEL_DOWNLOADS = 10
PARALLEL_RESTORES = 4
PARALLEL_PARQUET = 6          # was 2 - more parallel partition processing
PARALLEL_UPLOADS = 4

# Output format (DO NOT CHANGE - must match BlobFeeder)
ROW_GROUP_SIZE = 1000         # row group size inside parquet file
MAX_FILE_SIZE_MB = 100        # target file size

# Build buffer - how many rows to accumulate before calling build_table/write_table
# Bigger = less Python overhead, but bigger in-memory allocation.
# Split by system because big-XML systems (riskserver) would overshoot 100MB
# file target with huge buffers.
BUILD_BATCH_BIG = 5000        # riskserver, eliot - big XML per row
BUILD_BATCH_SMALL = 50000     # all other systems - small XML per row

DB_FETCH_SIZE = 100000        # was 10000 - fewer server round-trips

# Disk safety: big systems restore fewer days at once
BIG_SYSTEMS = ["riskserver", "eliot"]
RESTORE_BATCH_BIG = 2
RESTORE_BATCH_SMALL = 5

# Processing order
MONTHS = ["202510", "202509", "202508"]

# UPDATE THIS PER SERVER - split between 2 servers
SYSTEMS = [
    "riskserver", "gold", "eliot", "astro", "bga", "demeter", "efts",
    "iridium", "lma", "onyx", "pdc", "sge", "test", "xone", "xonepayment"
]
# ================================

# Setup
os.makedirs(LOCAL_TEMP, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("pipeline")

lock = threading.Lock()
results = {
    "success": [],
    "failed_download": [],
    "failed_restore": [],
    "failed_parquet": [],
    "failed_upload": [],
}
stats = {"files": 0, "rows": 0, "partitions": 0, "bytes_uploaded": 0}

# Parquet schema - matches BlobFeeder output exactly
FLAGS_TYPE = pa.list_(pa.struct([
    pa.field("Name", pa.string()),
    pa.field("Value", pa.string()),
    pa.field("FieldValue", pa.string()),
]))

SCHEMA = pa.schema([
    pa.field("AuditDate", pa.string()),
    pa.field("ApplicationName", pa.string()),
    pa.field("RedId", pa.string()),
    pa.field("DealId", pa.string()),
    pa.field("ElementaryClientId", pa.string()),
    pa.field("BookingEntityId", pa.string()),
    pa.field("ProductStructure", pa.string()),
    pa.field("TypObj", pa.string()),
    pa.field("RequestTs", pa.timestamp("ns")),
    pa.field("ResponseTs", pa.timestamp("ns")),
    pa.field("Request", pa.string()),
    pa.field("Response", pa.string()),
    pa.field("Flags", FLAGS_TYPE),
])

# Background upload pool
upload_pool = ThreadPoolExecutor(max_workers=PARALLEL_UPLOADS)
pending_uploads = []


# ============ HELPERS ============

def get_days(year, month):
    days = []
    for d in range(1, 32):
        try:
            date(year, month, d)
            days.append(d)
        except ValueError:
            pass
    return days


def disk_free_gb(path="D:\\"):
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        return free / (1024**3)
    except:
        return 999


# ============ DOWNLOAD ============

def download_one(folder, filename, local_path):
    url = f"{DOWNLOAD_API}?path={folder}/{filename}"
    try:
        r = requests.get(url, stream=True, timeout=600)
        if r.status_code != 200:
            return False
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=16 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
        if os.path.getsize(local_path) < 500:
            os.remove(local_path)
            return False
        return True
    except Exception as e:
        log.error(f"Download error {filename}: {e}")
        return False


def download_batch(folder, sys_name, batch_days, month):
    downloaded = []
    with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS) as pool:
        futures = {}
        for day in batch_days:
            date_str = f"{month}{day:02d}"
            detail_file = f"{sys_name}_{date_str}.dump"
            audit_file = f"{sys_name}_raw_audit_{date_str}.dump"
            detail_local = os.path.join(LOCAL_TEMP, detail_file)
            audit_local = os.path.join(LOCAL_TEMP, audit_file)

            fd = pool.submit(download_one, folder, detail_file, detail_local)
            fa = pool.submit(download_one, folder, audit_file, audit_local)
            futures[day] = (fd, fa, date_str, detail_local, audit_local, detail_file, audit_file)

        for day, (fd, fa, date_str, dl, al, df, af) in futures.items():
            dok = fd.result()
            aok = fa.result()
            if dok and aok:
                dsz = os.path.getsize(dl) / (1024**2)
                asz = os.path.getsize(al) / (1024**2)
                log.info(f"    DL {sys_name}_{date_str}: detail={dsz:.0f}MB audit={asz:.0f}MB")
                downloaded.append((day, date_str, dl, al))
            else:
                with lock:
                    if not dok:
                        results["failed_download"].append(f"{sys_name}_{date_str}_detail")
                    if not aok:
                        results["failed_download"].append(f"{sys_name}_{date_str}_audit")
                log.warning(f"    MISSING {sys_name}_{date_str} (detail={dok} audit={aok})")
                for p in [dl, al]:
                    if os.path.exists(p):
                        os.remove(p)
    return downloaded


# ============ RESTORE ============

def restore_one(dump_path, label):
    env = os.environ.copy()
    env["PGPASSWORD"] = LOCAL_PG_PASS
    cmd = f'pg_restore -h {LOCAL_PG_HOST} -p {LOCAL_PG_PORT} -U {LOCAL_PG_USER} -d {LOCAL_PG_DB} --no-owner -a "{dump_path}"'
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    if ret.returncode != 0:
        stderr = ret.stderr.strip()
        if "transaction_timeout" in stderr and "errors ignored" in stderr:
            return True
        if "does not exist" in stderr or "no matching" in stderr:
            log.warning(f"Restore {label}: partition empty/missing")
            return False
        log.error(f"Restore {label} FAILED: {stderr[:300]}")
        return False
    return True


def restore_sub_batch(sub_batch, sys_name):
    """Restore a sub-batch of days. Delete dump files after restore."""
    restored = []
    with ThreadPoolExecutor(max_workers=PARALLEL_RESTORES) as pool:
        futures = {}
        for day, date_str, detail_local, audit_local in sub_batch:
            fd = pool.submit(restore_one, detail_local, f"{sys_name}_{date_str}_detail")
            fa = pool.submit(restore_one, audit_local, f"{sys_name}_{date_str}_audit")
            futures[day] = (fd, fa, date_str, detail_local, audit_local)

        for day, (fd, fa, date_str, dl, al) in futures.items():
            dok = fd.result()
            aok = fa.result()

            # Always delete local dumps after restore attempt
            for p in [dl, al]:
                if os.path.exists(p):
                    os.remove(p)

            if dok and aok:
                restored.append((day, date_str))
                log.info(f"    Restored {sys_name}_{date_str}")
            else:
                with lock:
                    results["failed_restore"].append(f"{sys_name}_{date_str}")
                log.error(f"    Restore FAIL {sys_name}_{date_str}")
    return restored


# ============ UPLOAD ============

def upload_file(local_path, remote_path):
    try:
        file_size = os.path.getsize(local_path)
        if file_size > 100 * 1024 * 1024:
            with open(local_path, "rb") as f:
                r = requests.post(UPLOAD_STREAM_API, params={"path": remote_path}, data=f, timeout=600)
        else:
            with open(local_path, "rb") as f:
                r = requests.post(UPLOAD_API, params={"path": remote_path}, data=f.read(), timeout=300)
        if r.status_code == 200:
            with lock:
                stats["bytes_uploaded"] += file_size
            os.remove(local_path)
            return True
        log.error(f"Upload FAIL {remote_path}: HTTP {r.status_code}")
        return False
    except Exception as e:
        log.error(f"Upload error {remote_path}: {e}")
        return False


def upload_async(local_path, remote_path):
    f = upload_pool.submit(upload_file, local_path, remote_path)
    pending_uploads.append((f, remote_path))


def flush_uploads():
    global pending_uploads
    failed = 0
    for f, path in pending_uploads:
        try:
            if not f.result(timeout=600):
                failed += 1
                with lock:
                    results["failed_upload"].append(path)
        except Exception as e:
            failed += 1
            log.error(f"Upload future error {path}: {e}")
            with lock:
                results["failed_upload"].append(path)
    if failed:
        log.warning(f"  {failed} uploads failed in this batch")
    pending_uploads = []


# ============ CHECK EXISTING ============

def has_existing_files(app, yyyymm, biz_day):
    path = f"v2/{app}/{yyyymm}/businessDay={biz_day}"
    try:
        r = requests.get(LIST_FILES_API, params={"path": path}, timeout=30)
        if r.status_code == 200:
            return len(r.json().get("files", [])) > 0
    except:
        pass
    return False


# ============ XML PARSING (lxml - C-based, 3-10x faster than xml.etree) ============

def parse_flags(response_xml):
    if not response_xml:
        return [{"Name": None, "Value": None, "FieldValue": None}]
    try:
        data = response_xml.encode() if isinstance(response_xml, str) else response_xml
        root = etree.fromstring(data)
        flags = [
            {"Name": f.get("Name", ""), "Value": f.get("Value", ""), "FieldValue": None}
            for f in root.iter("Flag")
        ]
        return flags if flags else [{"Name": None, "Value": None, "FieldValue": None}]
    except Exception:
        return [{"Name": None, "Value": None, "FieldValue": None}]


# ============ PARQUET WRITING ============

def make_writer(parquet_dir, sys_name, date_str):
    guid = str(uuid.uuid4())
    filename = f"data_{sys_name}_{date_str}_histmig_{HOSTNAME}_{guid}.snappy.parquet"
    filepath = os.path.join(parquet_dir, filename)
    writer = pq.ParquetWriter(
        filepath, SCHEMA,
        compression="snappy",
        use_deprecated_int96_timestamps=True,
        coerce_timestamps="ns",
    )
    return writer, filepath


def build_table(rows):
    return pa.table({
        "AuditDate": pa.array([r[0] for r in rows], type=pa.string()),
        "ApplicationName": pa.array([r[1] for r in rows], type=pa.string()),
        "RedId": pa.array([r[2] for r in rows], type=pa.string()),
        "DealId": pa.array([r[3] for r in rows], type=pa.string()),
        "ElementaryClientId": pa.array([r[4] for r in rows], type=pa.string()),
        "BookingEntityId": pa.array([r[5] for r in rows], type=pa.string()),
        "ProductStructure": pa.array([r[6] for r in rows], type=pa.string()),
        "TypObj": pa.array([r[7] for r in rows], type=pa.string()),
        "RequestTs": pa.array([r[8] for r in rows], type=pa.timestamp("ns")),
        "ResponseTs": pa.array([r[9] for r in rows], type=pa.timestamp("ns")),
        "Request": pa.array([r[10] for r in rows], type=pa.string()),
        "Response": pa.array([r[11] for r in rows], type=pa.string()),
        "Flags": pa.array([r[12] for r in rows], type=FLAGS_TYPE),
    }, schema=SCHEMA)


# ============ PROCESS PARTITION ============

def process_one_partition(sys_name, month, day, upload_base):
    date_str = f"{month}{day:02d}"
    detail_table = f"redservice.t_raw_detail_audit_{sys_name}_{month}_{date_str}"
    audit_table = f"redservice.t_raw_audit_{sys_name}_{month}_{date_str}"

    # Pick build batch size based on system (big XML -> small buffer to hit ~100MB)
    build_batch = BUILD_BATCH_BIG if sys_name in BIG_SYSTEMS else BUILD_BATCH_SMALL

    conn = None
    try:
        conn = psycopg2.connect(
            host=LOCAL_PG_HOST, port=LOCAL_PG_PORT,
            user=LOCAL_PG_USER, password=LOCAL_PG_PASS,
            dbname=LOCAL_PG_DB,
        )
        cursor = conn.cursor(name=f"pq_{sys_name}_{date_str}")
        cursor.itersize = DB_FETCH_SIZE

        query = f"""
            SELECT
                TO_CHAR(a.response_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD'),
                a.application_name,
                a.red_id,
                a.deal_id,
                a.elementary_client_id,
                a.booking_entity_id,
                a.product_structure,
                a.typ_obj,
                a.request_ts,
                a.response_ts,
                d.request,
                d.response
            FROM {audit_table} a
            JOIN {detail_table} d ON a.detail_id = d.detail_id
        """
        cursor.execute(query)

        pq_dir = os.path.join(LOCAL_TEMP, f"{sys_name}_{date_str}_pq")
        os.makedirs(pq_dir, exist_ok=True)

        file_count = 0
        row_count = 0
        buf = []
        writer = None
        cur_file = None
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

        while True:
            db_rows = cursor.fetchmany(DB_FETCH_SIZE)
            if not db_rows:
                break

            for row in db_rows:
                flags = parse_flags(row[11])
                buf.append((
                    row[0] or "",
                    (row[1] or "").lower().replace(":", "_"),
                    row[2] or "",
                    row[3] or "",
                    row[4] or "",
                    row[5] or "",
                    row[6] or "",
                    row[7] or "",
                    row[8],
                    row[9],
                    row[10] or "",
                    row[11] or "",
                    flags,
                ))

                if len(buf) >= build_batch:
                    batch = buf[:build_batch]
                    buf = buf[build_batch:]

                    if writer is None:
                        file_count += 1
                        writer, cur_file = make_writer(pq_dir, sys_name, date_str)

                    # write_table with row_group_size=1000 produces 1000-row
                    # row groups in the output parquet, matching BlobFeeder format,
                    # regardless of how many rows are in 'batch'.
                    writer.write_table(build_table(batch), row_group_size=ROW_GROUP_SIZE)
                    row_count += len(batch)

                    # Check size without closing writer
                    try:
                        cur_size = os.path.getsize(cur_file)
                    except:
                        cur_size = 0

                    if cur_size >= max_bytes:
                        writer.close()
                        final_sz = os.path.getsize(cur_file)
                        upload_async(cur_file, f"{upload_base}/{os.path.basename(cur_file)}")
                        log.info(f"      File {file_count}: {final_sz/(1024*1024):.0f} MB")
                        writer = None
                        cur_file = None

        # Remaining buffer
        if buf:
            if writer is None:
                file_count += 1
                writer, cur_file = make_writer(pq_dir, sys_name, date_str)
            writer.write_table(build_table(buf), row_group_size=ROW_GROUP_SIZE)
            row_count += len(buf)

        # Close and upload final file
        if writer:
            writer.close()
            if cur_file and os.path.exists(cur_file):
                final_sz = os.path.getsize(cur_file)
                upload_async(cur_file, f"{upload_base}/{os.path.basename(cur_file)}")
                log.info(f"      File {file_count}: {final_sz/(1024*1024):.0f} MB (final)")

        cursor.close()
        conn.close()

        try:
            os.rmdir(pq_dir)
        except:
            pass

        return file_count, row_count

    except Exception as e:
        log.error(f"Process {sys_name}_{date_str} error: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return 0, 0


def truncate_tables(sys_name, month, date_str):
    try:
        conn = psycopg2.connect(
            host=LOCAL_PG_HOST, port=LOCAL_PG_PORT,
            user=LOCAL_PG_USER, password=LOCAL_PG_PASS,
            dbname=LOCAL_PG_DB,
        )
        cur = conn.cursor()
        cur.execute(f"TRUNCATE redservice.t_raw_detail_audit_{sys_name}_{month}_{date_str}")
        cur.execute(f"TRUNCATE redservice.t_raw_audit_{sys_name}_{month}_{date_str}")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.error(f"Truncate error {sys_name}_{date_str}: {e}")


def process_and_truncate(sys_name, month, day, date_str, year, mon):
    """Full cycle for one partition: check existing -> parquet -> truncate"""
    biz_day = f"{year}-{mon:02d}-{day:02d}"

    existing = has_existing_files(sys_name, month, biz_day)
    if existing:
        upload_base = f"v2/{sys_name}/{month}/businessDay={biz_day}_new"
        log.info(f"    {sys_name}_{date_str}: existing files -> _new")
    else:
        upload_base = f"v2/{sys_name}/{month}/businessDay={biz_day}"

    t0 = time.time()
    fc, rc = process_one_partition(sys_name, month, day, upload_base)
    dt = time.time() - t0

    if fc > 0:
        with lock:
            stats["files"] += fc
            stats["rows"] += rc
            stats["partitions"] += 1
            results["success"].append(f"{sys_name}_{date_str}")
        log.info(f"    DONE {sys_name}_{date_str} | {fc} files | {rc} rows | {dt/60:.1f} min")
    else:
        with lock:
            results["failed_parquet"].append(f"{sys_name}_{date_str}")
        log.error(f"    FAIL parquet {sys_name}_{date_str}")

    truncate_tables(sys_name, month, date_str)
    return fc, rc


# ============ MAIN ============

def main():
    t_start = time.time()

    log.info("=" * 60)
    log.info("  PARQUET PIPELINE - MAX PERFORMANCE")
    log.info(f"  Host: {HOSTNAME}")
    log.info(f"  Systems: {len(SYSTEMS)} -> {SYSTEMS}")
    log.info(f"  Months: {MONTHS}")
    log.info(f"  Download batch: {DOWNLOAD_BATCH} days")
    log.info(f"  Restore batch: big={RESTORE_BATCH_BIG} small={RESTORE_BATCH_SMALL}")
    log.info(f"  Parallel: dl={PARALLEL_DOWNLOADS} restore={PARALLEL_RESTORES} pq={PARALLEL_PARQUET} upload={PARALLEL_UPLOADS}")
    log.info(f"  Build batch: big={BUILD_BATCH_BIG} small={BUILD_BATCH_SMALL}")
    log.info(f"  Row group: {ROW_GROUP_SIZE} | Max file: {MAX_FILE_SIZE_MB}MB | DB fetch: {DB_FETCH_SIZE}")
    log.info(f"  Disk free: {disk_free_gb():.1f} GB")
    log.info(f"  Log: {log_file}")
    log.info("=" * 60)

    for month in MONTHS:
        year = int(month[:4])
        mon = int(month[4:])
        days = get_days(year, mon)
        folder = f"dumps_{month}"

        log.info(f"\n{'='*50}")
        log.info(f"  MONTH: {month} | {len(days)} days | {len(SYSTEMS)} systems")
        log.info(f"{'='*50}")

        for sys_name in SYSTEMS:
            sys_t0 = time.time()
            log.info(f"\n--- {sys_name.upper()} | {month} ---")

            restore_batch_size = RESTORE_BATCH_BIG if sys_name in BIG_SYSTEMS else RESTORE_BATCH_SMALL

            for dl_start in range(0, len(days), DOWNLOAD_BATCH):
                dl_days = days[dl_start:dl_start + DOWNLOAD_BATCH]
                log.info(f"\n  Download batch: days {dl_days[0]}-{dl_days[-1]}")

                # Check disk space
                free = disk_free_gb()
                if free < 50:
                    log.warning(f"  LOW DISK: {free:.1f} GB free. Waiting for uploads...")
                    flush_uploads()
                    free = disk_free_gb()
                    if free < 50:
                        log.error(f"  CRITICAL: only {free:.1f} GB free. Skipping batch.")
                        continue

                # Step 1: Download all 5 days (10 dumps) in parallel
                dl_t0 = time.time()
                downloaded = download_batch(folder, sys_name, dl_days, month)
                log.info(f"  Downloaded {len(downloaded)}/{len(dl_days)} in {time.time()-dl_t0:.0f}s")

                if not downloaded:
                    continue

                # Step 2 & 3: Restore and process in sub-batches (disk safe)
                for sub_start in range(0, len(downloaded), restore_batch_size):
                    sub = downloaded[sub_start:sub_start + restore_batch_size]
                    sub_days = [d[1] for d in sub]
                    log.info(f"\n  Restore sub-batch: {sub_days}")

                    # Restore
                    rs_t0 = time.time()
                    restored = restore_sub_batch(sub, sys_name)
                    log.info(f"  Restored {len(restored)}/{len(sub)} in {time.time()-rs_t0:.0f}s")

                    if not restored:
                        continue

                    # Parallel parquet generation
                    pq_t0 = time.time()
                    with ThreadPoolExecutor(max_workers=PARALLEL_PARQUET) as pq_pool:
                        pq_futures = []
                        for day, date_str in restored:
                            f = pq_pool.submit(process_and_truncate, sys_name, month, day, date_str, year, mon)
                            pq_futures.append(f)
                        for f in as_completed(pq_futures):
                            try:
                                f.result()
                            except Exception as e:
                                log.error(f"  Parquet thread error: {e}")

                    # Flush uploads before next sub-batch to free disk
                    flush_uploads()
                    log.info(f"  Sub-batch done in {(time.time()-pq_t0)/60:.1f} min | Disk: {disk_free_gb():.0f} GB free")

                # Progress
                elapsed = time.time() - t_start
                log.info(f"\n  PROGRESS: {stats['partitions']} parts | {stats['files']} files | {stats['rows']} rows | {stats['bytes_uploaded']/(1024**3):.1f} GB up | {elapsed/3600:.1f} hrs")

            sys_dt = time.time() - sys_t0
            log.info(f"\n  {sys_name} done in {sys_dt/60:.1f} min")

    # Final flush
    flush_uploads()

    elapsed = time.time() - t_start
    up_gb = stats["bytes_uploaded"] / (1024**3)

    log.info("\n" + "=" * 60)
    log.info("  PIPELINE COMPLETE")
    log.info(f"  Time: {elapsed/3600:.1f} hours")
    log.info(f"  Partitions: {stats['partitions']}")
    log.info(f"  Files: {stats['files']}")
    log.info(f"  Rows: {stats['rows']}")
    log.info(f"  Uploaded: {up_gb:.2f} GB")
    log.info(f"  Success: {len(results['success'])}")
    log.info(f"  Failed DL: {len(results['failed_download'])}")
    log.info(f"  Failed restore: {len(results['failed_restore'])}")
    log.info(f"  Failed parquet: {len(results['failed_parquet'])}")
    log.info(f"  Failed upload: {len(results['failed_upload'])}")

    for key in ["failed_download", "failed_restore", "failed_parquet", "failed_upload"]:
        if results[key]:
            log.info(f"\n  {key}: {results[key]}")

    log.info("=" * 60)

    # Summary file
    sf = os.path.join(LOG_DIR, f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(sf, "w") as f:
        f.write(f"Time: {elapsed/3600:.1f} hrs\n")
        f.write(f"Partitions: {stats['partitions']}\n")
        f.write(f"Files: {stats['files']}\n")
        f.write(f"Rows: {stats['rows']}\n")
        f.write(f"Uploaded: {up_gb:.2f} GB\n")
        for key in results:
            f.write(f"{key}: {results[key]}\n")


if __name__ == "__main__":
    main()
