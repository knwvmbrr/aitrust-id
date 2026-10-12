-- An independently applied synthetic profile, never a production migration.
\set ON_ERROR_STOP on
BEGIN;
DO $guard$
BEGIN
  IF current_database() <> 'postgres'
     OR current_setting('cluster_name') <> 'aitrust-metadata-synthetic'
     OR current_setting('listen_addresses') <> ''
     OR current_setting('data_directory') NOT LIKE '/tmp/aitrust-metadata-%/data'
     OR current_setting('server_version_num')::int NOT BETWEEN 180000 AND 189999
  THEN RAISE EXCEPTION 'Use the disposable PostgreSQL 18 synthetic cluster only'; END IF;
END
$guard$;
SET LOCAL ROLE ait_metadata_owner;
CREATE TABLE metadata_dev.invitations (
  digest bytea PRIMARY KEY CHECK (octet_length(digest)=32),
  capacity integer NOT NULL CHECK (capacity BETWEEN 1 AND 20),
  used integer NOT NULL DEFAULT 0 CHECK (used BETWEEN 0 AND capacity),
  expires_at timestamptz NOT NULL,
  retain_until timestamptz NOT NULL,
  revoked boolean NOT NULL DEFAULT false
);
CREATE TABLE metadata_dev.invitation_claims (
  withdrawal_digest bytea PRIMARY KEY CHECK (octet_length(withdrawal_digest)=32),
  invitation_digest bytea NOT NULL REFERENCES metadata_dev.invitations(digest),
  feedback_id uuid NOT NULL,
  retain_until timestamptz NOT NULL
);

CREATE FUNCTION metadata_dev.issue_invitation_synthetic(key_digest bytea, slots integer, lifetime_seconds integer)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE expiry timestamptz;
BEGIN
  IF key_digest IS NULL OR octet_length(key_digest)<>32 OR slots IS NULL OR slots NOT BETWEEN 1 AND 20
     OR lifetime_seconds IS NULL OR lifetime_seconds NOT BETWEEN 1 AND 86400
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invitation'; END IF;
  -- Bound retained issuance even across simultaneous maintenance sessions.
  PERFORM pg_advisory_xact_lock(18102026, 1);
  IF EXISTS (SELECT FROM metadata_dev.invitations WHERE digest=key_digest) THEN RETURN false; END IF;
  IF (SELECT count(*) FROM metadata_dev.invitations)>=100
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invitation'; END IF;
  expiry:=clock_timestamp()+make_interval(secs=>lifetime_seconds);
  INSERT INTO metadata_dev.invitations(digest,capacity,expires_at,retain_until)
  VALUES(key_digest,slots,expiry,expiry+interval '30 days');
  RETURN true;
END
$function$;

CREATE FUNCTION metadata_dev.revoke_invitation_synthetic(key_digest bytea)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE affected integer;
BEGIN
  IF key_digest IS NULL OR octet_length(key_digest)<>32
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invitation'; END IF;
  UPDATE metadata_dev.invitations SET revoked=true WHERE digest=key_digest AND NOT revoked;
  GET DIAGNOSTICS affected=ROW_COUNT;
  RETURN affected>0;
END
$function$;

CREATE FUNCTION metadata_dev.record_invited_synthetic(raw text, token_digest bytea, invitation_digest bytea)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE invite metadata_dev.invitations%ROWTYPE; claim metadata_dev.invitation_claims%ROWTYPE;
        identity uuid; retirement timestamptz;
BEGIN
  IF token_digest IS NULL OR octet_length(token_digest)<>32
     OR invitation_digest IS NULL OR octet_length(invitation_digest)<>32
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invited feedback'; END IF;
  SELECT * INTO STRICT invite FROM metadata_dev.invitations AS i WHERE i.digest=invitation_digest FOR UPDATE;
  IF invite.revoked OR invite.expires_at<=clock_timestamp()
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invited feedback'; END IF;
  -- Serialize cross-invitation attempts to bind the same withdrawal digest.
  PERFORM pg_advisory_xact_lock(hashtextextended(encode(token_digest,'hex'),0));
  SELECT * INTO claim FROM metadata_dev.invitation_claims AS c WHERE c.withdrawal_digest=token_digest;
  IF FOUND THEN
    IF claim.invitation_digest<>invitation_digest OR claim.retain_until<=clock_timestamp()
       OR NOT EXISTS (SELECT FROM metadata_dev.feedback AS f
                      WHERE f.id=claim.feedback_id AND f.withdrawal_digest=token_digest)
    THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invited feedback'; END IF;
    identity:=metadata_dev.record_synthetic(raw,token_digest);
    IF identity<>claim.feedback_id
    THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invited feedback'; END IF;
    RETURN identity;
  END IF;
  IF invite.used>=invite.capacity
     OR EXISTS (SELECT FROM metadata_dev.feedback WHERE withdrawal_digest=token_digest)
  THEN RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invited feedback'; END IF;
  identity:=metadata_dev.record_synthetic(raw,token_digest);
  SELECT expires_at INTO STRICT retirement FROM metadata_dev.feedback WHERE id=identity;
  INSERT INTO metadata_dev.invitation_claims(withdrawal_digest,invitation_digest,feedback_id,retain_until)
  VALUES(token_digest,invitation_digest,identity,retirement);
  UPDATE metadata_dev.invitations SET used=used+1 WHERE digest=invitation_digest;
  RETURN identity;
EXCEPTION WHEN OTHERS THEN
  -- The whole attempted insertion and quota change roll back together.
  RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Unsupported synthetic invited feedback';
END
$function$;

CREATE FUNCTION metadata_dev.prune_invitations_synthetic()
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
DECLARE affected integer;
BEGIN
  PERFORM metadata_dev.prune_synthetic();
  -- Keep bindings for valid invitations even when feedback has been withdrawn.
  DELETE FROM metadata_dev.invitation_claims AS c WHERE c.retain_until<clock_timestamp()
    AND EXISTS (SELECT FROM metadata_dev.invitations AS i WHERE i.digest=c.invitation_digest
                AND i.expires_at<=clock_timestamp() AND i.retain_until<clock_timestamp());
  DELETE FROM metadata_dev.invitations AS i WHERE i.retain_until<clock_timestamp()
    AND i.expires_at<=clock_timestamp() AND NOT EXISTS
    (SELECT FROM metadata_dev.invitation_claims AS c WHERE c.invitation_digest=i.digest);
  GET DIAGNOSTICS affected=ROW_COUNT;
  RETURN affected;
END
$function$;

REVOKE ALL ON metadata_dev.invitations,metadata_dev.invitation_claims FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION metadata_dev.record_synthetic(text,bytea) FROM ait_metadata_intake;
REVOKE ALL ON FUNCTION metadata_dev.issue_invitation_synthetic(bytea,integer,integer),
  metadata_dev.revoke_invitation_synthetic(bytea),metadata_dev.record_invited_synthetic(text,bytea,bytea),
  metadata_dev.prune_invitations_synthetic() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION metadata_dev.issue_invitation_synthetic(bytea,integer,integer),
  metadata_dev.revoke_invitation_synthetic(bytea),metadata_dev.prune_invitations_synthetic() TO ait_metadata_maintenance;
GRANT EXECUTE ON FUNCTION metadata_dev.record_invited_synthetic(text,bytea,bytea) TO ait_metadata_intake;
COMMIT;
