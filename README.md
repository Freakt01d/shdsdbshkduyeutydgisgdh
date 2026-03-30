SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename))
FROM pg_tables
WHERE schemaname = 'redservice'
AND tablename LIKE '%_202508'
ORDER BY tablename;
