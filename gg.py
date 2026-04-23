“””
Parquet Pipeline - RISKSERVER ONLY (Async Pipelined)

ASYNC PIPELINE STAGES (all run concurrently, connected by queues):

1. DOWNLOAD stage  - up to 2 parallel downloads (detail+audit), max 5 days on disk
1. RESTORE stage   - 1 day restoring, 1 day queued (pre-restore next while processing)
1. PARQUET stage   - 1 partition processing (streaming, serial)
1. UPLOAD stage    - 4 parallel uploads (background)

Restore overlaps with parquet: N+1 restores in DB while N is being parqueted.
Max 2 partitions in DB at once (~136GB). Download keeps ahead of restore.

Tuned for riskserver: ~311k rows/partition, 1MB avg row, 3.3MB max row.

OUTPUT FORMAT (unchanged):

- Snappy parquet, 1000-row row groups, ~100MB files
- Schema matches BlobFeeder exactly
- Filename: data_riskserver_{date}*histmig*{host}_{guid}.snappy.parquet
- Upload path: v2/riskserver/{month}/businessDay={biz_day}/
  “””

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
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading

# ============ CONFIG ============

API_BASE = “https://api-datalake.red.prd.euw.gbis.sg-azure.com”
DOWNLOAD_API = f”{API_BASE}/fileshare/get-file”
UPLOAD_API = f”{API_BASE}/datalake/upload-file”
UPLOAD_STREAM_API = f”{API_BASE}/datalake/upload-file-stream”
LIST_FILES_API = f”{API_BASE}/list-files”

LOCAL_PG_HOST = “localhost”
LOCAL_PG_PORT = “5432”
LOCAL_PG_USER = “postgres”
LOCAL_PG_PASS = “redadmin”
LOCAL_PG_DB = “audit”

LOCAL_TEMP = r”D:\parquet_temp”
LOG_DIR = r”D:\parquet_logs”
HOSTNAME = socket.gethostname()

# –– What to process ––

SYSTEM = “riskserver”
MONTHS = [“202508”, “202509”, “202510”]

# –– Pipeline capacities (backpressure) ––

# Bounded by API pod capacity: 2 replicas of FastAPI, each with

# 8-16GB memory and 0.5-2 CPU. Big dumps (~20GB) stream through pod memory.

# Keep concurrent ops low so pods don’t OOM under load from this client.

MAX_DOWNLOADED_BUFFER = 5

# Max days restored but not yet parqueted (in DB)

# 2 = current processing + next pre-restored

MAX_RESTORED_BUFFER = 2

# How many parallel downloads within a day (detail + audit)

PARALLEL_DOWNLOADS_PER_DAY = 2

# Parallel uploads. API has 2 replicas; upload streams through pod memory too.

# 3 leaves headroom if another client is also using the API.

PARALLEL_UPLOADS = 3

# –– Download ––

DOWNLOAD_MAX_RETRIES = 5
DOWNLOAD_CONNECT_TIMEOUT = 30
DOWNLOAD_READ_TIMEOUT = 3600

# –– Upload ––

UPLOAD_MAX_RETRIES = 3
UPLOAD_RETRY_BACKOFF = 10         # seconds, multiplied by attempt number

# –– DB streaming (critical for 1MB rows) ––

DB_FETCH = 10                     # 10 rows * ~1MB = 10MB wire buffer
ROWS_PER_WRITE = 1000             # flush to parquet every 1000 rows

# –– Output format (DO NOT CHANGE - BlobFeeder compat) ––

ROW_GROUP_SIZE = 1000
MAX_FILE_SIZE_MB = 100

# –– Disk safety ––

MIN_DISK_FREE_GB = 100

# ================================

os.makedirs(LOCAL_TEMP, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f”riskserver_async_{datetime.now().strftime(’%Y%m%d_%H%M%S’)}.log”)
logging.basicConfig(
level=logging.INFO,
format=”%(asctime)s | %(levelname)s | %(message)s”,
handlers=[
logging.FileHandler(log_file, encoding=“utf-8”),
logging.StreamHandler()
]
)
log = logging.getLogger(“riskserver”)

# Shared state

lock = threading.Lock()
results = {
“success”: [],
“failed_download”: [],
“failed_restore”: [],
“failed_parquet”: [],
“failed_upload”: [],
}
stats = {“files”: 0, “rows”: 0, “partitions”: 0, “bytes_uploaded”: 0}

