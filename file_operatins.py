SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 't_raw_detail_audit_riskserver_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC NULLS LAST
LIMIT 10;

SELECT 
    reltuples::bigint AS estimated_rows,
    pg_size_pretty(pg_total_relation_size('<schema>.<exact_table_name>')) AS total,
    pg_size_pretty((pg_total_relation_size('<schema>.<exact_table_name>') / NULLIF(reltuples, 0))::bigint) AS avg_per_row
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = '<schema>' AND c.relname = '<exact_table_name>';
