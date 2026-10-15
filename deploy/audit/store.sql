-- Dedicated database only. The explicit installer runs this transaction as its administrator.
BEGIN;
CREATE ROLE aitrust_audit_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE ROLE aitrust_audit_client NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE SCHEMA aitrust_audit AUTHORIZATION aitrust_audit_owner;
REVOKE ALL ON SCHEMA aitrust_audit FROM PUBLIC;
SET LOCAL ROLE aitrust_audit_owner;
SET LOCAL search_path = pg_catalog, aitrust_audit;
ALTER DEFAULT PRIVILEGES IN SCHEMA aitrust_audit REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE TABLE aitrust_audit.control (
 singleton boolean PRIMARY KEY CHECK(singleton), installation uuid NOT NULL,
 locked boolean NOT NULL DEFAULT false, backup_token uuid, schema_contract jsonb NOT NULL);
CREATE TABLE aitrust_audit.tenants (
 tenant uuid PRIMARY KEY, policy jsonb NOT NULL, policy_hash text NOT NULL,
 next_seq bigint NOT NULL DEFAULT 1, head text NOT NULL DEFAULT repeat('0',64),
 base_seq bigint NOT NULL DEFAULT 0, base_hash text NOT NULL DEFAULT repeat('0',64), recovery jsonb);
CREATE TABLE aitrust_audit.principals (
 principal name PRIMARY KEY, tenant uuid NOT NULL REFERENCES aitrust_audit.tenants,
 capabilities text[] NOT NULL CHECK(capabilities <@ ARRAY['write','read','review','delete']::text[]));
CREATE FUNCTION aitrust_audit._tenant(capability text DEFAULT NULL) RETURNS uuid
 LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE t uuid; BEGIN
 IF (SELECT locked FROM control WHERE singleton) THEN RAISE EXCEPTION 'Audit unavailable' USING ERRCODE='42501'; END IF;
 SELECT tenant INTO t FROM principals WHERE principal=session_user
 AND (capability IS NULL OR capability=ANY(capabilities));
 IF t IS NULL THEN RAISE EXCEPTION 'Audit unavailable' USING ERRCODE='42501'; END IF;
 RETURN t; END $$;
CREATE TABLE aitrust_audit.records (
 tenant uuid NOT NULL REFERENCES aitrust_audit.tenants, id text NOT NULL,
 metadata jsonb NOT NULL, metadata_hash text NOT NULL,
 received_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 predecessor text, PRIMARY KEY(tenant,id));
CREATE TABLE aitrust_audit.events (
 tenant uuid NOT NULL REFERENCES aitrust_audit.tenants, seq bigint NOT NULL,
 material text NOT NULL, previous text NOT NULL, hash text NOT NULL,
 created_at timestamptz NOT NULL, PRIMARY KEY(tenant,seq));