# –– Parquet schema ––

FLAGS_TYPE = pa.list_(pa.struct([
pa.field(“Name”, pa.string()),
pa.field(“Value”, pa.string()),
pa.field(“FieldValue”, pa.string()),
]))

SCHEMA = pa.schema([
pa.field(“AuditDate”, pa.string()),
pa.field(“ApplicationName”, pa.string()),
pa.field(“RedId”, pa.string()),
pa.field(“DealId”, pa.string()),
pa.field(“ElementaryClientId”, pa.string()),
pa.field(“BookingEntityId”, pa.string()),
pa.field(“ProductStructure”, pa.string()),
pa.field(“TypObj”, pa.string()),
pa.field(“RequestTs”, pa.timestamp(“ns”)),
pa.field(“ResponseTs”, pa.timestamp(“ns”)),
pa.field(“Request”, pa.string()),
pa.field(“Response”, pa.string()),
pa.field(“Flags”, FLAGS_TYPE),
])

# –– Queues (bounded for backpressure) ––

# Worklist: all (month, day) tuples to process

# downloaded_q: (month, day, date_str, detail_local, audit_local) after download

# restored_q: (month, day, date_str) after restore

# Bounded sizes enforce backpressure:

# - If downloaded_q is full, download worker blocks on put() -> natural throttle

# - If restored_q is full, restore worker blocks on put() -> natural throttle

downloaded_q = Queue(maxsize=MAX_DOWNLOADED_BUFFER)
restored_q = Queue(maxsize=MAX_RESTORED_BUFFER)

# Sentinel to signal stage shutdown (unique object - None would be ambiguous)

SHUTDOWN = object()

# Upload pool (async, non-blocking)

upload_pool = ThreadPoolExecutor(max_workers=PARALLEL_UPLOADS)

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

def disk_free_gb(path=“D:\”):
try:
import shutil
total, used, free = shutil.disk_usage(path)
return free / (1024**3)
except:
return 999

# ============ DOWNLOAD ============

def download_one(folder, filename, local_path):
“”“Download a single dump file with retry and HTTP Range resume.”””
url = f”{DOWNLOAD_API}?path={folder}/{filename}”
timeout = (DOWNLOAD_CONNECT_TIMEOUT, DOWNLOAD_READ_TIMEOUT)

```
for attempt in range(DOWNLOAD_MAX_RETRIES):
    try:
        resume_pos = os.path.getsize(local_path) if os.path.exists(local_path) else 0
        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"

        r = requests.get(url, stream=True, timeout=timeout, headers=headers)

        if r.status_code not in (200, 206):
            log.warning(f"    DL {filename} attempt {attempt+1}: HTTP {r.status_code}")
            if r.status_code != 206 and os.path.exists(local_path):
                os.remove(local_path)
            time.sleep(5 * (attempt + 1))
            continue

        if resume_pos > 0 and r.status_code == 206:
            mode = "ab"
        else:
            mode = "wb"
            if os.path.exists(local_path):
                os.remove(local_path)

        with open(local_path, mode) as f:
            for chunk in r.iter_content(chunk_size=16 * 1024 * 1024):
                if chunk:
                    f.write(chunk)

        if os.path.getsize(local_path) < 500:
            os.remove(local_path)
            return False

        if attempt > 0:
            log.info(f"    DL {filename} succeeded on attempt {attempt+1}")
        return True

    except (requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.Timeout) as e:
        got = os.path.getsize(local_path) if os.path.exists(local_path) else 0
        log.warning(f"    DL {filename} attempt {attempt+1}/{DOWNLOAD_MAX_RETRIES} "
                    f"failed ({got/(1024**2):.0f}MB so far): {str(e)[:200]}")
        time.sleep(min(60, 10 * (attempt + 1)))
        continue
    except Exception as e:
        log.error(f"    DL {filename} unexpected error: {e}")
        if os.path.exists(local_path):
            os.remove(local_path)
        return False

log.error(f"    DL {filename} FAILED after {DOWNLOAD_MAX_RETRIES} attempts")
return False
```

