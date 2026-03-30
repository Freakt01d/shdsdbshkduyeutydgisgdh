SELECT '"redservice.' || tablename || '"'
FROM pg_tables
WHERE schemaname = 'redservice'
AND tablename LIKE '%_202508'
ORDER BY tablename;
