SELECT 
  c.relname,
  c.reltuples::bigint as estimated_rows,
  pg_size_pretty(pg_total_relation_size(c.oid)) as total_size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'redservice'
  AND c.relname IN (
    't_raw_detail_audit_gold_202509_20250901',
    't_raw_detail_audit_xone_202509_20250901',
    't_raw_audit_gold_202509_20250901',
    't_raw_audit_xone_202509_20250901'
  )
ORDER BY c.relname;

-- Sample-based size analysis (safe on prod)
SELECT 
  'gold' as sys,
  COUNT(*) as sampled_rows,
  ROUND(AVG(LENGTH(response))/1024.0, 1) as avg_resp_kb,
  ROUND(MAX(LENGTH(response))/1024.0, 1) as max_resp_kb,
  ROUND(AVG(LENGTH(request))/1024.0, 1) as avg_req_kb,
  ROUND(AVG((LENGTH(response) - LENGTH(REPLACE(response, '<Flag', ''))) / 5.0)) as avg_flags
FROM redservice.t_raw_detail_audit_gold_202509_20250901 TABLESAMPLE SYSTEM(0.1);

SELECT 
  'xone' as sys,
  COUNT(*) as sampled_rows,
  ROUND(AVG(LENGTH(response))/1024.0, 1) as avg_resp_kb,
  ROUND(MAX(LENGTH(response))/1024.0, 1) as max_resp_kb,
  ROUND(AVG(LENGTH(request))/1024.0, 1) as avg_req_kb,
  ROUND(AVG((LENGTH(response) - LENGTH(REPLACE(response, '<Flag', ''))) / 5.0)) as avg_flags
FROM redservice.t_raw_detail_audit_xone_202509_20250901 TABLESAMPLE SYSTEM(0.1);

SELECT 
  c.relname,
  c.reltuples::bigint as est_rows,
  pg_size_pretty(pg_total_relation_size(c.oid)) as size,
  pg_size_pretty(pg_relation_size(c.oid)) as table_only,
  pg_size_pretty(pg_indexes_size(c.oid)) as indexes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'redservice'
  AND c.relname ~ '^t_raw_detail_audit_(gold|xone)_20250[89]'
  AND c.relkind IN ('r', 'p')
ORDER BY c.relname
LIMIT 30;
SELECT 
  'gold' as sys,
  COUNT(*) as sampled,
  ROUND(AVG(LENGTH(response))/1024.0, 1) as avg_resp_kb,
  ROUND(MAX(LENGTH(response))/1024.0, 1) as max_resp_kb,
  ROUND(AVG(LENGTH(request))/1024.0, 1) as avg_req_kb
FROM redservice.t_raw_detail_audit_gold_202508_20250801 TABLESAMPLE SYSTEM(0.1)
UNION ALL
SELECT 
  'xone' as sys,
  COUNT(*) as sampled,
  ROUND(AVG(LENGTH(response))/1024.0, 1) as avg_resp_kb,
  ROUND(MAX(LENGTH(response))/1024.0, 1) as max_resp_kb,
  ROUND(AVG(LENGTH(request))/1024.0, 1) as avg_req_kb
FROM redservice.t_raw_detail_audit_xone_202508_20250801 TABLESAMPLE SYSTEM(0.1);

SELECT 
  'gold' as sys,
  ROUND(AVG(flag_count), 1) as avg_flags,
  MAX(flag_count) as max_flags,
  ROUND(AVG(CASE WHEN flag_count = 0 THEN 1 ELSE 0 END) * 100, 1) as pct_no_flags
FROM (
  SELECT (LENGTH(response) - LENGTH(REPLACE(response, '<Flag', ''))) / 5 as flag_count
  FROM redservice.t_raw_detail_audit_gold_202508_20250801 TABLESAMPLE SYSTEM(0.05)
) s
UNION ALL
SELECT 
  'xone' as sys,
  ROUND(AVG(flag_count), 1),
  MAX(flag_count),
  ROUND(AVG(CASE WHEN flag_count = 0 THEN 1 ELSE 0 END) * 100, 1)
FROM (
  SELECT (LENGTH(response) - LENGTH(REPLACE(response, '<Flag', ''))) / 5 as flag_count
  FROM redservice.t_raw_detail_audit_xone_202508_20250801 TABLESAMPLE SYSTEM(0.05)
) s;