def download_day(month, day):
“”“Download detail + audit dumps for one day. Returns paths or None on failure.”””
date_str = f”{month}{day:02d}”
folder = f”dumps_{month}”
detail_file = f”{SYSTEM}_{date_str}.dump”
audit_file = f”{SYSTEM}*raw_audit*{date_str}.dump”
detail_local = os.path.join(LOCAL_TEMP, detail_file)
audit_local = os.path.join(LOCAL_TEMP, audit_file)

```
with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS_PER_DAY) as pool:
    fd = pool.submit(download_one, folder, detail_file, detail_local)
    fa = pool.submit(download_one, folder, audit_file, audit_local)
    dok = fd.result()
    aok = fa.result()

if dok and aok:
    dsz = os.path.getsize(detail_local) / (1024**2)
    asz = os.path.getsize(audit_local) / (1024**2)
    log.info(f"[DL ] {date_str} done: detail={dsz:.0f}MB audit={asz:.0f}MB")
    return (detail_local, audit_local)

with lock:
    if not dok:
        results["failed_download"].append(f"{SYSTEM}_{date_str}_detail")
    if not aok:
        results["failed_download"].append(f"{SYSTEM}_{date_str}_audit")
log.warning(f"[DL ] {date_str} FAILED (detail={dok} audit={aok})")

for p in [detail_local, audit_local]:
    if os.path.exists(p):
        os.remove(p)
return None
```

# ============ RESTORE ============

def restore_one(dump_path, label):
env = os.environ.copy()
env[“PGPASSWORD”] = LOCAL_PG_PASS
cmd = f’pg_restore -h {LOCAL_PG_HOST} -p {LOCAL_PG_PORT} -U {LOCAL_PG_USER} -d {LOCAL_PG_DB} –no-owner -a “{dump_path}”’
ret = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
if ret.returncode != 0:
stderr = ret.stderr.strip()
if “errors ignored on restore” in stderr:
if “duplicate key” in stderr:
log.warning(f”    Restore {label}: partition already populated”)
return True
if “does not exist” in stderr or “no matching” in stderr:
log.warning(f”    Restore {label}: partition empty/missing”)
return False
log.error(f”    Restore {label} FAILED: {stderr[:300]}”)
return False
return True

def restore_day(date_str, detail_local, audit_local):
“”“Restore detail + audit in parallel. Always deletes dumps after.”””
with ThreadPoolExecutor(max_workers=2) as pool:
fd = pool.submit(restore_one, detail_local, f”{SYSTEM}_{date_str}*detail”)
fa = pool.submit(restore_one, audit_local, f”{SYSTEM}*{date_str}_audit”)
dok = fd.result()
aok = fa.result()

```
# Delete dumps to free disk, regardless of restore success
for p in [detail_local, audit_local]:
    if os.path.exists(p):
        os.remove(p)

if dok and aok:
    log.info(f"[RST] {date_str} done")
    return True

with lock:
    results["failed_restore"].append(f"{SYSTEM}_{date_str}")
log.error(f"[RST] {date_str} FAILED")
return False
```

# ============ UPLOAD ============

def upload_file(local_path, remote_path):
“”“Upload a single parquet file with retry. Only deletes local file on success.”””
if not os.path.exists(local_path):
log.warning(f”[UP ] file gone before upload: {local_path}”)
return False

```
file_size = os.path.getsize(local_path)

for attempt in range(UPLOAD_MAX_RETRIES):
    try:
        if file_size > 100 * 1024 * 1024:
            with open(local_path, "rb") as f:
                r = requests.post(UPLOAD_STREAM_API, params={"path": remote_path},
                                  data=f, timeout=1800)
        else:
            with open(local_path, "rb") as f:
                r = requests.post(UPLOAD_API, params={"path": remote_path},
                                  data=f.read(), timeout=600)
        if r.status_code == 200:
            with lock:
                stats["bytes_uploaded"] += file_size
            try:
                os.remove(local_path)
            except Exception as e:
                log.warning(f"[UP ] failed to delete {local_path} after upload: {e}")
            if attempt > 0:
                log.info(f"[UP ] {remote_path} succeeded on attempt {attempt+1}")
            return True

        log.warning(f"[UP ] attempt {attempt+1}/{UPLOAD_MAX_RETRIES} HTTP {r.status_code} for {remote_path}")

    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError) as e:
        log.warning(f"[UP ] attempt {attempt+1}/{UPLOAD_MAX_RETRIES} transient error {remote_path}: {str(e)[:150]}")
    except Exception as e:
        log.error(f"[UP ] attempt {attempt+1}/{UPLOAD_MAX_RETRIES} error {remote_path}: {e}")

    # Backoff before retry
    if attempt < UPLOAD_MAX_RETRIES - 1:
        time.sleep(UPLOAD_RETRY_BACKOFF * (attempt + 1))

# All attempts failed - leave file on disk for manual recovery
log.error(f"[UP ] FAIL {remote_path} after {UPLOAD_MAX_RETRIES} attempts, file kept at {local_path}")
return False
```

