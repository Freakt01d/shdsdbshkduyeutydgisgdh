SELECT 
    pg_size_pretty(MAX(octet_length(request) + octet_length(COALESCE(response, '')))::bigint) AS max_payload,
    pg_size_pretty(AVG(octet_length(request) + octet_length(COALESCE(response, '')))::bigint) AS avg_payload,
    COUNT(*) FILTER (WHERE octet_length(request) + octet_length(COALESCE(response, '')) > 1000000) AS rows_over_1mb,
    COUNT(*) FILTER (WHERE octet_length(request) + octet_length(COALESCE(response, '')) > 10000000) AS rows_over_10mb
FROM redservice.t_raw_detail_audit_riskserver_202601_20260105
LIMIT 1;