CREATE INDEX audit_event_record ON aitrust_audit.events(tenant,((material::jsonb)->>'record'));
CREATE INDEX audit_record_expiry ON aitrust_audit.records(tenant,expires_at);
ALTER TABLE aitrust_audit.records ENABLE ROW LEVEL SECURITY;
ALTER TABLE aitrust_audit.records FORCE ROW LEVEL SECURITY;
CREATE POLICY own_records ON aitrust_audit.records USING(tenant=aitrust_audit._tenant()) WITH CHECK(tenant=aitrust_audit._tenant());
ALTER TABLE aitrust_audit.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE aitrust_audit.events FORCE ROW LEVEL SECURITY;
CREATE POLICY own_events ON aitrust_audit.events USING(tenant=aitrust_audit._tenant()) WITH CHECK(tenant=aitrust_audit._tenant());
-- Fixed, bounded subset of JSON Schema. No schema or SQL supplied by record writers.
CREATE FUNCTION aitrust_audit._shape(v jsonb,s jsonb,depth integer DEFAULT 0) RETURNS boolean
 LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE typ text; k text; child jsonb; i integer; n numeric; str text; BEGIN
 IF depth>12 OR v IS NULL OR s IS NULL THEN RETURN false; END IF;
 typ=jsonb_typeof(v);
 IF s ? 'const' AND v<>s->'const' THEN RETURN false; END IF;
 IF s ? 'enum' AND NOT (s->'enum' @> jsonb_build_array(v)) THEN RETURN false; END IF;
 IF s ? 'type' THEN
  IF jsonb_typeof(s->'type')='array' THEN
   IF NOT (s->'type' @> to_jsonb(ARRAY[CASE WHEN typ='number' AND v::numeric=trunc(v::numeric) THEN 'integer' ELSE typ END]))
    AND NOT (typ='number' AND s->'type' @> '["number"]'::jsonb) THEN RETURN false; END IF;
  ELSIF s->>'type'='integer' THEN
   IF typ<>'number' OR v::numeric<>trunc(v::numeric) THEN RETURN false; END IF;
  ELSIF s->>'type'<>typ THEN RETURN false; END IF;
 END IF;
 IF typ='object' THEN
  IF s->'additionalProperties'<>'false'::jsonb THEN RETURN false; END IF;
  FOR k IN SELECT jsonb_object_keys(v) LOOP
   IF NOT (s->'properties' ? k) OR NOT _shape(v->k,s->'properties'->k,depth+1) THEN RETURN false; END IF;
  END LOOP;
  FOR child IN SELECT value FROM jsonb_array_elements(coalesce(s->'required','[]')) LOOP
   IF NOT (v ? (child#>>'{}')) THEN RETURN false; END IF;
  END LOOP;
 ELSIF typ='array' THEN
  i=jsonb_array_length(v);
  IF i<coalesce((s->>'minItems')::integer,0) OR i>coalesce((s->>'maxItems')::integer,4096) THEN RETURN false; END IF;
  IF s->'uniqueItems'='true'::jsonb AND i<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(v)) THEN RETURN false; END IF;
  FOR child IN SELECT value FROM jsonb_array_elements(v) LOOP IF NOT _shape(child,s->'items',depth+1) THEN RETURN false; END IF; END LOOP;
 ELSIF typ='string' THEN
  str=v#>>'{}';
  IF octet_length(str)<>length(str) OR str ~ '[[:cntrl:]]' OR length(str)<coalesce((s->>'minLength')::integer,0)
    OR length(str)>coalesce((s->>'maxLength')::integer,256) THEN RETURN false; END IF;
  IF s ? 'pattern' AND str !~ (s->>'pattern') THEN RETURN false; END IF;
  IF s->>'format'='date-time' THEN PERFORM str::timestamptz; END IF;
  IF s->>'format'='uuid' THEN PERFORM str::uuid; END IF;
 ELSIF typ='number' THEN
  n=v::numeric;
  IF n<coalesce((s->>'minimum')::numeric,n) OR n>coalesce((s->>'maximum')::numeric,n) THEN RETURN false; END IF;
 END IF;
 RETURN true;
 EXCEPTION WHEN invalid_text_representation OR datetime_field_overflow OR invalid_datetime_format OR numeric_value_out_of_range THEN RETURN false;
 END $$;
CREATE FUNCTION aitrust_audit._valid(v jsonb) RETURNS boolean
 LANGUAGE plpgsql STABLE SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE tag jsonb; sig jsonb; span jsonb; total integer=0; BEGIN
 IF octet_length(replace(v::text,' ',''))>65536 OR NOT _shape(v,(SELECT schema_contract FROM control WHERE singleton)) THEN RETURN false; END IF;
 IF (SELECT count(DISTINCT value->>'code') FROM jsonb_array_elements(v->'tags'))<>jsonb_array_length(v->'tags')
 OR (SELECT count(DISTINCT value->>'code') FROM jsonb_array_elements(v->'abstentions'))<>jsonb_array_length(v->'abstentions')
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(v->'tags') a JOIN jsonb_array_elements(v->'abstentions') b ON a->>'code'=b->>'code')
 OR v->>'result_state'<>(CASE WHEN jsonb_array_length(v->'tags')>0 THEN 'FINDING' WHEN jsonb_array_length(v->'abstentions')>0 THEN 'UNCERTAIN' ELSE 'NO_FINDING' END) THEN RETURN false; END IF;
 FOR tag IN SELECT value FROM jsonb_array_elements(v->'tags') LOOP
  FOR sig IN SELECT value FROM jsonb_array_elements(tag->'signals') LOOP
   FOR span IN SELECT value FROM jsonb_array_elements(sig->'spans') LOOP
    total=total+1;
    IF (span->>0)::integer >= (span->>1)::integer OR (span->>1)::integer>(v->>'subject_char_len')::integer THEN RETURN false; END IF;
   END LOOP;
  END LOOP;
 END LOOP;
 RETURN total<=4096;
 END $$;
