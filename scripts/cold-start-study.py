#!/usr/bin/env python3
"""One predeclared three-host Android study; no runtime or acceptance changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys

FROZEN_COMMIT='78c634ba425e7ee1b4c2df3e97219cf0fef8cd33'
SAMPLES=(1,2,3)
CASES=('receive_requires_explicit_check','actual_offline_ps_finding','edit_hides_previous_finding',
       'new_share_and_no_finding','unsupported_mime_has_no_verdict','clear_removes_input_and_result','background_clears_text')
MAX_JSON=131072
EXPECTED_SOURCES={'.github/workflows/android-share.yml': 'e673479d729368e86e45b990f3c2f7649abbaac2b2698e2532e43042a2c15f6e',
 'mobile/android/AndroidManifest.xml': 'f4ed0cebdc2b9198702ef2c62015b0e70758082661e1edc7da8d0a51313c5a74',
 'mobile/android/res/drawable/camouflage.xml': '92f183c3df0dd7c790b627f07523849f745757f9104051ff506d6d0200d8dbca',
 'mobile/android/res/drawable/ic_tag.xml': 'b0f3d896ef3be0239929857372d2249253d50a8d8efe1b4838bd2032bc8b68f2',
 'mobile/android/res/values-night/colors.xml': '2d51774a873ac59b53ac8ac9d83a969015fbcc112a8d41854fdf04527d244c3a',
 'mobile/android/res/values-night/styles.xml': '323aeaa6e5cf6776e2e986ed51753799a06e691bcf9d9625a9d86a951400385d',
 'mobile/android/res/values/colors.xml': 'a02ea5c1dd1cdac67550685cb0d0ce4ad36c2f3ba47beb6badaa01d5551f9cb3',
 'mobile/android/res/values/styles.xml': '2e11243a09e33148fee4dc180f39da3318fc9b3892f2b45ca7be6c1ef749322b',
 'mobile/android/src/com/aitrustid/android/CheckActivity.java': '2ab7df4100143e4e17e9c87db74f15c1641edf54fff7a986c30b463aa2c6266b',
 'mobile/android/src/com/aitrustid/android/OfflineEngine.java': '5be1c6b878b6d8690e140d2d24b91dab11c16f1df4d683c8ef09c9c6b363b65f',
 'mobile/android/src/com/aitrustid/android/ShareSession.java': '04ea340fad0984944e1f41220ba3803db4164a78efea79561112d9e2039c1332',
 'mobile/android/tests/ShareSessionTest.java': '8089af2b7968c748e82d027107937fb8046235e246f48f0cd3f5437b0ca51dd6',
 'mobile/android/web/bridge.mjs': 'b499e790d92354cc6f247f5f4e74e56b0acc57eaa99b11623274809102bc09ad',
 'mobile/android/web/index.html': '56aa15470255e8953463f10795fd8ba5641345111f5354e92671b4d5dd171a29',
 'protocol/normalization.py': 'd949dd32a43762b6d71c7c746430c3ee0fc0d4036885e3b1a2a94deb056f09d1',
 'protocol/unicode15-data.json': '76121e982f9338f18905eb69e9c9c4b5268247b91841eb20e999b39e11aa0458',
 'sbom/assets/notices.json': '5c165aea3c716a183174a10ce8be0b5e0894554a8ad5492171e5141dc642facd',
 'sbom/notices/manifest.json': '8a19f0328c542c610fb5028e78313c80e7bf40c2d4e51f281a144883ee95bb58',
 'scripts/android-share-build.py': '8cb6ed20056bbf9d7f69dfb2fb19eaf9c5025eeb44ef8ea3f7d52576ffa1184e',
 'scripts/build-device-detector.py': '582e2b24f8895071216bbbde0891062feb093869283e776757ea5def40ea93a3',
 'scripts/verify-android-emulator.py': '740b64ffde7368ade2c5134fbf9e53f53cadb8ca677a38d48eba0373ebbe6e59',
 'services/evaluator/app.py': 'ee1cc1e11b68de9c6971714232b505b97e4a9f32e216d544217fbebf04779631',
 'site/package-lock.json': '527f689fcb38beb9de7756c227084b41e9afcf547de92c687646edd90e01449e',
 'tests/android/CheckActivity.java': '76e847187c37bf216aaaffb7da71d7b663ffe1cba5c64c17eb4cf7f098d513e7',
 'tests/test_android_emulator_prerequisites.py': '1f8187bf906fd0391cc63180fc03b1e37d91414273138b11b14429d2a43ad07d',
 'tests/test_android_intake_probe.py': '6bfa1bb529e2521002674cce484677f636c9ac60862848bb84694a49a82ac029',
 'tests/test_android_share.py': '6991a63dda1ad6817f85ab759f0e9f14149cbaa1e37fc1d08903bcd8541c9938'}
NATIVE_SOURCES={'mobile/android/AndroidManifest.xml': 'f4ed0cebdc2b9198702ef2c62015b0e70758082661e1edc7da8d0a51313c5a74',
 'mobile/android/res/drawable/camouflage.xml': '92f183c3df0dd7c790b627f07523849f745757f9104051ff506d6d0200d8dbca',
 'mobile/android/res/drawable/ic_tag.xml': 'b0f3d896ef3be0239929857372d2249253d50a8d8efe1b4838bd2032bc8b68f2',
 'mobile/android/res/values-night/colors.xml': '2d51774a873ac59b53ac8ac9d83a969015fbcc112a8d41854fdf04527d244c3a',
 'mobile/android/res/values-night/styles.xml': '323aeaa6e5cf6776e2e986ed51753799a06e691bcf9d9625a9d86a951400385d',
 'mobile/android/res/values/colors.xml': 'a02ea5c1dd1cdac67550685cb0d0ce4ad36c2f3ba47beb6badaa01d5551f9cb3',
 'mobile/android/res/values/styles.xml': '2e11243a09e33148fee4dc180f39da3318fc9b3892f2b45ca7be6c1ef749322b',
 'mobile/android/src/com/aitrustid/android/CheckActivity.java': '2ab7df4100143e4e17e9c87db74f15c1641edf54fff7a986c30b463aa2c6266b',
 'mobile/android/src/com/aitrustid/android/OfflineEngine.java': '5be1c6b878b6d8690e140d2d24b91dab11c16f1df4d683c8ef09c9c6b363b65f',
 'mobile/android/src/com/aitrustid/android/ShareSession.java': '04ea340fad0984944e1f41220ba3803db4164a78efea79561112d9e2039c1332',
 'mobile/android/tests/ShareSessionTest.java': '8089af2b7968c748e82d027107937fb8046235e246f48f0cd3f5437b0ca51dd6',
 'mobile/android/web/bridge.mjs': 'b499e790d92354cc6f247f5f4e74e56b0acc57eaa99b11623274809102bc09ad',
 'mobile/android/web/index.html': '56aa15470255e8953463f10795fd8ba5641345111f5354e92671b4d5dd171a29'}
EXPECTED_DIAGNOSTIC_VARIANT={'compiled_base_sha256': 'a4b5629e5e2cdf953632c25fb1163ce3ed5d3703f1be3f905338b34ab19517f3',
 'production_activity_sha256': '2ab7df4100143e4e17e9c87db74f15c1641edf54fff7a986c30b463aa2c6266b',
 'production_equivalent_apk': False,
 'variant': 'intake-provenance-only/v1',
 'wrapper_sha256': '76e847187c37bf216aaaffb7da71d7b663ffe1cba5c64c17eb4cf7f098d513e7'}


class StudyError(ValueError):pass
class OutputCommitUncertain(StudyError):pass

def need(value):
    if not value:raise StudyError('study_input_unavailable')

def sha(raw):return hashlib.sha256(raw).hexdigest()

def read_regular(path,limit=MAX_JSON):
    path=Path(path).absolute();need('..' not in path.parts)
    owned=[];directories=[]
    try:
        current=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);owned.append(current)
        for part in path.parts[1:-1]:
            parent=current;current=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent);owned.append(current)
            directories.append((parent,part,os.fstat(current)))
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current);owned.append(fd)
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit)
        raw=bytearray()
        while len(raw)<=limit:
            chunk=os.read(fd,min(65536,limit+1-len(raw)))
            if not chunk:break
            raw.extend(chunk)
        after=os.fstat(fd);named=os.stat(path.name,dir_fd=current,follow_symlinks=False)
        identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        need(len(raw)==before.st_size and identity(before)==identity(after)==identity(named))
        for parent,name,info in directories:
            now=os.stat(name,dir_fd=parent,follow_symlinks=False)
            need((info.st_dev,info.st_ino,info.st_mode)==(now.st_dev,now.st_ino,now.st_mode))
        return bytes(raw)
    finally:
        error=None
        for fd in reversed(owned):
            try:os.close(fd)
            except OSError as failure:error=failure
        if error is not None:raise StudyError('study_input_unavailable') from None


def decode(raw):
    def unique(items):
        result={}
        for key,value in items:
            need(key not in result);result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(StudyError('study_input_unavailable')))
    need(isinstance(value,dict));return value


def save(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();need(len(raw)<=MAX_JSON)
    path=Path(path).absolute();need('..' not in path.parts)
    parents=[]
    try:
        parent=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);parents.append(parent)
        for name in path.parts[1:-1]:
            try:os.mkdir(name,mode=0o700,dir_fd=parent)
            except FileExistsError:pass
            parent=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent);parents.append(parent)
    except BaseException:
        for owned in reversed(parents):
            try:os.close(owned)
            except OSError:pass
        raise
    temporary='.study-'+secrets.token_hex(16);fd=None;attempted=False;error=None
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        view=memoryview(raw)
        while view:
            written=os.write(fd,view);need(written>0);view=view[written:]
        os.fsync(fd);owned=fd;fd=None;os.close(owned)
        try:os.link(temporary,path.name,src_dir_fd=parent,dst_dir_fd=parent,follow_symlinks=False)
        except FileExistsError:raise
        except OSError:attempted=True;raise
        attempted=True;os.fsync(parent)
    except Exception as failure:error=failure
    finally:
        if fd is not None:
            owned=fd;fd=None
            try:os.close(owned)
            except OSError as failure:
                if error is None:error=failure
        try:os.unlink(temporary,dir_fd=parent)
        except FileNotFoundError:pass
        except OSError as failure:
            if error is None:error=failure
        for owned in reversed(parents):
            try:os.close(owned)
            except OSError as failure:
                if error is None:error=failure
    if error is not None:
        if attempted:raise OutputCommitUncertain('output_commit_uncertain') from None
        raise StudyError('study_output_unavailable') from None


def source_record(root,phase):
    root=Path(root).absolute();need(phase in ('start','end'))
    def git(args):
        process=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=10)
        need(process.returncode==0);return process.stdout
    commit=git(['rev-parse','HEAD']).decode('ascii').strip();need(commit==FROZEN_COMMIT)
    need(git(['status','--porcelain','--untracked-files=no'])==b'')
    observed={name:sha(read_regular(root/name,2_000_000)) for name in EXPECTED_SOURCES}
    need(observed==EXPECTED_SOURCES)
    return {'format':'android-intake-provenance-source/v1','phase':phase,'pass':True,
            'source_commit':commit,'sources_sha256':observed,'tracked_source_clean':True,
            'control_script_sha256':sha(Path(__file__).read_bytes())}


def read_json(path):return decode(read_regular(path))

def provenance(value):
    unavailable={'state':'UNAVAILABLE','reason':'intake_provenance_unavailable'}
    if type(value) is not dict or set(value)!={'state','scope','schema','instances','truncated','events'}:return unavailable
    if value['state']!='OBSERVED' or value['scope']!='diagnostic-variant-current-process-only':return unavailable
    if type(value['schema']) is not int or value['schema']!=1:return unavailable
    if type(value['instances']) is not int or not 1<=value['instances']<=255:return unavailable
    if value['truncated'] is not False or type(value['events']) is not list or not 1<=len(value['events'])<=32:return unavailable
    callbacks={name+'_'+phase for name in ('CREATE','NEW_INTENT','RESUME','PAUSE','STOP','DESTROY','SAVE') for phase in ('BEGIN','END')}
    for row in value['events']:
        if type(row) is not list or len(row)!=6:return unavailable
        instance,callback,action,editor,status,changing=row
        if type(instance) is not int or not 1<=instance<=value['instances']:return unavailable
        if type(callback) is not str or callback not in callbacks:return unavailable
        if type(action) is not str or action not in ('NONE','SEND','MAIN','OTHER'):return unavailable
        if type(editor) is not bool or type(changing) is not bool:return unavailable
        if type(status) is not str or status not in ('UNBUILT','READY','RECEIVED','CLEARED','OTHER'):return unavailable
    return value


def diagnostics(value):
    result={}
    if not isinstance(value,dict):return result
    ui=value.get('last_ui_observation')
    keys=('owned_ui_present','owned_editor_present','owned_editor_nonempty','received_text_present','ready_text_present',
          'cleared_text_present','changed_text_present','finding_text_present','no_finding_text_present',
          'unsupported_mime_text_present','unavailable_text_present','tag_ps_present','first_synthetic_text_present',
          'system_ui_present','launcher_ui_present','platform_error_dialog_present')
    if isinstance(ui,dict):result['last_ui_booleans']={k:ui[k] for k in keys if type(ui.get(k)) is bool}
    lifecycle=value.get('first_failure_lifecycle')
    if isinstance(lifecycle,dict):
        state=lifecycle.get('state');result['lifecycle_metadata_state']=state if state in ('OBSERVED','PARTIAL','NO_MATCHING_OWNED_EVENTS','UNAVAILABLE') else 'UNRECOGNIZED'
        counts=lifecycle.get('observed_event_counts');tags=('wm_create_activity','wm_new_intent','wm_relaunch_activity','wm_on_create_called','wm_on_resume_called','wm_on_paused_called','wm_on_stop_called')
        if isinstance(counts,dict) and set(counts)==set(tags) and all(type(counts[k]) is int and 0<=counts[k]<=128 for k in tags):result['observed_event_counts']={k:counts[k] for k in tags}
        allowed=set(tags[2:])|{tag+':'+action for tag in tags[:2] for action in ('SEND','MAIN','OTHER')}
        sequence=lifecycle.get('observed_sequence')
        if isinstance(sequence,list) and len(sequence)<=128 and all(isinstance(v,str) and v in allowed for v in sequence):result['observed_sequence']=sequence
    result['first_receive_provenance']=provenance(value.get('first_receive_provenance'))
    return result


def sample_result(directory):
    result={'pass':False,'reported_status':'MISSING_OR_REFUSED','reported_case_count':None,'reasons':[]}
    try:
        start=read_json(directory/'study-source-start.json');end=read_json(directory/'study-source-end.json')
        for phase,value in [('start',start),('end',end)]:
            need(value.get('format')=='android-intake-provenance-source/v1' and value.get('phase')==phase and value.get('pass') is True)
            need(value.get('source_commit')==FROZEN_COMMIT and value.get('sources_sha256')==EXPECTED_SOURCES and value.get('tracked_source_clean') is True)
            need(value.get('control_script_sha256')==sha(Path(__file__).read_bytes()))
        emulator_raw=read_regular(directory/'emulator.json');emulator=decode(emulator_raw)
        status=emulator.get('status');result['reported_status']=status if status in ('EXECUTED','UNAVAILABLE','FAILED') else 'UNRECOGNIZED'
        cases=emulator.get('cases')
        if isinstance(cases,list) and len(cases)<=7:result['reported_case_count']=len(cases)
        result.update(diagnostics(emulator))
        result['raw_emulator_sha256']=sha(emulator_raw)
        need(emulator.get('format')=='ai-trust-id-android-emulator/v1' and status=='EXECUTED' and emulator.get('pass') is True and emulator.get('phase')=='complete')
        need(type(emulator.get('case_count')) is int and emulator['case_count']==7 and emulator.get('api_level')=='36')
        need(emulator.get('internet_permission') is False and emulator.get('license_record_unchanged') is True and emulator.get('sdk_license_acceptance_inferred_from_metadata_hash') is False)
        need(emulator.get('physical_device_evidence') is False and emulator.get('independent_accuracy_evidence') is False)
        need(isinstance(cases,list) and len(cases)==7)
        for row,name in zip(cases,CASES):need(isinstance(row,dict) and set(row)=={'case','pass'} and row['case']==name and row['pass'] is True)
        build=read_json(directory/'build.json');engine=read_json(directory/'engine-parity.json');prep=read_json(directory/'preparation.json')
        variant=build.get('diagnostic_variant')
        need(type(variant) is dict and set(variant)==set(EXPECTED_DIAGNOSTIC_VARIANT))
        need(variant['production_equivalent_apk'] is False)
        need(all(type(variant[key]) is str for key in EXPECTED_DIAGNOSTIC_VARIANT if key!='production_equivalent_apk'))
        need(variant==EXPECTED_DIAGNOSTIC_VARIANT)
        need(provenance(emulator.get('first_receive_provenance'))['state']=='OBSERVED')
        need(emulator.get('requested_diagnostic_variant')=='intake-provenance-only/v1')
        need(build.get('pass') is True and build.get('sources')==NATIVE_SOURCES and type(build.get('permission_count')) is int and build['permission_count']==0)
        need(engine.get('pass') is True and prep.get('pass') is True and prep.get('runtime')=='314.0.7')
        method=build.get('method_sha256');need(method==EXPECTED_SOURCES['services/evaluator/app.py'])
        need(engine.get('method_sha256')==method==prep.get('method_sha256'))
        result['raw_emulator_sha256']=sha(emulator_raw);result['pass']=True
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,RecursionError):result['reasons'].append('missing_failed_or_refused_sample')
    return result


def aggregate(inputs,run_id,attempt,matrix_result):
    need(re.fullmatch(r'[1-9][0-9]{0,19}',run_id) is not None)
    expected={f'android-intake-provenance-{run_id}-sample-{sample}' for sample in SAMPLES}
    root=Path(inputs).absolute();inventory_ok=False
    try:inventory_ok=root.is_dir() and not root.is_symlink() and {p.name for p in root.iterdir()}==expected
    except OSError:pass
    rows=[]
    for sample in SAMPLES:
        name=f'android-intake-provenance-{run_id}-sample-{sample}'
        result=sample_result(root/name);rows.append({'sample':sample,**result})
    passed=attempt=='1' and matrix_result=='success' and inventory_ok and all(row['pass'] for row in rows)
    return {'format':'android-intake-provenance-study/v1','pass':passed,'source_commit':FROZEN_COMMIT,
            'control_script_sha256':sha(Path(__file__).read_bytes()),'run_id':run_id,'run_attempt_admitted':attempt=='1',
            'matrix_result_success':matrix_result=='success','exact_three_artifact_inventory':inventory_ok,
            'expected_samples':3,'samples_executed_seven':sum(row['pass'] for row in rows),'samples':rows,
            'all_outcomes_required':True,'historical_cause_known':False,'startup_reliability_established':False,
            'independent_accuracy_evidence':False,'physical_device_evidence':False,'original_requirement_closed':False}


class Parser(argparse.ArgumentParser):
    def error(self,message):raise StudyError('study_arguments_unavailable')


def main(argv=None):
    try:
        parser=Parser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
        for command in ('source-start','source-end'):
            p=sub.add_parser(command);p.add_argument('--root',required=True);p.add_argument('--output',required=True)
        p=sub.add_parser('aggregate');p.add_argument('--inputs',required=True);p.add_argument('--run-id',required=True);p.add_argument('--attempt',required=True);p.add_argument('--matrix-result',required=True);p.add_argument('--output',required=True)
        args=parser.parse_args(argv)
    except (StudyError,ValueError):print('{"pass":false,"reason":"study_arguments_unavailable"}');return 2
    try:
        value=aggregate(args.inputs,args.run_id,args.attempt,args.matrix_result) if args.command=='aggregate' else source_record(args.root,args.command.removeprefix('source-'))
    except (OSError,ValueError,UnicodeError,RecursionError,subprocess.SubprocessError):value={'format':'android-intake-provenance-source/v1','pass':False,'reason':'frozen_source_unavailable'}
    try:save(args.output,value)
    except OutputCommitUncertain:print('{"pass":false,"reason":"output_commit_uncertain","output_may_exist":true}');return 2
    except (OSError,ValueError):print('{"pass":false,"reason":"study_output_unavailable"}');return 2
    print(json.dumps({'pass':value['pass'],'format':value['format']}));return 0 if value['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
