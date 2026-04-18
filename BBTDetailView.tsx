SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'redservice' 
AND tablename LIKE 't_raw_detail_audit%' 
LIMIT 20;

SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'redservice' 
AND tablename LIKE 't_raw_audit%' 
LIMIT 20;
