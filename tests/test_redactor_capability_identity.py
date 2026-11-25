"""Identity-only controls with synthetic records; no Presidio/model execution."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

from protocol.replay_identity import digest, redactor_identity

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('capability_identity_under_test',ROOT/'services/anonymizer/replay_metadata.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class CapabilityIdentity(unittest.TestCase):
    def recognizer(self,record,name='SpacyRecognizer',module=m._SPACY_CLASS[0]):
        cls=type(name,(),{'__module__':module,'to_dict':lambda self:self.record})
        value=cls();value.record=record
        return value

    def record(self,values):
        return {'name':'SpacyRecognizer','version':'0.0.1','supported_language':'en',
                'supported_entities':values}

    def test_observed_nine_value_permutations_have_one_configuration_digest(self):
        # These are capability labels, not participant text or model observations.
        first=['EMAIL','PHONE_NUMBER','PERSON','NRP','LOCATION','AGE','DATE_TIME','ID','ORGANIZATION']
        second=['AGE','EMAIL','ORGANIZATION','PERSON','DATE_TIME','NRP','PHONE_NUMBER','ID','LOCATION']
        self.assertNotEqual(digest(self.record(first)),digest(self.record(second)))
        a=m._recognizer_record(self.recognizer(self.record(first)))
        b=m._recognizer_record(self.recognizer(self.record(second)))
        self.assertEqual(a,b);self.assertEqual(digest(a),digest(b))

    def test_membership_change_remains_a_different_digest(self):
        a=m._recognizer_record(self.recognizer(self.record(['EMAIL','PERSON'])))
        b=m._recognizer_record(self.recognizer(self.record(['EMAIL','PHONE_NUMBER'])))
        self.assertNotEqual(digest(a),digest(b))

    def test_patterns_context_and_deny_list_order_are_preserved(self):
        base=self.record(['PERSON','EMAIL'])
        base.update(patterns=[{'name':'first','score':0.8},{'name':'second','score':0.7}],
                    context=['beta','alpha'],deny_list=['two','one'])
        expected=m._recognizer_record(self.recognizer(copy.deepcopy(base)))
        for field in ('patterns','context','deny_list'):
            changed=copy.deepcopy(base);changed[field].reverse()
            actual=m._recognizer_record(self.recognizer(changed))
            self.assertEqual(actual[field],changed[field])
            self.assertNotEqual(digest(expected),digest(actual))

    def test_serialization_copies_capabilities_without_mutating_recognizer(self):
        values=['PERSON','EMAIL'];raw=self.record(values);raw['context']=['last','first']
        before=copy.deepcopy(raw);recognizer=self.recognizer(raw)
        actual=m._recognizer_record(recognizer)
        self.assertEqual(raw,before);self.assertIs(recognizer.record,raw)
        self.assertIsNot(actual,raw);self.assertIsNot(actual['supported_entities'],values)
        self.assertIs(actual['context'],raw['context'])

    def test_duplicate_or_invalid_capability_set_refuses(self):
        class String(str):pass
        class List(list):pass
        invalid=[None,True,False,[],(),{'EMAIL'},['EMAIL','EMAIL'],[''],['email'],
                 ['EMAIL\n'],['EMAIL ADDRESS'],['ÉMAIL'],[True],[None],[1],
                 ['A'*81],['K_'+str(x)for x in range(129)],[String('EMAIL')],List(['EMAIL'])]
        for values in invalid:
            with self.subTest(values=repr(values)):
                with self.assertRaises(ValueError):m._recognizer_record(self.recognizer(self.record(values)))

    def test_missing_capability_field_is_not_silently_accepted(self):
        raw=self.record(['EMAIL']);raw.pop('supported_entities')
        with self.assertRaises(ValueError):m._recognizer_record(self.recognizer(raw))

    def test_bounded_valid_capabilities_are_accepted(self):
        values=['K_'+str(x)for x in range(128)]
        self.assertEqual(m._recognizer_record(self.recognizer(self.record(values)))['supported_entities'],sorted(values))
        self.assertEqual(m._recognizer_record(self.recognizer(self.record(['A'*80])))['supported_entities'],['A'*80])

    def test_matching_display_name_does_not_normalize_a_foreign_class(self):
        raw=self.record(['PERSON','EMAIL'])
        for name,module in [('OtherRecognizer',m._SPACY_CLASS[0]),('SpacyRecognizer','other.publisher')]:
            actual=m._recognizer_record(self.recognizer(raw,name,module))
            self.assertEqual(actual,raw);self.assertIs(actual['supported_entities'],raw['supported_entities'])

    def test_pattern_recognizer_record_is_unchanged(self):
        raw={'name':'EmailRecognizer','supported_entity':'EMAIL','context':['b','a'],
             'patterns':[{'name':'second'},{'name':'first'}]}
        actual=m._recognizer_record(self.recognizer(raw,'PatternRecognizer','presidio_analyzer.pattern_recognizer'))
        self.assertEqual(actual,raw)

    def test_non_dictionary_serialization_refuses(self):
        with self.assertRaises(ValueError):m._recognizer_record(self.recognizer(['EMAIL']))

    def test_wire_envelope_retains_source_method_identity(self):
        names={'app':'services/anonymizer/app.py','model_loader':'services/anonymizer/model_identity.py',
            'requirements_lock':'services/anonymizer/requirements.lock','identity_contract':'protocol/replay_identity.py',
            'identity_builder':'services/anonymizer/replay_metadata.py'}
        sources={k:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for k,p in names.items()}
        self.assertNotEqual(sources['identity_builder'],'82b160ab375689bee61ec98f298ac472e9bed2d684a5b3ff12d7946b2e2eb2a5')
        config={'python':'3.12.14','platform_machine':'x86_64','model_manifest_sha256':'a'*64,
            'sources':sources,'dependencies':{'synthetic-test-only':'1.0'},
            'dependency_records':{'synthetic-test-only':'b'*64},'recognizer_configuration_sha256':'c'*64,'recognizer_count':1}
        value=redactor_identity(config)
        self.assertEqual(value['version'],'presidio-offline-en/v1')
        self.assertEqual(value['configuration']['sources']['identity_builder'],sources['identity_builder'])


if __name__=='__main__':unittest.main()
