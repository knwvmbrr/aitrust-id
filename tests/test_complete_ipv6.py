import importlib.util
from pathlib import Path
import pytest
# Execute the actual source helper without loading sealed model assets or a service.
# Live engine and whole-route integration are separately exercised on staging.
import ast,ipaddress,re
ROOT=Path(__file__).resolve().parents[1]
file=ROOT/'services/anonymizer/app.py'
tree=ast.parse(file.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='complete_ipv6_spans' or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['IPV6_TOKEN','IPV6_LABEL_TOKEN'] for t in n.targets)]
assert len(nodes)==3
scope={'ipaddress':ipaddress,'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),scope)
class Helper:complete_ipv6_spans=staticmethod(scope['complete_ipv6_spans'])
m=Helper()
@pytest.mark.parametrize('value',['2001:db8::27','2001:DB8::ABCD','::1','::','2001:db8:0:0:0:0:0:27','::ffff:192.0.2.42','2001:db8::192.0.2.42','fe80::1'])
@pytest.mark.parametrize('prefix,suffix',[('Host: ','.'),('Host: [',']:443'),('"','"')])
def test_complete_valid_address(prefix,suffix,value):
 text=prefix+value+suffix;assert m.complete_ipv6_spans(text)==[(len(prefix),len(prefix)+len(value))]
@pytest.mark.parametrize('value',['2001:db8:::27','2001:db8::27::8','2001:db8::gg','2001:db8','12345::27','fe80::1%eth0','x2001:db8::27','2001:db8::27z','2001:db8::27_extra','abc','42','198.51.100.27','1.2.3.4','00:11:22:33:44:55','https://example.org'])
def test_malformed_or_unsupported_does_not_add_address(value):assert m.complete_ipv6_spans(value)==[]
def test_two_addresses_keep_exact_offsets_and_no_whole_sentence_mask():
 text='A [2001:db8::27] B ::1.';assert [text[a:b] for a,b in m.complete_ipv6_spans(text)]==['2001:db8::27','::1']
def test_long_invalid_token_is_not_sliced_into_valid_addresses():assert m.complete_ipv6_spans('a'*200000+'::27')==[]


class Finding:
    def __init__(self,entity_type,start,end,score):self.entity_type=entity_type;self.start=start;self.end=end;self.score=score
class Upstream:
    values=[]
    calls=[]
    def analyze(self,text,entities,nlp_artifacts=None):
        self.calls.append((text,entities,nlp_artifacts));return list(self.values)
class_node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CompleteIPv6Recognizer')
scope.update(IpRecognizer=Upstream,RecognizerResult=Finding)
exec(compile(ast.Module(body=[class_node],type_ignores=[]),str(file),'exec'),scope)

def recognizer(values):
    r=scope['CompleteIPv6Recognizer']();r.values=values;r.calls=[];return r

def test_upstream_ipv4_is_retained_and_arguments_forwarded():
    v=Finding('IP_ADDRESS',0,13,.9);r=recognizer([v]);marker=object();assert r.analyze('198.51.100.27',['IP_ADDRESS'],marker)==[v];assert r.calls==[('198.51.100.27',['IP_ADDRESS'],marker)]
def test_partial_ipv6_replaced_by_complete_shape():
    r=recognizer([Finding('IP_ADDRESS',0,10,.6)]);values=r.analyze('2001:db8::27',['IP_ADDRESS']);assert [(v.start,v.end,v.score) for v in values]==[(0,12,.6)]
def test_existing_complete_finding_keeps_score_and_no_duplicate():
    v=Finding('IP_ADDRESS',0,12,.85);r=recognizer([v]);assert r.analyze('2001:db8::27',['IP_ADDRESS'])==[v]
def test_entity_filter_does_not_add_a_different_entity():
    r=recognizer([]);assert r.analyze('2001:db8::27',['PERSON'])==[]
def test_upstream_scoped_finding_is_retained_without_new_scope_claim():
    v=Finding('IP_ADDRESS',0,13,.6);r=recognizer([v]);assert r.analyze('fe80::1%eth0',['IP_ADDRESS'])==[v]


@pytest.mark.parametrize('label',['IP:','IPv6:','addr:','address:','Host:','ip_address:'])
@pytest.mark.parametrize('value',['2001:db8::27','::1','::ffff:192.0.2.42','2001:db8:0:0:0:0:0:27'])
def test_supported_compact_labels_mask_value_only(label,value):
    text=label+value;assert m.complete_ipv6_spans(text)==[(len(label),len(text))]

@pytest.mark.parametrize('text',['IP:2001:db8:::27','IP:2001:db8::27::8','Host:fe80::1%eth0','IP:2001:db8::27suffix','IP:2001:db8::27_extra','z2001:db8::27','IP:'+('a'*200)+'::27','IP:00:11:22:33:44:55'])
def test_label_value_malformed_embedded_and_scoped_remain_unsupported(text):
    assert m.complete_ipv6_spans(text)==[]

@pytest.mark.parametrize('text',['ffff:2001:db8::27','FACE:2001:db8::27'])
def test_hexadecimal_prefix_is_address_hextet_not_label(text):
    assert m.complete_ipv6_spans(text)==[(0,len(text))]

def test_compact_and_standalone_addresses_keep_sorted_exact_spans():
    text='Host:2001:db8::27; ::1';assert [text[a:b] for a,b in m.complete_ipv6_spans(text)]==['2001:db8::27','::1']

def test_compact_partial_candidate_replaced_without_masking_label():
    r=recognizer([Finding('IP_ADDRESS',3,13,.6)]);values=r.analyze('IP:2001:db8::27',['IP_ADDRESS']);assert [(v.start,v.end,v.score) for v in values]==[(3,15,.6)]

def test_compact_ipv4_candidate_is_unchanged():
    text='IP:198.51.100.27';v=Finding('IP_ADDRESS',3,len(text),.9);r=recognizer([v]);assert r.analyze(text,['IP_ADDRESS'])==[v]
