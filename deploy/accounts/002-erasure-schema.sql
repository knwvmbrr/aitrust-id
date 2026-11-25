-- Append-only migration identity. Do not reinterpret or replace migration001.
BEGIN;
SELECT pg_advisory_xact_lock(1095324737,2);
SET LOCAL ROLE ait_account_owner;
SELECT singleton FROM accounts.meta WHERE singleton=1 FOR UPDATE;
LOCK TABLE accounts.accounts IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF current_database() NOT IN ('ait_erasure_review','ait_erasure_restore')
    OR current_setting('cluster_name') <> 'aitrust-account-review'
    OR current_setting('listen_addresses') <> '' OR inet_server_addr() IS NOT NULL
    OR (SELECT count(*) FROM accounts.meta) <> 1
    OR (SELECT schema_sha FROM accounts.meta WHERE singleton=1)
       IS DISTINCT FROM '8bf9fe5a84f6cf13d5118a8fe8e18a27edeae3d2f980ceec0e34ca0500c5e159'
    OR (SELECT kdf FROM accounts.meta WHERE singleton=1)
       IS DISTINCT FROM 'scrypt-n32768-r8-p3-dk32/v1'
    OR COALESCE((SELECT clock<0 FROM accounts.meta WHERE singleton=1),true)
    OR (SELECT array_agg(tablename::text ORDER BY tablename) FROM pg_tables WHERE schemaname='accounts')
       IS DISTINCT FROM ARRAY['accounts','audit','cleanup','history','meta','rates','sessions']
    OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='accounts' AND c.relname IN ('erasure_state','erasure_journal'))
 THEN RAISE EXCEPTION 'Fresh explicit erasure migration required'; END IF;
END $$;
-- Only these two new review databases passed the guard above. No role or
-- membership is added. This read-only built-in identifies the actual backend.
RESET ROLE;
REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO ait_account_runtime;
SET LOCAL ROLE ait_account_owner;
CREATE TABLE accounts.erasure_state(
 singleton integer PRIMARY KEY CHECK(singleton=1),
 generation text NOT NULL CHECK(generation ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
 migration_sha text NOT NULL CHECK(migration_sha ~ '^[0-9a-f]{64}$'),
 clock bigint NOT NULL CHECK(clock>=0),
 head bigint NOT NULL CHECK(head>=0),
 floor bigint NOT NULL CHECK(floor>=0 AND floor<=head),
 floor_time bigint NOT NULL CHECK(floor_time>=0 AND floor_time<=clock),
 reserved_live integer NOT NULL CHECK(reserved_live>=0),
 retained_rows integer NOT NULL CHECK(retained_rows>=0),
 restored_from_sha text CHECK(restored_from_sha ~ '^[0-9a-f]{64}$'),
 reconciled_sha text CHECK(reconciled_sha ~ '^[0-9a-f]{64}$'),
 reconciled_at bigint CHECK(reconciled_at>0),
 CHECK(reserved_live+retained_rows<=4096), CHECK(retained_rows=head-floor),
 CHECK((reconciled_sha IS NULL)=(reconciled_at IS NULL)),
 CHECK(reconciled_sha IS NULL OR restored_from_sha IS NOT NULL));
CREATE TABLE accounts.erasure_journal(
 sequence bigint PRIMARY KEY CHECK(sequence>0),
 account_id text UNIQUE NOT NULL CHECK(account_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
 erased_at bigint NOT NULL CHECK(erased_at>0));
INSERT INTO accounts.erasure_state
 SELECT 1,'DATABASE_GENERATION','ERASURE_SOURCE_DIGEST',clock,0,0,0,
        (SELECT count(*) FROM accounts.accounts),0,NULL,NULL,NULL FROM accounts.meta WHERE singleton=1;

CREATE FUNCTION accounts.reserve_erasure_slot() RETURNS trigger
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE chosen bigint;
BEGIN
 -- Domain transactions already own meta before entering either trigger.
 SELECT clock INTO STRICT chosen FROM accounts.meta WHERE singleton=1;
 UPDATE accounts.erasure_state SET reserved_live=reserved_live+1,clock=chosen
  WHERE singleton=1 AND clock<=chosen AND reserved_live+retained_rows<4096;
 IF NOT FOUND THEN RAISE EXCEPTION 'Account erasure capacity unavailable'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION accounts.record_account_erasure() RETURNS trigger
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE chosen bigint; next_sequence bigint;
BEGIN
 SELECT clock INTO STRICT chosen FROM accounts.meta WHERE singleton=1;
 IF chosen<=0 THEN RAISE EXCEPTION 'Account erasure clock unavailable'; END IF;
 UPDATE accounts.erasure_state
  SET reserved_live=reserved_live-1,retained_rows=retained_rows+1,head=head+1,clock=chosen
  WHERE singleton=1 AND clock<=chosen AND reserved_live>0 RETURNING head INTO next_sequence;
 IF NOT FOUND THEN RAISE EXCEPTION 'Account erasure identity unavailable'; END IF;
 INSERT INTO accounts.erasure_journal VALUES(next_sequence,OLD.account_id,chosen);
 RETURN OLD;
END $$;
CREATE TRIGGER account_erasure_reservation AFTER INSERT ON accounts.accounts
 FOR EACH ROW EXECUTE FUNCTION accounts.reserve_erasure_slot();
CREATE TRIGGER account_erasure_record AFTER DELETE ON accounts.accounts
 FOR EACH ROW EXECUTE FUNCTION accounts.record_account_erasure();
REVOKE ALL ON accounts.erasure_state,accounts.erasure_journal FROM PUBLIC,ait_account_runtime;
REVOKE ALL ON FUNCTION accounts.reserve_erasure_slot(),accounts.record_account_erasure()
 FROM PUBLIC,ait_account_runtime;
-- Runtime may inspect the bounded migration/counter identity, never change it.
GRANT SELECT ON accounts.erasure_state TO ait_account_runtime;
COMMIT;