CREATE FUNCTION aitrust_audit._event(t uuid, action text, id text, detail jsonb) RETURNS void
 LANGUAGE plpgsql SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE n bigint; prev text; m text; h text; now_at timestamptz=clock_timestamp(); BEGIN
 SELECT next_seq,head INTO n,prev FROM tenants WHERE tenant=t FOR UPDATE;
 m=jsonb_build_object('sequence',n,'action',action,'record',id,'detail',detail,'principal',session_user,'at',now_at)::text;
 h=encode(sha256(decode(prev,'hex')||convert_to(m,'UTF8')),'hex');
 INSERT INTO events VALUES(t,n,m,prev,h,now_at);
 UPDATE tenants SET next_seq=n+1,head=h WHERE tenant=t;
 END $$;
CREATE FUNCTION aitrust_audit.policy() RETURNS jsonb
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 SELECT jsonb_build_object('policy',policy,'policy_sha256',policy_hash,'installation',installation) FROM tenants CROSS JOIN control WHERE tenant=_tenant() $$;
CREATE FUNCTION aitrust_audit.append(v jsonb, accepted_policy text, p_predecessor text DEFAULT NULL) RETURNS jsonb
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE t uuid=_tenant('write'); new_id text=v->>'source_record_sha256'; old records; days integer; at_time timestamptz=clock_timestamp(); BEGIN
 PERFORM 1 FROM tenants WHERE tenant=t FOR UPDATE;
 IF NOT _valid(v) OR accepted_policy IS DISTINCT FROM (SELECT policy_hash FROM tenants WHERE tenant=t) THEN RAISE EXCEPTION 'Audit admission refused' USING ERRCODE='22023'; END IF;
 SELECT * INTO old FROM records WHERE tenant=t AND id=new_id;
 IF FOUND THEN
  IF old.metadata=v AND old.predecessor IS NOT DISTINCT FROM p_predecessor AND old.expires_at>at_time THEN RETURN jsonb_build_object('id',new_id,'retry',true); END IF;
  RAISE EXCEPTION 'Audit admission refused' USING ERRCODE='22023';
 END IF;
 IF EXISTS(SELECT 1 FROM events WHERE tenant=t AND (material::jsonb->>'record')=new_id) THEN RAISE EXCEPTION 'Audit admission refused' USING ERRCODE='22023'; END IF;
 IF p_predecessor IS NOT NULL THEN
  SELECT * INTO old FROM records WHERE tenant=t AND id=p_predecessor AND expires_at>at_time;
  IF NOT FOUND OR old.metadata->>'subject_sha256'<>v->>'subject_sha256' OR old.metadata->>'subject_char_len'<>v->>'subject_char_len' OR old.metadata->'normalization_sha256'<>v->'normalization_sha256' THEN RAISE EXCEPTION 'Audit lineage refused' USING ERRCODE='22023'; END IF;
 END IF;
 SELECT (policy->>'record_days')::integer INTO days FROM tenants WHERE tenant=t;
 INSERT INTO records VALUES(t,new_id,v,encode(sha256(convert_to(v::text,'UTF8')),'hex'),at_time,at_time+make_interval(days=>days),p_predecessor);
 PERFORM _event(t,'append',new_id,jsonb_build_object('metadata_sha256',encode(sha256(convert_to(v::text,'UTF8')),'hex'),'predecessor',p_predecessor,'received_at',at_time,'expires_at',at_time+make_interval(days=>days)));
 RETURN jsonb_build_object('id',new_id,'retry',false);
 END $$;
CREATE FUNCTION aitrust_audit.review(id text, decision text, reason text) RETURNS jsonb
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE t uuid=_tenant('review'); BEGIN
 PERFORM 1 FROM tenants WHERE tenant=t FOR UPDATE;
 IF decision IS NULL OR reason IS NULL OR decision NOT IN ('agree','disagree','uncertain') OR reason NOT IN ('supported','missed_pattern','false_alarm','insufficient_context','other') OR NOT EXISTS(SELECT 1 FROM records WHERE tenant=t AND records.id=review.id AND expires_at>clock_timestamp()) THEN RAISE EXCEPTION 'Audit review refused' USING ERRCODE='22023'; END IF;
 PERFORM _event(t,'review',id,jsonb_build_object('decision',decision,'reason',reason));
 RETURN jsonb_build_object('record',id,'review_appended',true,'independent_label',false);
 END $$;
CREATE FUNCTION aitrust_audit.remove_record(id text) RETURNS jsonb
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE t uuid=_tenant('delete'); n integer; BEGIN
 PERFORM 1 FROM tenants WHERE tenant=t FOR UPDATE;
 DELETE FROM records WHERE tenant=t AND records.id=remove_record.id; GET DIAGNOSTICS n=ROW_COUNT;
 IF n>0 THEN PERFORM _event(t,'remove',id,'{}'); END IF;
 RETURN jsonb_build_object('removed',n,'older_backups_may_retain_metadata',true);
 END $$;