def upload_async(local_path, remote_path):
“”“Fire-and-forget upload. Result tracked via future list.”””
fut = upload_pool.submit(upload_file, local_path, remote_path)
with lock:
pending_uploads.append((fut, remote_path))

pending_uploads = []

def flush_uploads():
“”“Wait for all pending uploads to finish.”””
global pending_uploads
with lock:
current = list(pending_uploads)
pending_uploads = []
failed = 0
for fut, path in current:
try:
if not fut.result(timeout=1800):
failed += 1
with lock:
results[“failed_upload”].append(path)
except Exception as e:
failed += 1
log.error(f”[UP ] future error {path}: {e}”)
with lock:
results[“failed_upload”].append(path)
if failed:
log.warning(f”[UP ] {failed} uploads failed”)

# ============ CHECK EXISTING ============

def has_existing_files(app, yyyymm, biz_day):
“”“Check if target path already has files.
- True if listing succeeded and found files
- False if listing succeeded and found no files
- False if listing 500’d because the directory does not exist yet (first upload)
- True if listing truly failed (API unreachable, genuine server error) - fail-safe to _new
“””
path = f”v2/{app}/{yyyymm}/businessDay={biz_day}”
try:
r = requests.get(LIST_FILES_API, params={“path”: path}, timeout=30)
if r.status_code == 200:
return len(r.json().get(“files”, [])) > 0
if r.status_code == 500:
# API wraps Azure errors in 500 with the error message in body.
# Missing directory = first-ever upload = legitimately no files.
body = (r.text or “”).lower()
not_found_markers = (
“pathnotfound”, “path not found”,
“filenotfound”, “file not found”,
“does not exist”, “doesn’t exist”, “not found”,
“notfound”, “sourcepathnotfound”,
)
if any(m in body for m in not_found_markers):
return False
log.warning(f”[EXIST] list-files HTTP 500 for {path}: {r.text[:200]}, assuming exists”)
return True
log.warning(f”[EXIST] list-files HTTP {r.status_code} for {path}, assuming exists”)
return True
except Exception as e:
log.warning(f”[EXIST] list-files error for {path}: {e}, assuming exists”)
return True

# ============ XML PARSING ============

def parse_flags(response_xml):
if not response_xml:
return [{“Name”: None, “Value”: None, “FieldValue”: None}]
try:
data = response_xml.encode() if isinstance(response_xml, str) else response_xml
root = etree.fromstring(data)
flags = [
{“Name”: f.get(“Name”, “”), “Value”: f.get(“Value”, “”), “FieldValue”: None}
for f in root.iter(“Flag”)
]
return flags if flags else [{“Name”: None, “Value”: None, “FieldValue”: None}]
except Exception:
return [{“Name”: None, “Value”: None, “FieldValue”: None}]

# ============ PARQUET WRITING ============

def make_writer(parquet_dir, date_str):
guid = str(uuid.uuid4())
filename = f”data_{SYSTEM}*{date_str}*histmig*{HOSTNAME}*{guid}.snappy.parquet”
filepath = os.path.join(parquet_dir, filename)
writer = pq.ParquetWriter(
filepath, SCHEMA,
compression=“snappy”,
use_deprecated_int96_timestamps=True,
)
return writer, filepath

