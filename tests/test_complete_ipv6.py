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


@pytest.mark.parametrize('text,start,end', [('IPv6:::1',5,6),('IPv6:::1',5,8),('addr:::ffff:192.0.2.42',5,6),('addr:::ffff:192.0.2.42',5,22)])
def test_compact_separator_overhang_preserves_the_separator(text,start,end):
    wrong=Finding('IP_ADDRESS',start-1,end,.6)
    values=recognizer([wrong]).analyze(text,['IP_ADDRESS'])
    assert [(v.start,v.end) for v in values]==[(start,len(text))]
    assert text[:values[0].start].endswith(':')

@pytest.mark.parametrize('text,start,end', [('IPv6::::1',4,9),('word:::1',4,8),('Host:fe80::1%eth0',4,16)])
def test_unverified_or_scoped_overlap_is_not_suppressed(text,start,end):
    old=Finding('IP_ADDRESS',start,end,.8)
    assert old in recognizer([old]).analyze(text,['IP_ADDRESS'])

def test_wider_candidate_and_other_entity_are_preserved():
    text='IPv6:::1';wide=Finding('IP_ADDRESS',0,len(text),.9)
    other=Finding('PERSON',4,len(text),.95)
    values=recognizer([wide,other]).analyze(text,['IP_ADDRESS'])
    assert wide in values and other in values
    assert wide.score==.9 and other.score==.95

def test_canonical_score_is_retained_when_separator_duplicate_is_removed():
    text='IPv6:::1';full=Finding('IP_ADDRESS',5,8,.85)
    duplicate=Finding('IP_ADDRESS',4,8,.6)
    assert recognizer([full,duplicate]).analyze(text,['IP_ADDRESS'])==[full]

def test_two_labelled_addresses_preserve_unrelated_findings():
    text='IPv6:::1 addr:::ffff:192.0.2.42';spans=m.complete_ipv6_spans(text)
    old=[Finding('IP_ADDRESS',a-1,b,.6) for a,b in spans]
    keep=Finding('PERSON',0,4,.9)
    result=recognizer([*old,keep]).analyze(text,['IP_ADDRESS'])
    assert keep in result
    assert sorted((v.start,v.end) for v in result if v.entity_type=='IP_ADDRESS')==spans


def test_separator_candidate_extending_beyond_the_valid_value_is_preserved():
    text='IPv6:::1 tail';old=Finding('IP_ADDRESS',4,len(text),.9)
    assert old in recognizer([old]).analyze(text,['IP_ADDRESS'])

def test_more_than_one_outside_character_is_not_removed():
    text='IPv6:::1';old=Finding('IP_ADDRESS',3,6,.9)
    assert old in recognizer([old]).analyze(text,['IP_ADDRESS'])
