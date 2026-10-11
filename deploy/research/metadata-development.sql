-- Synthetic storage controls only. This is not a production migration.
\set ON_ERROR_STOP on
BEGIN;
DO $guard$
BEGIN
  IF current_database() <> 'postgres'
     OR current_setting('cluster_name') <> 'aitrust-metadata-synthetic'
     OR current_setting('listen_addresses') <> ''
     OR current_setting('data_directory') NOT LIKE '/tmp/aitrust-metadata-%/data'
     OR current_setting('server_version_num')::int NOT BETWEEN 180000 AND 189999
  THEN RAISE EXCEPTION 'Use the disposable PostgreSQL 18 synthetic cluster only';
  END IF;
END
$guard$;
CREATE ROLE ait_metadata_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT NOBYPASSRLS;
CREATE ROLE ait_metadata_intake NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT NOBYPASSRLS;
CREATE ROLE ait_metadata_review NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT NOBYPASSRLS;
CREATE ROLE ait_metadata_maintenance NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT NOBYPASSRLS;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA metadata_dev AUTHORIZATION ait_metadata_owner;
SET LOCAL ROLE ait_metadata_owner;
ALTER DEFAULT PRIVILEGES IN SCHEMA metadata_dev REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE TABLE metadata_dev.feedback (
  id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
  withdrawal_digest bytea NOT NULL UNIQUE CHECK (octet_length(withdrawal_digest) = 32),
  method_version text NOT NULL CHECK (method_version = 'context-v6'),
  reported_result text NOT NULL CHECK (reported_result IN ('pattern_found','no_pattern_found','unavailable','not_checked')),
  failure_category text NOT NULL CHECK (failure_category IN ('none_observed','unexpected_finding','possible_missed_pattern','could_not_check','unclear_result')),
  feedback text NOT NULL CHECK (feedback IN ('easy_to_understand','needs_clearer_explanation','hard_to_use','could_not_complete')),
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  expires_at timestamptz NOT NULL DEFAULT (clock_timestamp() + interval '30 days'),
  permission text NOT NULL DEFAULT 'synthetic_test_only' CHECK (permission = 'synthetic_test_only')
);
CREATE TABLE metadata_dev.withdrawals (
  withdrawal_digest bytea PRIMARY KEY CHECK (octet_length(withdrawal_digest) = 32),
  retain_until timestamptz NOT NULL DEFAULT (clock_timestamp() + interval '7 days')
);

CREATE FUNCTION metadata_dev.record_synthetic(body text, token_digest bytea)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE parsed json; item json; identity uuid; existing metadata_dev.feedback%ROWTYPE;
BEGIN
  IF body IS NULL OR octet_length(body) > 4096 OR token_digest IS NULL OR octet_length(token_digest) <> 32
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback'; END IF;
  BEGIN parsed := body::json;
  EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback';
  END;
  IF json_typeof(parsed) IS DISTINCT FROM 'object'
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback'; END IF;
  IF ARRAY(SELECT key FROM json_each(parsed) ORDER BY key) IS DISTINCT FROM ARRAY['feedback','format','permission','synthetic']
     OR json_typeof(parsed->'format') IS DISTINCT FROM 'string'
     OR parsed->>'format' IS DISTINCT FROM 'metadata-storage-development/v1'
     OR json_typeof(parsed->'synthetic') IS DISTINCT FROM 'boolean'
     OR parsed->>'synthetic' IS DISTINCT FROM 'true'
     OR json_typeof(parsed->'permission') IS DISTINCT FROM 'string'
     OR parsed->>'permission' IS DISTINCT FROM 'synthetic_test_only'
     OR json_typeof(parsed->'feedback') IS DISTINCT FROM 'object'
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback'; END IF;
  item := parsed->'feedback';
  IF ARRAY(SELECT key FROM json_each(item) ORDER BY key) IS DISTINCT FROM
       ARRAY['failure_category','feedback','method_version','purpose','reported_result','schema_version','sharing','tag']
     OR json_typeof(item->'schema_version') IS DISTINCT FROM 'number'
     OR item->>'schema_version' IS DISTINCT FROM '1'
     OR EXISTS (SELECT FROM json_each(item) WHERE key <> 'schema_version' AND json_typeof(value) IS DISTINCT FROM 'string')
     OR item->>'purpose' IS DISTINCT FROM 'PS_preview_usability_and_failure_review'
     OR item->>'tag' IS DISTINCT FROM 'PS'
     OR item->>'method_version' IS DISTINCT FROM 'context-v6'
     OR item->>'sharing' IS DISTINCT FROM 'local_file_not_submitted'
     OR item->>'reported_result' NOT IN ('pattern_found','no_pattern_found','unavailable','not_checked')
     OR item->>'failure_category' NOT IN ('none_observed','unexpected_finding','possible_missed_pattern','could_not_check','unclear_result')
     OR item->>'feedback' NOT IN ('easy_to_understand','needs_clearer_explanation','hard_to_use','could_not_complete')
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback'; END IF;
  -- Hash collisions only serialize unrelated requests; this is not identity.
  PERFORM pg_advisory_xact_lock(hashtextextended(encode(token_digest,'hex'),0));
  IF EXISTS (SELECT FROM metadata_dev.withdrawals WHERE withdrawal_digest=token_digest)
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback'; END IF;
  INSERT INTO metadata_dev.feedback(withdrawal_digest,method_version,reported_result,failure_category,feedback)
  VALUES(token_digest,item->>'method_version',item->>'reported_result',item->>'failure_category',item->>'feedback')
  ON CONFLICT (withdrawal_digest) DO NOTHING RETURNING id INTO identity;
  IF identity IS NOT NULL THEN RETURN identity; END IF;
  SELECT * INTO STRICT existing FROM metadata_dev.feedback WHERE withdrawal_digest=token_digest;
  IF existing.expires_at <= clock_timestamp()
     OR ROW(existing.method_version,existing.reported_result,existing.failure_category,existing.feedback)
        IS DISTINCT FROM ROW(item->>'method_version',item->>'reported_result',item->>'failure_category',item->>'feedback')
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback'; END IF;
  RETURN existing.id;