def build_table(rows):
return pa.table({
“AuditDate”: pa.array([r[0] for r in rows], type=pa.string()),
“ApplicationName”: pa.array([r[1] for r in rows], type=pa.string()),
“RedId”: pa.array([r[2] for r in rows], type=pa.string()),
“DealId”: pa.array([r[3] for r in rows], type=pa.string()),
“ElementaryClientId”: pa.array([r[4] for r in rows], type=pa.string()),
“BookingEntityId”: pa.array([r[5] for r in rows], type=pa.string()),
“ProductStructure”: pa.array([r[6] for r in rows], type=pa.string()),
“TypObj”: pa.array([r[7] for r in rows], type=pa.string()),
“RequestTs”: pa.array([r[8] for r in rows], type=pa.timestamp(“ns”)),
“ResponseTs”: pa.array([r[9] for r in rows], type=pa.timestamp(“ns”)),
“Request”: pa.array([r[10] for r in rows], type=pa.string()),
“Response”: pa.array([r[11] for r in rows], type=pa.string()),
“Flags”: pa.array([r[12] for r in rows], type=FLAGS_TYPE),
}, schema=SCHEMA)

def process_partition(month, day, upload_base):
“”“Stream a restored partition to parquet, uploading files as they complete.”””
date_str = f”{month}{day:02d}”
detail_table = f”redservice.t_raw_detail_audit_{SYSTEM}*{month}*{date_str}”
audit_table = f”redservice.t_raw_audit_{SYSTEM}*{month}*{date_str}”

```
conn = None
cursor = None
writer = None
cur_file = None
pq_dir = os.path.join(LOCAL_TEMP, f"{SYSTEM}_{date_str}_pq")
file_count = 0
row_count = 0

try:
    conn = psycopg2.connect(
        host=LOCAL_PG_HOST, port=LOCAL_PG_PORT,
        user=LOCAL_PG_USER, password=LOCAL_PG_PASS,
        dbname=LOCAL_PG_DB,
    )
    conn.set_session(autocommit=False)
    cursor = conn.cursor(name=f"pq_{SYSTEM}_{date_str}")
    cursor.itersize = DB_FETCH

    query = f"""
        SELECT
            TO_CHAR(a.response_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD'),
            a.application_name, a.red_id, a.deal_id,
            a.elementary_client_id, a.booking_entity_id,
            a.product_structure, a.typ_obj,
            a.request_ts, a.response_ts,
            d.request, d.response
        FROM {audit_table} a
        JOIN {detail_table} d ON a.detail_id = d.detail_id
    """
    cursor.execute(query)

    os.makedirs(pq_dir, exist_ok=True)

    buf = []
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

    last_log_time = time.time()
    last_log_rows = 0

    while True:
        db_rows = cursor.fetchmany(DB_FETCH)
        if not db_rows:
            break

        for row in db_rows:
            flags = parse_flags(row[11])
            buf.append((
                row[0] or "",
                (row[1] or "").lower().replace(":", "_"),
                row[2] or "", row[3] or "", row[4] or "",
                row[5] or "", row[6] or "", row[7] or "",
                row[8], row[9],
                row[10] or "", row[11] or "",
                flags,
            ))

            if len(buf) >= ROWS_PER_WRITE:
                if writer is None:
                    file_count += 1
                    writer, cur_file = make_writer(pq_dir, date_str)

                writer.write_table(build_table(buf), row_group_size=ROW_GROUP_SIZE)
                row_count += len(buf)
                buf = []

                # Progress log every 2 minutes
                now = time.time()
                if now - last_log_time >= 120:
                    rate = (row_count - last_log_rows) / max(now - last_log_time, 1)
                    log.info(f"[PQ ] {date_str}: {row_count} rows | {rate:.0f} rows/sec | file {file_count}")
                    last_log_time = now
                    last_log_rows = row_count

                # Check file size - close and upload if over threshold
                try:
                    cur_size = os.path.getsize(cur_file)
                except:
                    cur_size = 0

                if cur_size >= max_bytes:
                    writer.close()
                    writer = None
                    final_sz = os.path.getsize(cur_file)
                    upload_async(cur_file, f"{upload_base}/{os.path.basename(cur_file)}")
                    log.info(f"[PQ ] {date_str}: file {file_count} closed ({final_sz/(1024*1024):.0f} MB)")
                    cur_file = None

    # Final flush
    if buf:
        if writer is None:
            file_count += 1
            writer, cur_file = make_writer(pq_dir, date_str)
        writer.write_table(build_table(buf), row_group_size=ROW_GROUP_SIZE)
        row_count += len(buf)
        buf = []

    if writer:
        writer.close()
        writer = None
        if cur_file and os.path.exists(cur_file):
            final_sz = os.path.getsize(cur_file)
            upload_async(cur_file, f"{upload_base}/{os.path.basename(cur_file)}")
            log.info(f"[PQ ] {date_str}: file {file_count} closed ({final_sz/(1024*1024):.0f} MB) (final)")
            cur_file = None

    return file_count, row_count

except Exception as e:
    log.error(f"[PQ ] {date_str} error: {e}")
    return file_count, row_count  # return partial progress, not (0, 0)

finally:
    # Best-effort cleanup - never re-raise from here
    if writer is not None:
        try:
            writer.close()
        except Exception as e:
            log.warning(f"[PQ ] {date_str} writer.close() in finally: {e}")
    if cursor is not None:
        try:
            cursor.close()
        except Exception as e:
            log.warning(f"[PQ ] {date_str} cursor.close() in finally: {e}")
    if conn is not None:
        try:
            conn.rollback()  # release any open transaction
        except Exception:
            pass
        try:
            conn.close()
        except Exception as e:
            log.warning(f"[PQ ] {date_str} conn.close() in finally: {e}")
    # Try to remove the temp dir - may have stale files if uploads are pending
    try:
        if os.path.isdir(pq_dir):
            # Only rmdir if empty (files still there = uploads pending or failed)
            remaining = os.listdir(pq_dir)
            if not remaining:
                os.rmdir(pq_dir)
            else:
                log.info(f"[PQ ] {date_str} pq_dir keeps {len(remaining)} file(s) "
                         f"(uploads pending/failed)")
    except Exception:
        pass
```

