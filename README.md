SELECT indexdef 
FROM pg_indexes 
WHERE schemaname = 'redservice' 
AND indexname = 'pk_raw_detail_audit';
