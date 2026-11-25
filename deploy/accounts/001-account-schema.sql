-- Fresh dedicated database/schema only. No account data is dropped or replaced.
-- The operator creates database + NOLOGIN owner + runtime role separately.
BEGIN;
SELECT pg_advisory_xact_lock(1095324737,1);
DO $$ BEGIN
  IF current_database() NOT IN ('ait_account_review','ait_account_restore')
     OR current_setting('cluster_name') <> 'aitrust-account-review'
     OR current_setting('listen_addresses') <> ''
     OR inet_server_addr() IS NOT NULL
     OR EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='accounts')
  THEN RAISE EXCEPTION 'Fresh isolated account database required'; END IF;
END $$;
SET LOCAL ROLE ait_account_owner;
CREATE SCHEMA accounts AUTHORIZATION ait_account_owner;
REVOKE ALL ON SCHEMA accounts FROM PUBLIC;
CREATE TABLE accounts.meta(singleton integer PRIMARY KEY CHECK(singleton=1),clock bigint NOT NULL CHECK(clock>=0),kdf text NOT NULL CHECK(kdf='scrypt-n32768-r8-p3-dk32/v1'),schema_sha text NOT NULL CHECK(schema_sha ~ '^[0-9a-f]{64}$'));
CREATE TABLE accounts.accounts(account_id text PRIMARY KEY CHECK(account_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),username text UNIQUE NOT NULL CHECK(username ~ '^[a-z][a-z0-9_-]{2,31}$'),salt bytea NOT NULL CHECK(octet_length(salt)=16),password_hash bytea NOT NULL CHECK(octet_length(password_hash)=32),created_at bigint NOT NULL CHECK(created_at>0),history_enabled smallint NOT NULL CHECK(history_enabled IN(0,1)));
CREATE TABLE accounts.sessions(token_hash bytea PRIMARY KEY CHECK(octet_length(token_hash)=32),account_id text REFERENCES accounts.accounts(account_id) ON DELETE CASCADE,created_at bigint NOT NULL,seen_at bigint NOT NULL,expires_at bigint NOT NULL,CHECK(0<created_at AND created_at<=seen_at AND seen_at<expires_at));
CREATE TABLE accounts.history(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,account_id text NOT NULL REFERENCES accounts.accounts(account_id) ON DELETE CASCADE,event_id text NOT NULL CHECK(event_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),created_at bigint NOT NULL CHECK(created_at>0),payload bytea NOT NULL CHECK(octet_length(payload) BETWEEN 1 AND 4096),UNIQUE(account_id,event_id));
CREATE TABLE accounts.rates(rate_key text PRIMARY KEY CHECK(rate_key ~ '^[0-9a-f]{64}$'),until_at bigint NOT NULL CHECK(until_at>0),count integer NOT NULL CHECK(count BETWEEN 1 AND 60));
CREATE TABLE accounts.audit(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,account_id text,operation text NOT NULL CHECK(length(operation) BETWEEN 1 AND 40),at bigint NOT NULL CHECK(at>0));
CREATE TABLE accounts.cleanup(account_id text PRIMARY KEY,at bigint NOT NULL CHECK(at>0));
CREATE INDEX history_expiry ON accounts.history(created_at);
CREATE INDEX history_owner_sequence ON accounts.history(account_id,sequence);
CREATE INDEX sessions_expiry ON accounts.sessions(expires_at);
CREATE INDEX sessions_idle ON accounts.sessions(seen_at);
CREATE INDEX sessions_owner ON accounts.sessions(account_id);
CREATE INDEX rates_expiry ON accounts.rates(until_at);
INSERT INTO accounts.meta VALUES(1,0,'scrypt-n32768-r8-p3-dk32/v1','SOURCE_DIGEST');
REVOKE ALL ON ALL TABLES IN SCHEMA accounts FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA accounts FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA accounts REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
GRANT USAGE ON SCHEMA accounts TO ait_account_runtime;
GRANT SELECT ON accounts.meta TO ait_account_runtime;
GRANT UPDATE(clock) ON accounts.meta TO ait_account_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON accounts.accounts,accounts.sessions,accounts.history,accounts.rates,accounts.audit,accounts.cleanup TO ait_account_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA accounts TO ait_account_runtime;
COMMIT;