def truncate_tables(month, date_str):
try:
conn = psycopg2.connect(
host=LOCAL_PG_HOST, port=LOCAL_PG_PORT,
user=LOCAL_PG_USER, password=LOCAL_PG_PASS,
dbname=LOCAL_PG_DB,
)
cur = conn.cursor()
cur.execute(f”TRUNCATE redservice.t_raw_detail_audit_{SYSTEM}*{month}*{date_str}”)
cur.execute(f”TRUNCATE redservice.t_raw_audit_{SYSTEM}*{month}*{date_str}”)
conn.commit()
cur.close()
conn.close()
except Exception as e:
log.error(f”[TRN] {date_str} error: {e}”)

# ============ PIPELINE WORKERS ============

def download_worker(worklist, t_start):
“”“Stage 1: download days. Blocks if downloaded_q is full (backpressure).”””
log.info(”[DL ] worker started”)
for (month, day) in worklist:
# Disk safety check
while disk_free_gb() < MIN_DISK_FREE_GB:
log.warning(f”[DL ] LOW DISK: {disk_free_gb():.0f} GB free. Waiting 30s…”)
time.sleep(30)

```
    date_str = f"{month}{day:02d}"
    log.info(f"[DL ] starting {date_str}")

    result = download_day(month, day)
    if result is None:
        continue

    detail_local, audit_local = result
    # Blocks if queue full (i.e., 5 days already waiting to be restored)
    downloaded_q.put((month, day, date_str, detail_local, audit_local))
    log.info(f"[DL ] {date_str} -> restore queue (qsize={downloaded_q.qsize()})")

# Signal restore worker that no more downloads will come
downloaded_q.put(SHUTDOWN)
log.info("[DL ] worker done")
```

def restore_worker(t_start):
“”“Stage 2: restore days from downloaded_q into PG. Blocks if restored_q is full.”””
log.info(”[RST] worker started”)
while True:
item = downloaded_q.get()
if item is SHUTDOWN:
restored_q.put(SHUTDOWN)
break

```
    month, day, date_str, detail_local, audit_local = item
    log.info(f"[RST] starting {date_str}")

    ok = restore_day(date_str, detail_local, audit_local)
    if not ok:
        continue

    # Blocks if queue full (= 2 partitions already in DB)
    restored_q.put((month, day, date_str))
    log.info(f"[RST] {date_str} -> parquet queue (qsize={restored_q.qsize()})")

log.info("[RST] worker done")
```

def parquet_worker(t_start):
“”“Stage 3: serial parquet processing of restored partitions.”””
log.info(”[PQ ] worker started”)
while True:
item = restored_q.get()
if item is SHUTDOWN:
break

