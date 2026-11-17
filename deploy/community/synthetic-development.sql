-- Disposable synthetic cluster only. No LOGIN roles, credentials or real data.
BEGIN;
CREATE ROLE ait_community_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE ait_community_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE ait_community_public NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE SCHEMA community_dev AUTHORIZATION ait_community_owner;
CREATE SCHEMA community_public_dev AUTHORIZATION ait_community_owner;
REVOKE ALL ON SCHEMA community_dev, community_public_dev FROM PUBLIC;
SET ROLE ait_community_owner;
CREATE TABLE community_dev.document (
 singleton integer PRIMARY KEY CHECK(singleton=1),
 payload jsonb NOT NULL CHECK((jsonb_typeof(payload)='object'
   AND payload->>'format'='community-workbench/v1'
   AND payload->'synthetic_only'='true'::jsonb
   AND jsonb_typeof(payload->'revision')='number'
   AND jsonb_typeof(payload->'clock')='number'
   AND octet_length(payload::text)<=262144) IS TRUE)
);
CREATE FUNCTION community_dev.compare_swap_synthetic(previous_base64 text, next_base64 text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE old_value jsonb; new_value jsonb; changed integer; key_name text;
BEGIN
 IF octet_length(previous_base64)>349528 OR octet_length(next_base64)>349528 THEN
   RAISE EXCEPTION 'Synthetic community transaction refused';
 END IF;
 old_value:=convert_from(decode(previous_base64,'base64'),'UTF8')::jsonb;
 new_value:=convert_from(decode(next_base64,'base64'),'UTF8')::jsonb;
 IF jsonb_typeof(new_value) IS DISTINCT FROM 'object'
    OR ARRAY(SELECT jsonb_object_keys(new_value) ORDER BY 1)<>ARRAY(SELECT jsonb_object_keys(old_value) ORDER BY 1) THEN
   RAISE EXCEPTION 'Synthetic community transaction refused';
 END IF;
 FOREACH key_name IN ARRAY ARRAY['clock','revision','public_sequence'] LOOP
   IF NOT coalesce((new_value->>key_name) ~ '^(0|[1-9][0-9]{0,15})$',false)
      OR NOT coalesce((old_value->>key_name) ~ '^(0|[1-9][0-9]{0,15})$',false) THEN
     RAISE EXCEPTION 'Synthetic community transaction refused';
   END IF;
 END LOOP;
 FOREACH key_name IN ARRAY ARRAY['actors','posts','reports','appeals','requests','rates'] LOOP
   IF jsonb_typeof(new_value->key_name) IS DISTINCT FROM 'object' THEN
     RAISE EXCEPTION 'Synthetic community transaction refused';
   END IF;
 END LOOP;
 IF jsonb_typeof(new_value->'events') IS DISTINCT FROM 'array'
    OR jsonb_typeof(new_value->'audit') IS DISTINCT FROM 'array'
    OR jsonb_typeof(new_value->'posting_paused') IS DISTINCT FROM 'boolean' THEN
   RAISE EXCEPTION 'Synthetic community transaction refused';
 END IF;
 IF (new_value->>'revision')::bigint<>(old_value->>'revision')::bigint+1
    OR (new_value->>'clock')::bigint<(old_value->>'clock')::bigint THEN
   RAISE EXCEPTION 'Synthetic community transaction refused';
 END IF;
 UPDATE community_dev.document SET payload=new_value WHERE singleton=1 AND payload=old_value;
 GET DIAGNOSTICS changed=ROW_COUNT;
 RETURN changed=1;
EXCEPTION WHEN others THEN
 RAISE EXCEPTION 'Synthetic community transaction refused';
END $$;
REVOKE ALL ON FUNCTION community_dev.compare_swap_synthetic(text,text) FROM PUBLIC;
GRANT USAGE ON SCHEMA community_dev TO ait_community_runtime;
GRANT SELECT ON community_dev.document TO ait_community_runtime;
GRANT EXECUTE ON FUNCTION community_dev.compare_swap_synthetic(text,text) TO ait_community_runtime;

CREATE FUNCTION community_public_dev.snapshot_synthetic(after_revision bigint DEFAULT 0, page_size integer DEFAULT 20)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE current_value jsonb; items jsonb; last_created bigint; amount integer;
BEGIN
 SELECT payload INTO STRICT current_value FROM community_dev.document WHERE singleton=1;
 IF after_revision<0 OR after_revision>(current_value->>'revision')::bigint OR page_size<1 OR page_size>20 THEN
   RAISE EXCEPTION 'Synthetic public projection refused';
 END IF;
 SELECT coalesce(jsonb_agg(item ORDER BY created),'[]'::jsonb),max(created),count(*) INTO items,last_created,amount FROM (
   SELECT created, jsonb_build_object(
     'id',key,'version',CASE WHEN (value->>'version') ~ '^[1-9][0-9]{0,15}$' THEN value->'version' ELSE '0'::jsonb END,
     'state',CASE WHEN value->>'state'='queued' THEN 'review_pending'
                  WHEN value->>'state' IN ('published','retracted','superseded') THEN value->>'state' ELSE 'retracted' END,
     'body',CASE WHEN value->>'state'='published' AND jsonb_typeof(value->'body')='string'
                     AND value->>'approved_by' IN ('mod-one','mod-two') THEN value->'body' ELSE 'null'::jsonb END,
     'official',value->>'owner'='official-one',
     'replacement',CASE WHEN (value->>'replacement') ~ '^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$' THEN value->'replacement' ELSE 'null'::jsonb END,
     'reply_to',CASE WHEN (value->>'reply_to') ~ '^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$' THEN value->'reply_to' ELSE 'null'::jsonb END,
     'reason_category',CASE WHEN value->>'public_reason' IN ('privacy','conduct','off_scope','incorrect','author_request','corrected','review_pending') THEN value->'public_reason' ELSE 'null'::jsonb END,
     'updated_at',CASE WHEN (value->>'updated_at') ~ '^[1-9][0-9]{0,15}$' THEN value->'updated_at' ELSE '0'::jsonb END,
     'appeal',CASE WHEN value->>'last_moderator' IN ('mod-one','mod-two') AND value->>'state'='retracted'
                  THEN to_jsonb('independent_review_requested_privately'::text) ELSE 'null'::jsonb END) AS item
   FROM (
     SELECT key,value,CASE WHEN (value->>'created') ~ '^[1-9][0-9]{0,15}$' THEN (value->>'created')::bigint ELSE 0 END AS created
     FROM jsonb_each(current_value->'posts')
     WHERE key ~ '^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
       AND jsonb_typeof(value)='object' AND value->'was_public'='true'::jsonb
       AND value->>'owner' IN ('user-one','user-two','official-one')
   ) eligible
   WHERE created>after_revision ORDER BY created LIMIT page_size
 ) selected;
 RETURN jsonb_build_object('format','community-public-projection/v1',
   'sequence',current_value->'public_sequence','items',items,
   'next_page',CASE WHEN amount=page_size THEN last_created ELSE NULL END,
   'cache_control','no-store','training_consent',false);
END $$;
REVOKE ALL ON FUNCTION community_public_dev.snapshot_synthetic(bigint,integer) FROM PUBLIC;
GRANT USAGE ON SCHEMA community_public_dev TO ait_community_public;
GRANT EXECUTE ON FUNCTION community_public_dev.snapshot_synthetic(bigint,integer) TO ait_community_public;
RESET ROLE;
COMMIT;
