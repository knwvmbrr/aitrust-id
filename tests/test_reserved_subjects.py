"""Cross-runtime subjects, transforms, resource bounds and actual safe CLI use."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from protocol.reserved_subjects import subject,validate_span
ROOT=Path(__file__).resolve().parents[1]
def b64(value):return base64.b64encode(value).decode()
def image(raw=b'\xff\x00\x00\xff',width=1,height=1):return {'modality':'image','width':width,'height':height,'representation':'RGBA8-sRGB-straight-oriented','pixels_base64':b64(raw)}
def audio(raw=b'\x00\x00\xff\x7f',rate=48000,channels=1):return {'modality':'audio','sample_rate':rate,'channels':channels,'representation':'PCM16LE-interleaved','samples_base64':b64(raw)}
def video(count=3):return {'modality':'video','representation':'decoded-frames-us-v1','frames':[{'timestamp_us':i*40000,'duration_us':40000,'image':image(bytes([i,0,0,255]))} for i in range(count)]}
def document(text='e\u0301🧪\r\n'):
    return {'modality':'document','extraction_profile':'supplied-page-text-v1','pages':[{'text':text,'assets':[]},{'text':'Second page','assets':[{'media_type':'application/octet-stream','data_base64':b64(b'\x00\xff')},{'media_type':'image/png','data_base64':b64(b'prepared asset bytes')}]}]}
def valid_cases():
    return [image(),image(b'\x00\x00\x00\x00'),image(bytes(range(16)),2,2),image(bytes(range(16)),4,1),audio(),audio(rate=44100),audio(channels=2),audio(b'\x01\x00\x00\x01'),video(1),video(2),video(3),video(4),document(),document('é🧪\r\n'),document('é🧪\n'),{'modality':'document','extraction_profile':'supplied-page-text-v1','pages':[{'text':'','assets':[]}]}]
def invalid_cases():
    values=[None,[],{}, {'modality':'pdf'},{'modality':'text','text':'unreserved'}]
    for key,value in [('width',True),('width',0),('height',1.5),('width',262145),('height',None),('representation','RGB8'),('pixels_base64','not base64'),('pixels_base64','AA=='),('pixels_base64','AB=='),('metadata',{'orientation':6})]:
        case=image();case[key]=value;values.append(case)
    for key,value in [('sample_rate',7999),('sample_rate',192001),('channels',0),('channels',True),('representation','float32'),('samples_base64','AA=='),('samples_base64',''),('samples_base64',4),('samples_base64','AAAA\n')]:
        case=audio();case[key]=value;values.append(case)
    for field,value in [('timestamp_us',-1),('duration_us',0),('duration_us',True),('timestamp_us',2**53),('timestamp_us',1)]:
        case=video();case['frames'][1][field]=value;values.append(case)
    case=video();case['frames']=[];values.append(case)
    case=video();case['frames']*=22;values.append(case)
    for field,value in [('extraction_profile','pdf-reader-unversioned'),('pages',[]),('pages',[{'text':'hello'}]),('pages',[{'text':42,'assets':[]}]),('pages',[{'text':'\ud800','assets':[]}]),('pages',[{'text':'a'*200001,'assets':[]}]),('pages',[{'text':'hello','assets':[{'media_type':'bad type','data_base64':''}]}])]:
        case=document();case[field]=value;values.append(case)
    case=document();case['pages']*=51;values.append(case)
    case=document();case['pages'][1]['assets']*=33;values.append(case)
    values.extend([image(b'a'*(1048576+1),1,1),audio(b'a'*(1048576+1)),{'modality':'video','representation':'decoded-frames-us-v1','frames':[{'timestamp_us':i,'duration_us':1,'image':image(b'a'*1048576,512,512)} for i in range(5)]}])
    return values
def node_results(values):
    script="const fs=require('fs'),{subject}=require('./protocol/reserved-subjects.cjs'); const values=JSON.parse(fs.readFileSync(0,'utf8')); console.log(JSON.stringify(values.map(v=>{try{return {ok:true,value:subject(v)}}catch{return {ok:false}}})));"
    p=subprocess.run(['node','-e',script],cwd=ROOT,input=json.dumps(values),text=True,capture_output=True,check=True)
    return json.loads(p.stdout)
@pytest.mark.parametrize('value',valid_cases())
def test_expected_fixed_vectors(value):
    vectors=json.loads((ROOT/'eval/vectors/reserved-subjects-v1.json').read_text())['valid']
    expected=next(row['expected'] for row in vectors if row['input']==value)
    assert subject(value)==expected
@pytest.mark.parametrize('value',invalid_cases())
def test_invalid_artifacts_fail(value):
    with pytest.raises((ValueError,UnicodeError)):subject(value)
def test_independent_node_agrees_and_rejects_every_invalid_artifact():
    valid=valid_cases();invalid=invalid_cases();results=node_results(valid+invalid)
    assert [r['value'] for r in results[:len(valid)]]==[subject(v) for v in valid]
    assert all(not r['ok'] for r in results[len(valid):])
def test_document_canonical_equivalence_and_transform_sensitivity():
    assert subject(document('e\u0301🧪\r\n'))==subject(document('é🧪\r\n'))
    assert subject(document('é🧪\r\n'))['sha256']!=subject(document('é🧪\n'))['sha256']
    a=document();b=copy.deepcopy(a);b['pages'].reverse();assert subject(a)['sha256']!=subject(b)['sha256']
    b=copy.deepcopy(a);b['pages'][1]['assets'].reverse();assert subject(a)['sha256']!=subject(b)['sha256']
def test_parameters_and_timing_are_bound_to_subject():
    assert subject(image(bytes(range(16)),2,2))['sha256']!=subject(image(bytes(range(16)),4,1))['sha256']
    assert subject(audio())['sha256']!=subject(audio(rate=44100))['sha256']
    a=video();b=copy.deepcopy(a);b['frames'][-1]['duration_us']+=1;assert subject(a)['sha256']!=subject(b)['sha256']
def test_integral_json_number_representation_is_not_a_language_difference():
    value=image();value['width']=1.0;value['height']=1e0
    assert subject(value)==subject(image())==node_results([value])[0]['value']
def test_actual_cli_has_no_input_echo_and_rejects_duplicates_files_and_size():
    command=[sys.executable,str(ROOT/'scripts/hash-reserved-artifact.py')]
    for value in [image(),audio(),video(),document()]:
        p=subprocess.run(command,input=json.dumps(value),text=True,capture_output=True)
        assert p.returncode==0 and json.loads(p.stdout)==subject(value)
    for raw in ['{"modality":"image","modality":"audio"}', 'private response canary',json.dumps({'path':'/etc/passwd'}),'x'*8388609]:
        p=subprocess.run(command,input=raw,text=True,capture_output=True)
        assert p.returncode==1 and not p.stdout and 'canary' not in p.stderr and '/etc/passwd' not in p.stderr
def span_cases():
    return [(image(),[0,0,1,1]),(audio(),[0,2]),(video(),{'frame':2,'box':[0,0,1,1]}),(document(),{'page':0,'range':[0,2]})]
def invalid_spans():
    return [(image(),[0,0,2,1]),(image(),[0,0,0,1]),(image(),[True,0,1,1]),(audio(),[-1,1]),(audio(),[0,3]),(audio(),[0,0]),(video(),{'frame':3,'box':[0,0,1,1]}),(video(),{'frame':0,'box':[0,0,1,1],'timestamp_us':0}),(document(),{'page':0,'range':[0,5]}),(document(),{'page':-1,'range':[0,1]}),(document(),{'page':True,'range':[0,1]})]
@pytest.mark.parametrize('artifact,span',span_cases())
def test_valid_exact_coordinate_units(artifact,span):assert validate_span(artifact,span)==span
@pytest.mark.parametrize('artifact,span',invalid_spans())
def test_out_of_bound_or_ambiguous_coordinates_refused(artifact,span):
    with pytest.raises(ValueError):validate_span(artifact,span)
def test_node_coordinates_match_independently():
    values=span_cases()+invalid_spans()
    script="const fs=require('fs'),{validateSpan}=require('./protocol/reserved-subjects.cjs'); console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(([v,s])=>{try{return {ok:true,value:validateSpan(v,s)}}catch{return {ok:false}}})));"
    p=subprocess.run(['node','-e',script],cwd=ROOT,input=json.dumps(values),text=True,capture_output=True,check=True);results=json.loads(p.stdout)
    assert [r['value'] for r in results[:4]]==[span for _,span in span_cases()]
    assert all(not r['ok'] for r in results[4:])
