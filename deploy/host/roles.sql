\set ON_ERROR_STOP on
BEGIN;
SELECT format('CREATE ROLE %I NOLOGIN', role_name)
FROM (VALUES ('aitrust_owner'), ('aitrust_intake'), ('aitrust_reviewer'), ('aitrust_reader')) AS roles(role_name)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name)
\gexec
ALTER ROLE aitrust_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE aitrust_intake LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 8;
ALTER ROLE aitrust_reviewer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 4;
ALTER ROLE aitrust_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 4;
ALTER ROLE aitrust_reader SET default_transaction_read_only = on;
ALTER ROLE aitrust_reader SET statement_timeout = '15s';
COMMIT;
SELECT 'CREATE DATABASE aitrustid OWNER aitrust_owner'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'aitrustid')
\gexec
\connect aitrustid
BEGIN;
REVOKE ALL ON DATABASE aitrustid FROM PUBLIC;
GRANT CONNECT ON DATABASE aitrustid TO aitrust_intake, aitrust_reviewer, aitrust_reader;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION aitrust_owner;
GRANT USAGE ON SCHEMA app TO aitrust_intake, aitrust_reviewer, aitrust_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE aitrust_owner IN SCHEMA app REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
-- No blanket table permissions: migrations must grant per-table rights and
-- implement/test tenant policy before intake can receive real observations.
COMMIT;