```
    month, day, date_str = item
    year = int(month[:4])
    mon = int(month[4:])
    biz_day = f"{year}-{mon:02d}-{day:02d}"

    existing = has_existing_files(SYSTEM, month, biz_day)
    if existing:
        upload_base = f"v2/{SYSTEM}/{month}/businessDay={biz_day}_new"
        log.info(f"[PQ ] {date_str}: existing files -> _new")
    else:
        upload_base = f"v2/{SYSTEM}/{month}/businessDay={biz_day}"

    t0 = time.time()
    log.info(f"[PQ ] starting {date_str}")
    fc, rc = process_partition(month, day, upload_base)
    dt = time.time() - t0

    if fc > 0 and rc > 0:
        with lock:
            stats["files"] += fc
            stats["rows"] += rc
            stats["partitions"] += 1
            results["success"].append(f"{SYSTEM}_{date_str}")
        rate = rc / max(dt, 1)
        log.info(f"[PQ ] DONE {date_str} | {fc} files | {rc} rows | {dt/60:.1f} min | {rate:.0f} rows/sec")
    else:
        with lock:
            results["failed_parquet"].append(f"{SYSTEM}_{date_str}")
        log.error(f"[PQ ] FAIL {date_str} (fc={fc}, rc={rc})")

    # Truncate AFTER parquet done - frees DB space for next pre-restored partition
    truncate_tables(month, date_str)
    log.info(f"[TRN] {date_str} done")

    # Overall progress
    elapsed = time.time() - t_start
    with lock:
        bytes_up = stats["bytes_uploaded"]
        parts = stats["partitions"]
        fls = stats["files"]
        rws = stats["rows"]
    log.info(f"### PROGRESS: {parts} parts | {fls} files | "
             f"{rws} rows | {bytes_up/(1024**3):.1f} GB up | "
             f"{elapsed/3600:.1f} hrs | Disk: {disk_free_gb():.0f} GB free | "
             f"DLq:{downloaded_q.qsize()} RSTq:{restored_q.qsize()}")

log.info("[PQ ] worker done")
```

# ============ MAIN ============

def build_worklist():
“”“Return list of (month, day) tuples in order.”””
worklist = []
for month in MONTHS:
year = int(month[:4])
mon = int(month[4:])
for day in get_days(year, mon):
worklist.append((month, day))
return worklist

def main():
t_start = time.time()

```
log.info("=" * 60)
log.info(f"  RISKSERVER ASYNC PIPELINE | Host: {HOSTNAME}")
log.info(f"  Months: {MONTHS}")
log.info(f"  Buffers: downloaded={MAX_DOWNLOADED_BUFFER} restored={MAX_RESTORED_BUFFER}")
log.info(f"  DB fetch: {DB_FETCH} rows | Write every: {ROWS_PER_WRITE} rows")
log.info(f"  Row group: {ROW_GROUP_SIZE} | Max file: {MAX_FILE_SIZE_MB}MB")
log.info(f"  Uploads: {PARALLEL_UPLOADS} parallel")
log.info(f"  Disk free: {disk_free_gb():.1f} GB")
log.info(f"  Log: {log_file}")
log.info("=" * 60)

worklist = build_worklist()
log.info(f"  Total days in worklist: {len(worklist)}")

# Start pipeline stages as separate threads
dl_thread = threading.Thread(target=download_worker, args=(worklist, t_start), name="download")
rst_thread = threading.Thread(target=restore_worker, args=(t_start,), name="restore")
pq_thread = threading.Thread(target=parquet_worker, args=(t_start,), name="parquet")

dl_thread.start()
rst_thread.start()
pq_thread.start()

# Wait for pipeline to drain
pq_thread.join()
log.info("[MAIN] parquet stage done")

rst_thread.join()
log.info("[MAIN] restore stage done")
dl_thread.join()
log.info("[MAIN] download stage done")

# Wait for all in-flight uploads
log.info("[MAIN] waiting for uploads to complete...")
flush_uploads()
upload_pool.shutdown(wait=True)

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

sf = os.path.join(LOG_DIR, f"riskserver_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
with open(sf, "w") as f:
    f.write(f"Time: {elapsed/3600:.1f} hrs\n")
    f.write(f"Partitions: {stats['partitions']}\n")
    f.write(f"Files: {stats['files']}\n")
    f.write(f"Rows: {stats['rows']}\n")
    f.write(f"Uploaded: {up_gb:.2f} GB\n")
    for key in results:
        f.write(f"{key}: {results[key]}\n")
```

if **name** == “**main**”:
main()