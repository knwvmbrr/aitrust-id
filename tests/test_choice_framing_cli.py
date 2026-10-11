import importlib.util
import json
from pathlib import Path
import pytest
from protocol import corpus
from tools.language_observations import digest
from tools.choice_framing import observe

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('choice_cli',ROOT/'scripts/check-choice-framing.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)

@pytest.fixture
def packet(tmp_path):
    tmp_path.chmod(0o700)
    doc=tmp_path/'reference.txt';doc.write_text('You can remain undecided.')
    manifest=tmp_path/'corpus.json';corpus.create([('reference',doc)],manifest)
    record=corpus.load(manifest)
    text='Either agree or oppose.';query=tmp_path/'subject.txt';query.write_text(text);query.chmod(0o600)
    data={'format':'choice-frame-context/v1','language':'en','subject_sha256':digest(text),
        'manifest_sha256':record['manifest_sha256'],'frames':[{'span':[0,len(text)],'choices':[[7,12],[16,22]],
        'additional_reference':{'document_id':'reference','document_sha256':record['documents'][0]['sha256'],
        'source_span':[0,len(doc.read_text())]}}]}
    context=tmp_path/'context.json';context.write_text(json.dumps(data));context.chmod(0o600)
    args=['--subject',str(query),'--corpus',str(manifest),'--context',str(context)]
    return tmp_path,query,manifest,context,data,args

def test_default_summary_omits_content_hashes_and_spans(packet,capsys):
    assert cli.main(packet[-1])==0
    out=capsys.readouterr();summary=json.loads(out.out)
    assert summary['supported_binary_patterns']==1 and summary['selected_frames_checked']==1
    assert not summary['tag_asserted'] and not summary['manipulation_established']
    assert 'subject_sha256' not in summary and 'observations' not in summary
    assert 'Either agree' not in out.out and 'You can remain' not in out.out
    assert str(packet[0]) not in out.out and not out.err

def test_details_are_explicit_private_and_not_overwritten(packet,capsys):
    target=packet[0]/'details';args=packet[-1]+['--details',str(target)]
    assert cli.main(args)==0
    item=target/'choice-observations.json';before=item.read_bytes();data=json.loads(before)
    assert data['observations'][0]['choice_spans']==[[7,12],[16,22]]
    assert not data['observations'][0]['additional_option_verified']
    assert target.stat().st_mode&0o077==0 and item.stat().st_mode&0o077==0
    assert cli.main(args)==2 and item.read_bytes()==before
    output=capsys.readouterr();assert str(packet[0]) not in output.out+output.err

@pytest.mark.parametrize('kind',['query-public','context-public','corpus-public','query-link','context-link','corpus-link','query-hardlink','context-hardlink','duplicate-json','invalid-utf8','oversized-json','stale-hash','boolean-span','unsupported-language','unknown-field'])
def test_private_and_binding_refusals_have_no_echo(packet,capsys,kind):
    base,query,manifest,context,data,_=packet
    if kind.endswith('-public'):
        {'query':query,'context':context,'corpus':manifest}[kind.split('-')[0]].chmod(0o644)
    if kind.endswith('-link'):
        original={'query':query,'context':context,'corpus':manifest}[kind.split('-')[0]]
        link=base/'link';link.symlink_to(original)
        if kind=='query-link':query=link
        if kind=='context-link':context=link
        if kind=='corpus-link':manifest=link
    if kind.endswith('-hardlink'):(base/'hard').hardlink_to(query if kind=='query-hardlink' else context)
    if kind=='duplicate-json':context.write_text('{"private-canary":1,"private-canary":2}')
    if kind=='invalid-utf8':query.write_bytes(b'private-canary\xff')
    if kind=='oversized-json':context.write_text('private-canary '*3000)
    if kind=='stale-hash':data['subject_sha256']='private-canary';context.write_text(json.dumps(data))
    if kind=='boolean-span':data['frames'][0]['span'][0]=True;context.write_text(json.dumps(data))
    if kind=='unsupported-language':data['language']='private-canary';context.write_text(json.dumps(data))
    if kind=='unknown-field':data['private-canary']=True;context.write_text(json.dumps(data))
    assert cli.main(['--subject',str(query),'--corpus',str(manifest),'--context',str(context)])==2
    output=capsys.readouterr();assert not output.out and str(base) not in output.err and 'private-canary' not in output.err
    assert json.loads(output.err)['state']=='UNAVAILABLE'


def test_packet_mode_matches_individual_files(packet,capsys):
    assert cli.main(['--packet',str(packet[0])])==0
    first=json.loads(capsys.readouterr().out)
    assert cli.main(packet[-1])==0
    assert json.loads(capsys.readouterr().out)==first


def test_mixed_or_incomplete_input_modes_refuse(packet,capsys):
    assert cli.main(['--packet',str(packet[0]),'--subject',str(packet[1])])==2
    assert cli.main(['--subject',str(packet[1])])==2
    output=capsys.readouterr();assert not output.out and str(packet[0]) not in output.err


def test_demo_is_private_valid_synthetic_and_exclusive(packet,capsys):
    spec=importlib.util.spec_from_file_location('choice_demo',ROOT/'scripts/prepare-choice-demo.py')
    demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
    target=packet[0]/'practice'
    assert demo.main(['--output',str(target)])==0
    metadata=json.loads(capsys.readouterr().out)
    assert metadata['synthetic_only'] and not metadata['user_example_read']
    before={p.name:p.read_bytes() for p in target.iterdir()}
    assert set(before)=={'subject.txt','corpus.json','context.json'}
    assert target.stat().st_mode&0o077==0 and all(p.stat().st_mode&0o077==0 for p in target.iterdir())
    assert cli.main(['--packet',str(target)])==0
    summary=json.loads(capsys.readouterr().out)
    assert summary['supported_binary_patterns']==1 and not summary['additional_options_verified']
    assert demo.main(['--output',str(target)])==2
    assert before=={p.name:p.read_bytes() for p in target.iterdir()}
