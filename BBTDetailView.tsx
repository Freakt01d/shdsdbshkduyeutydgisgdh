CREATE INDEX CONCURRENTLY idx_raw_audit_detail_id 
ON redservice.t_raw_audit (detail_id);


ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET checkpoint_timeout = '5min';
ALTER SYSTEM SET work_mem = '128MB';
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
SELECT pg_reload_conf();