CREATE FUNCTION aitrust_audit.expire() RETURNS jsonb
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE t uuid=_tenant('delete'); expired_row record; n integer=0; cutoff timestamptz; boundary events; BEGIN
 PERFORM 1 FROM tenants WHERE tenant=t FOR UPDATE;
 FOR expired_row IN DELETE FROM records WHERE tenant=t AND expires_at<=clock_timestamp() RETURNING id LOOP
  n=n+1;PERFORM _event(t,'expire',expired_row.id,'{}');
 END LOOP;
 SELECT clock_timestamp()-make_interval(days=>(policy->>'audit_days')::integer) INTO cutoff FROM tenants WHERE tenant=t;
 SELECT * INTO boundary FROM events WHERE tenant=t AND created_at<cutoff AND seq<coalesce((SELECT min(seq) FROM events WHERE tenant=t AND created_at>=cutoff),9223372036854775807) AND seq<coalesce((SELECT min(e.seq) FROM events e JOIN records r ON r.tenant=e.tenant AND r.id=(e.material::jsonb->>'record') WHERE e.tenant=t AND e.material::jsonb->>'action'='append'),9223372036854775807) ORDER BY seq DESC LIMIT 1;
 IF FOUND THEN
  UPDATE tenants SET base_seq=boundary.seq,base_hash=boundary.hash WHERE tenant=t;
  DELETE FROM events WHERE tenant=t AND seq<=boundary.seq;
 END IF;
 RETURN jsonb_build_object('expired',n,'audit_prefix_may_be_pruned',true,'older_backups_may_retain_metadata',true);
 END $$;
-- Pages must share the same head; CLI refuses a concurrent mutation or expiring record.
CREATE FUNCTION aitrust_audit.snapshot(section text, after_key text DEFAULT '', expected_head text DEFAULT NULL) RETURNS jsonb
 LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,aitrust_audit,pg_temp AS $$
 DECLARE t uuid=_tenant('read'); result jsonb; h text; BEGIN
 SELECT head INTO h FROM tenants WHERE tenant=t;
 IF expected_head IS NOT NULL AND expected_head<>h THEN RAISE EXCEPTION 'Audit export changed' USING ERRCODE='40001'; END IF;
 IF section='header' THEN
 SELECT jsonb_build_object('format','organization-audit-export/v1','installation',installation,'tenant',t,'policy',policy,'policy_sha256',policy_hash,
 'head',head,'next_seq',next_seq,'base_seq',base_seq,'base_hash',base_hash,'recovery',recovery,'captured_at',clock_timestamp(),
 'active_count',(SELECT count(*) FROM records WHERE tenant=t AND expires_at>clock_timestamp()),
 'event_count',(SELECT count(*) FROM events WHERE tenant=t),'metadata_only',true,'independent_witness',false)
 INTO result FROM tenants CROSS JOIN control WHERE tenant=t;
 ELSIF section='records' THEN
 SELECT coalesce(jsonb_agg((to_jsonb(r)-'tenant')||jsonb_build_object('metadata_material',r.metadata::text) ORDER BY id),'[]') INTO result FROM
 (SELECT * FROM records WHERE tenant=t AND expires_at>clock_timestamp() AND id>after_key ORDER BY id LIMIT 10) r;
 ELSIF section='events' THEN
 IF after_key !~ '^[0-9]{1,18}$' THEN RAISE EXCEPTION 'Audit cursor refused' USING ERRCODE='22023'; END IF;
 SELECT coalesce(jsonb_agg(to_jsonb(e)-'tenant' ORDER BY seq),'[]') INTO result FROM
 (SELECT * FROM events WHERE tenant=t AND seq>after_key::bigint ORDER BY seq LIMIT 25) e;
 ELSE RAISE EXCEPTION 'Audit section refused' USING ERRCODE='22023'; END IF;
 RETURN result;
 END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA aitrust_audit FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA aitrust_audit FROM PUBLIC;
GRANT USAGE ON SCHEMA aitrust_audit TO aitrust_audit_client;
GRANT EXECUTE ON FUNCTION aitrust_audit.policy(),aitrust_audit.append(jsonb,text,text),aitrust_audit.review(text,text,text),aitrust_audit.remove_record(text),aitrust_audit.expire(),aitrust_audit.snapshot(text,text,text) TO aitrust_audit_client;
RESET ROLE;
-- Installer inserts the reviewed schema and installation identity before committing.