EXCEPTION WHEN OTHERS THEN
  -- json preserves duplicate keys but some escaped Unicode errors arise only
  -- when keys/values are read. Never reflect their input-bearing diagnostics.
  RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic feedback';
END
$function$;

CREATE FUNCTION metadata_dev.withdraw_synthetic(token_digest bytea)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE affected integer;
BEGIN
  IF token_digest IS NULL OR octet_length(token_digest) <> 32
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic withdrawal'; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended(encode(token_digest,'hex'),0));
  DELETE FROM metadata_dev.feedback WHERE withdrawal_digest=token_digest;
  GET DIAGNOSTICS affected = ROW_COUNT;
  -- Do not turn arbitrary nonexistent keys into unbounded retained records.
  IF affected > 0 THEN
    INSERT INTO metadata_dev.withdrawals(withdrawal_digest) VALUES(token_digest)
    ON CONFLICT (withdrawal_digest) DO NOTHING;
  END IF;
  RETURN affected > 0;
END
$function$;

CREATE FUNCTION metadata_dev.prune_synthetic()
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE affected integer;
BEGIN
  -- Apply pending instructions before removing them, including after a restore.
  DELETE FROM metadata_dev.feedback AS f
  WHERE f.expires_at <= clock_timestamp() OR EXISTS
    (SELECT FROM metadata_dev.withdrawals AS w WHERE w.withdrawal_digest=f.withdrawal_digest);
  GET DIAGNOSTICS affected = ROW_COUNT;
  DELETE FROM metadata_dev.withdrawals WHERE retain_until < clock_timestamp();
  RETURN affected;
END
$function$;

CREATE VIEW metadata_dev.review_counts WITH (security_barrier=true) AS
SELECT method_version, reported_result, failure_category, feedback, count(*) AS reports
FROM metadata_dev.feedback AS f
WHERE expires_at > clock_timestamp() AND NOT EXISTS
  (SELECT FROM metadata_dev.withdrawals AS w WHERE w.withdrawal_digest=f.withdrawal_digest)
GROUP BY method_version,reported_result,failure_category,feedback HAVING count(*) >= 5;

REVOKE ALL ON ALL TABLES IN SCHEMA metadata_dev FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA metadata_dev FROM PUBLIC;
GRANT USAGE ON SCHEMA metadata_dev TO ait_metadata_intake,ait_metadata_review,ait_metadata_maintenance;
GRANT EXECUTE ON FUNCTION metadata_dev.record_synthetic(text,bytea),metadata_dev.withdraw_synthetic(bytea) TO ait_metadata_intake;
GRANT SELECT ON metadata_dev.review_counts TO ait_metadata_review;
GRANT EXECUTE ON FUNCTION metadata_dev.prune_synthetic() TO ait_metadata_maintenance;
COMMIT;
