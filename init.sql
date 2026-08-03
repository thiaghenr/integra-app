-- Run automatically by the postgres container on first initialization.
-- Ensures the integra_db database and integra user exist.

SELECT 'CREATE DATABASE integra_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'integra_db')\gexec

GRANT ALL PRIVILEGES ON DATABASE integra_db TO integra;
