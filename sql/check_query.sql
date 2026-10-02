SELECT pid,
       usename,
       state,
       query_start,
       now() - query_start AS duration,
       query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_start;

SELECT pid,
       usename,
       state,
       backend_start,
       query_start,
       query
FROM pg_stat_activity
ORDER BY backend_start;