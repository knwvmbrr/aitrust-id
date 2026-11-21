"""Declared unique literal selections and builder refusals, not MT accuracy."""
import copy
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from tools import choice_framing,mt_choice_device as device
from protocol import corpus
from protocol.normalization import normalize_nfc

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('choice_practice_builder',ROOT/'scripts/build-mt-choice-practice.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def request(**changes):
    return dict(subject='Not only tea but also coffee.',first='tea',second='coffee',reference='Water is also listed.',whole_frame=True,**changes)if not changes else {**request(),**changes}

def inspect(value):return json.loads(device.inspect_mt_choice(json.dumps(value,ensure_ascii=False,separators=(',',':'))))

@pytest.mark.parametrize('subject,kind',[
    ('Not only tea but also coffee.','not_only_but_also'),('Either tea or coffee.','either_or'),
    ('Only tea or coffee.','only_or'),('Neither tea nor coffee.','neither_nor'),('Between tea and coffee.','between_and')])
def test_full_canonical_record_and_raw_selection_bindings(subject,kind):
    value=request(subject=subject);out=inspect(value);row=out['original']['observations'][0]
    assert row['construction']==kind and not out['intent_established']and out['tags']==[]
    assert out['counts']['additive_frames']==int(kind=='not_only_but_also')
    normalized=normalize_nfc(subject);reference=value['reference']
    source={'id':'practice-reference','text':reference,'sha256':corpus.sha(reference.encode())};content={'format':corpus.VERSION,'documents':[source]};record={**content,'manifest_sha256':corpus.sha(corpus.encoded(content))}
    context={'format':'choice-frame-context/v1','language':'en','subject_sha256':corpus.sha(normalized.encode()),'manifest_sha256':record['manifest_sha256'],'frames':[{'span':[0,len(normalized)],'choices':[[normalized.index(w),normalized.index(w)+len(w)]for w in ('tea','coffee')],'additional_reference':{'document_id':source['id'],'document_sha256':source['sha256'],'source_span':[0,len(reference)]}}]}
    assert out['original']==choice_framing.observe(subject,record,context)
    assert subject not in json.dumps(out)and reference not in json.dumps(out)

@pytest.mark.parametrize('changes',[
    {'whole_frame':False},{'whole_frame':1},{'first':'water'},{'first':'coffee','second':'tea'},
    {'subject':'Not only tea but also tea.'},{'first':'te','second':'tea'},
    {'subject':'x'*2001},{'reference':'x'*2001},{'first':'x'*257},
    {'subject':'\0'},{'first':True},{'reference':''},{'subject':'\ud800'},
])
def test_invalid_or_ambiguous_selection_refuses(changes):
    with pytest.raises((ValueError,UnicodeError)):inspect(request(**changes))

@pytest.mark.parametrize('raw',['{"subject":1,"subject":2}','[]','{}','{"extra":1}','x'*24001])
def test_closed_request_and_wire_budget(raw):
    with pytest.raises((ValueError,UnicodeError)):device.inspect_mt_choice(raw)


def test_NFC_equivalent_raw_request_has_distinct_identity_and_exact_emoji_spans():
    raw=request(subject='😀 Not only cafe\u0301 but also tea.',first='café',second='tea');out=inspect(raw)
    nfc=inspect({**raw,'subject':normalize_nfc(raw['subject'])})
    assert out['subject_sha256']==nfc['subject_sha256']and out['request_sha256']!=nfc['request_sha256']and out['raw_subject_sha256']!=nfc['raw_subject_sha256']
    text=normalize_nfc(raw['subject']);assert[text[a:b]for a,b in out['original']['observations'][0]['choice_spans']]==['café','tea']

@pytest.mark.parametrize('kind',['link','fifo','large','hardlink'])
def test_actual_source_capture_refuses_unsafe_inputs_without_import(tmp_path,kind):
    root=tmp_path.resolve();file=root/'source.py';file.write_text('raise RuntimeError("must not execute")')
    if kind=='link':(root/'real.py').write_text('x');file.unlink();file.symlink_to(root/'real.py')
    if kind=='fifo':file.unlink();os.mkfifo(file)
    if kind=='large':file.write_bytes(b'x'*20)
    if kind=='hardlink':(root/'other').hardlink_to(file)
    with builder.Capture(root)as captured:
        with pytest.raises((ValueError,OSError)):captured.read('source.py',10 if kind=='large' else 200000)


def test_capture_parent_replacement_and_close_attempts_all(tmp_path):
    root=tmp_path.resolve();(root/'sub').mkdir();(root/'sub/x').write_text('data')
    with builder.Capture(root)as captured:
        captured.read('sub/x');(root/'sub').rename(root/'old');(root/'sub').mkdir()
        with pytest.raises(ValueError):captured.check()
    captured=builder.Capture(root);owned=list(captured.fds);calls=[];close=os.close
    def fail(fd):calls.append(fd);close(fd);raise OSError('private close')
    with patch.object(os,'close',side_effect=fail),pytest.raises(ValueError):captured.close()
    assert calls==list(reversed(owned))and captured.fds==[]


def test_exclusive_publish_preserves_old_output_and_reports_new_write_failure(tmp_path):
    parent=tmp_path.resolve();parent.chmod(0o700);out=parent/'artifact';out.mkdir(mode=0o700);(out/'owner').write_text('keep')
    with pytest.raises(ValueError):builder.publish(out,{'x.txt':b'new'},lambda:None,{'started':False})
    assert(out/'owner').read_text()=='keep'
    out=parent/'new';state={'started':False}
    with patch.object(os,'write',side_effect=OSError('private write')),pytest.raises(OSError):builder.publish(out,{'x.txt':b'new'},lambda:None,state)
    assert state['started']and not out.exists()


def test_generated_theme_keeps_brand_paths_palette_and_quiet_background():
    raw=(ROOT/'site/public/camo-q4.svg').read_bytes();images=builder.theme_images(raw)
    assert set(images)=={'camo-light.svg','camo-dark.svg'}
    for name,base,other in [('light',b'#f3f1e7',b'#11170f'),('dark',b'#11170f',b'#f3f1e7')]:
        value=images['camo-'+name+'.svg'];assert base in value and other not in value
        assert b'opacity="0.3"'in value and b'woodland-a'in value and b'woodland-b'in value and b'woodland-c'in value
        assert b'<view 'not in value and b'<script'not in value
    with pytest.raises(ValueError):builder.theme_images(b'<svg><script>bad</script></svg>')
