SELECT 
    relname,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_total_relation_size(c.oid) AS size_bytes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'redservice'
AND relname LIKE 't_raw_detail_audit_riskserver_%'
AND relkind = 'r'
AND pg_total_relation_size(c.oid) > 1000000
ORDER BY size_bytes DESC
LIMIT 5;

SELECT 
    COUNT(*) AS row_count,
    pg_size_pretty(AVG(octet_length(request) + octet_length(COALESCE(response, '')))::bigint) AS avg_payload,
    pg_size_pretty(MAX(octet_length(request) + octet_length(COALESCE(response, '')))::bigint) AS max_payload,
    pg_size_pretty(SUM(octet_length(request) + octet_length(COALESCE(response, '')))::bigint) AS total_payload
FROM redservice.t_raw_detail_audit_riskserver_202509_20250901;
