"""Owned, serial Simulator layout observations; never seven-flow/physical acceptance."""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import types
import uuid

ROOT=Path(__file__).absolute().parents[1]
RUNTIME='com.apple.CoreSimulator.SimRuntime.iOS-26-2'
BUILD='23C54'
PROFILES={'small':'iPhone-SE-3rd-generation','regular':'iPhone-14','plus':'iPhone-14-Plus','max':'iPhone-17-Pro-Max'}
MODEL_NAMES={'small':'iPhone SE (3rd generation)','regular':'iPhone 14','plus':'iPhone 14 Plus','max':'iPhone 17 Pro Max'}
CONFIGS=(('light-standard','light','large'),('dark-standard','dark','large'),('light-largest','light','accessibility-extra-extra-extra-large'))
TEST_ID='SizeLayoutFlows/testReadableControlsAndNotices()'
FIXTURE_SHA256='6e456b4ba2af4d72019c7b3717523302265a7be1194d97000bc18afb766eba90'
LEGACY_UI_SHA256='16b0ac936caed61cd2d26ba0bc45c03714992488196b0af8175301a6946ed388'
PINS={'scripts/verify-ios-share.py':'c61df1755cc93dd04d6d9af0960833151e6b920fd6d68903405b8262475c86bf','scripts/build-ios-project.py':'821b0e95ee9e6169997bd030ab17f6d279fa747b5c91293d0c67b3f72514108e','tools/artifact_evidence_io.py':'2d8089a460d0b70c7725ce8bfdecda88b798c70d3335cfbb22c8fe5b31ea0b4e'}
MAX_LOG=32*1024**2
MAX_META=2_000_000
MIN_FREE=10_000_000_000
MIN_RAM=8*1024**3
WHOLE_SECONDS=1800
CLEANUP_RESERVE=105

class Unavailable(ValueError):
    def __init__(self,reason='unavailable'):self.reason=reason;super().__init__('Simulator layout unavailable.')

class OutputUncertain(Unavailable):
    output_may_exist=True

def need(value,reason='unavailable'):
    if not value:raise Unavailable(reason)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def read_fixed(path,limit):
    path=Path(path).absolute();parts=path.parts[1:];need(0<len(parts)<=32,'source_refused');owned=[];failure=None
    try:
        rootfd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);owned.append(rootfd);parents=[];current=rootfd
        for component in parts[:-1]:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current);owned.append(child);info=os.fstat(child);parents.append((current,component,child,(info.st_dev,info.st_ino,info.st_mode)));current=child
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current);owned.append(fd);a=os.fstat(fd);need(stat.S_ISREG(a.st_mode)and a.st_size<=limit,'source_refused');raw=bytearray()
        while len(raw)<=limit:
            b=os.read(fd,min(65536,limit+1-len(raw)))
            if not b:break
            raw.extend(b)
        snap=lambda v:(v.st_dev,v.st_ino,v.st_mode,v.st_size,v.st_mtime_ns,v.st_ctime_ns)
        need(snap(a)==snap(os.fstat(fd))==snap(os.stat(parts[-1],dir_fd=current,follow_symlinks=False))and len(raw)==a.st_size,'source_changed')
        for parent,name,child,identity in parents:
            value=os.stat(name,dir_fd=parent,follow_symlinks=False);now=os.fstat(child);need(identity==(value.st_dev,value.st_ino,value.st_mode)==(now.st_dev,now.st_ino,now.st_mode),'source_changed')
        return bytes(raw)
    finally:
        while owned:
            fd=owned.pop()
            try:os.close(fd)
            except BaseException:failure=True
        if failure:raise Unavailable('read_cleanup_uncertain')


def pinned_module(name):
    raw=read_fixed(ROOT/name,262144);need(sha(raw)==PINS[name],'source_changed')
    n=types.ModuleType('private_ios_matrix_'+Path(name).stem);n.__dict__.update(__file__=str(ROOT/name),__name__=n.__name__)
    exec(compile(raw,str(ROOT/name),'exec'),n.__dict__);return n.__dict__

def profile_type(profile):
    need(type(profile)is str and profile in PROFILES,'unsupported_profile');return 'com.apple.CoreSimulator.SimDeviceType.'+PROFILES[profile]

def runtime_profile(raw,profile):
    need(type(raw)is bytes and len(raw)<=MAX_META,'metadata_limit');v=json.loads(raw);need(type(v)is dict and type(v.get('runtimes'))is list and len(v['runtimes'])<=16,'runtime_unavailable')
    selected=[x for x in v['runtimes']if type(x)is dict and x.get('identifier')==RUNTIME];need(len(selected)==1,'runtime_unavailable');x=selected[0]
    need(x.get('isAvailable')is True and x.get('buildversion')==BUILD and x.get('version')=='26.2','runtime_unavailable');wanted=profile_type(profile);types=x.get('supportedDeviceTypes');need(type(types)is list and len(types)<=128,'runtime_unavailable')
    rows=[z for z in types if type(z)is dict and z.get('identifier')==wanted];need(len(rows)==1 and rows[0].get('productFamily')=='iPhone','device_unavailable');return wanted

def toolchain_identity(version,sdk):
    need(version==b'Xcode 27.2\nBuild version 27B52' and sdk==b'27.2','toolchain_unavailable')
    return {'xcode':'27.2','xcode_build':'27B52','simulator_sdk':'27.2'}


class Clock:
    """A failed time source is sticky; it cannot reset an existing budget."""
    def __init__(self,raw=None):
        self.raw=time.monotonic if raw is None else raw;need(callable(self.raw),'clock_unavailable');self.first=None;self.last=None;self.failed=False
    def __call__(self):
        need(not self.failed,'clock_unavailable')
        try:
            value=self.raw()
            valid=type(value)in(int,float)and math.isfinite(value)
            if not valid or(self.last is not None and value<self.last):raise ValueError('invalid clock')
        except Exception:
            self.failed=True;raise Unavailable('clock_unavailable')from None
        if self.first is None:self.first=value
        self.last=value;return value


class Budget:
    def __init__(self,clock=None):
        self.clock=Clock(clock);self.start=self.clock();self.end=self.start+WHOLE_SECONDS;self.work_end=self.end-CLEANUP_RESERVE;self.ui_end=None
    def begin_ui(self):self.ui_end=min(self.work_end,self.clock()+780)
    def operation_end(self,*,cleanup=False,ui=False):
        end=self.end if cleanup else self.work_end
        if ui:need(self.ui_end is not None,'deadline');end=min(end,self.ui_end)
        return end-5
    def seconds(self,cap,*,cleanup=False,ui=False):
        # Owned child reap consumes the SAME original deadline.
        remaining=self.operation_end(cleanup=cleanup,ui=ui)-self.clock();need(math.isfinite(remaining)and remaining>0,'deadline');return min(cap,remaining)
    def check(self,*,ui=False):
        end=self.work_end if not ui else min(self.work_end,self.ui_end or 0);need(self.clock()<end,'deadline')


def process(argv,*,output,stage,timeout,metadata=False,cleanup=False,directory_fd=None,no_log=False,clock=None,stop_at=None):
    """One owned group. Cleanup is never conditional on diagnostics/free space."""
    need(type(argv)is list and argv and all(type(x)is str and x and '\0'not in x for x in argv),'command_refused')
    need(type(timeout)in(int,float)and math.isfinite(timeout)and 0<timeout<=600,'deadline')
    checked_clock=clock if isinstance(clock,Clock)else Clock(clock);started=checked_clock();deadline=started+timeout
    if stop_at is not None:
        need(type(stop_at)in(int,float)and math.isfinite(stop_at),'deadline');deadline=min(deadline,stop_at)
    need(started<deadline,'deadline');child=None;selector=None;pipe=None;log=None
    captured=bytearray();total=0;digest=hashlib.sha256();failure=None;cleanup_failure=False;logging_ok=not no_log
    def close_log():
        nonlocal log
        if log is not None:
            owned=log;log=None;os.close(owned)
    try:
        if not no_log:
            try:
                name=stage+'.log'
                log=os.open(name if directory_fd is not None else output/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,**({'dir_fd':directory_fd}if directory_fd is not None else{}))
            except OSError:
                if not cleanup:raise
                logging_ok=False
        need(checked_clock()<deadline,'deadline')
        child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'LANG':'en_US.UTF-8','DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'})
        try:
            pipe=child.stdout;selector=selectors.DefaultSelector();os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ);eof=False
            while not eof:
                remaining=deadline-checked_clock();need(remaining>0,'deadline')
                if not cleanup:need(shutil.disk_usage(output.parent).free>=2_000_000_000,'capacity_reserve')
                for key,_ in selector.select(min(.1,remaining)):
                    try:raw=os.read(key.fileobj.fileno(),min(65536,MAX_LOG-total+1))
                    except BlockingIOError:continue
                    if not raw:eof=True;break
                    need(len(raw)<=MAX_LOG-total,'log_limit');total+=len(raw);digest.update(raw)
                    if log is not None:
                        try:
                            view=memoryview(raw)
                            while view:
                                size=os.write(log,view);need(size>0,'log_unavailable');view=view[size:]
                        except (OSError,Unavailable):
                            if not cleanup:raise
                            logging_ok=False
                            try:close_log()
                            except OSError:pass
                    if metadata:need(total<=MAX_META,'metadata_limit');captured.extend(raw)
            remaining=deadline-checked_clock();need(remaining>0,'deadline');code=child.wait(timeout=remaining);need(code==0,'command_failed')
            if log is not None:
                try:os.fsync(log)
                except OSError:
                    if not cleanup:raise
                    logging_ok=False
        finally:
            if child.returncode is None:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                except BaseException:cleanup_failure=True
                try:child.wait(timeout=5)
                except BaseException:cleanup_failure=True
    except BaseException as e:failure=e
    finally:
        for obj in (selector,pipe):
            if obj is not None:
                try:obj.close()
                except BaseException:cleanup_failure=True
        try:close_log()
        except BaseException:
            if cleanup:logging_ok=False
            else:cleanup_failure=True
    final_clock_error=None
    try:need(checked_clock()<deadline,'deadline')
    except BaseException as error:final_clock_error=error if isinstance(error,Unavailable)else Unavailable('command_cancelled')
    def error(reason,original=None):
        value=original if isinstance(original,Unavailable)else Unavailable(reason)
        # Private transport facts, never included in public exception text.
        value.private_stdout=bytes(captured);value.child_started=child is not None
        value.child_returncode=child.returncode if child is not None else None
        return value
    if cleanup_failure:raise error('process_cleanup_uncertain')
    if failure is not None:raise error('command_unavailable',failure)from None
    if final_clock_error is not None:raise error(final_clock_error.reason)from None
    return {'stdout':bytes(captured),'bytes':total,'sha256':digest.hexdigest(),'returncode':child.returncode,'logging_ok':logging_ok}


def derive_payload(payload,fixture):
    need(type(payload)is dict and len(payload)==46 and 'Tests/UIFlows.swift'in payload and all(type(x)is bytes for x in payload.values()),'producer_changed')
    need(type(fixture)is bytes and 0<len(fixture)<=65536 and sha(fixture)==FIXTURE_SHA256,'fixture_refused');need(sha(payload['Tests/UIFlows.swift'])==LEGACY_UI_SHA256,'producer_changed');derived=dict(payload);derived['Tests/UIFlows.swift']=fixture
    changed=[n for n in payload if payload[n]!=derived[n]];need(changed==['Tests/UIFlows.swift'],'producer_changed');return derived,{'changed_members':changed,'unchanged_members':45,'original':{k:sha(v)for k,v in sorted(payload.items())},'derived':{k:sha(v)for k,v in sorted(derived.items())}}

def accepted(summary,tree,*,owned,profile):
    required={'totalTestCount':1,'passedTests':1,'failedTests':0,'skippedTests':0}
    if type(summary)is not dict or summary.get('result')!='Passed'or any(type(summary.get(k))is not int or summary[k]!=v for k,v in required.items())or summary.get('testFailures'):return False
    devices=summary.get('devicesAndConfigurations')
    if type(devices)is not list or len(devices)!=1 or type(devices[0])is not dict:return False
    device=devices[0].get('device');expected={'deviceId':owned,'modelName':MODEL_NAMES.get(profile),'osVersion':'26.2','osBuildNumber':BUILD,'platform':'iOS Simulator','architecture':'arm64'}
    if type(device)is not dict or any(device.get(k)!=v for k,v in expected.items()):return False
    tree_devices=tree.get('devices')if type(tree)is dict else None
    if type(tree_devices)is not list or len(tree_devices)!=1 or type(tree_devices[0])is not dict or any(tree_devices[0].get(k)!=v for k,v in expected.items()):return False
    pending=tree.get('testNodes')if type(tree)is dict else None
    if type(pending)is not list:return False
    pending=pending.copy();found=[];count=0
    while pending:
        n=pending.pop();count+=1
        if count>256 or type(n)is not dict or type(n.get('children',[]))is not list:return False
        if n.get('nodeType')=='Test Case':
            if n.get('nodeIdentifier')!=TEST_ID or n.get('result')!='Passed':return False
            found.append(n['nodeIdentifier'])
        pending.extend(n.get('children',[]))
    return found==[TEST_ID]

def cleanup_owned(owned,command,absent):
    result={'owned_created':owned is not None,'delete_passed':False,'inventory_absent':None,'removed':False,'diagnostics_retained':True}
    if owned is None:return result
    try:
        observed=command(['/usr/bin/xcrun','simctl','delete',owned],90,'delete',True);result['delete_passed']=True;result['diagnostics_retained']&=observed.get('logging_ok',True)
    except Exception:pass
    try:
        observed=command(['/usr/bin/xcrun','simctl','list','devices',owned,'--json'],15,'absence',True);result['diagnostics_retained']&=observed.get('logging_ok',True);result['inventory_absent']=absent(observed['stdout'].decode(),owned)
    except Exception:pass
    result['removed']=result['delete_passed']and result['inventory_absent']is True;return result

def write_private(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view);need(n>0,'output_unavailable');view=view[n:]
        os.fsync(fd)
    finally:os.close(fd)


def source_map(legacy):
    extra=['tools/ios_simulator_matrix.py','scripts/verify-ios-size-matrix.py','mobile/ios/Tests/SizeLayoutFlows.swift','docs/ios-simulator-matrix-plan.md','docs/ios-simulator-matrix.md']
    return {**legacy['source_hashes'](),**{n:sha(read_fixed(ROOT/n,262144))for n in extra}}

def one_device(profile,output,legacy,builder,capture):
    budget=Budget();owned=None;record={'profile':profile,'device_type':profile_type(profile),'runtime':RUNTIME,'runtime_build':BUILD,'pass':False,'configurations':[],'commands':[]};ui=False
    output_fd=capture.directory(output)
    def command(argv,cap,stage,cleanup=False,metadata=True):
        nonlocal owned
        record['active_stage']=stage;boundary_ok=True
        if cleanup:
            try:capture.check()
            except (ValueError,OSError):boundary_ok=False;record['cleanup_boundary_uncertain']=True
        else:capture.check()
        timeout=budget.seconds(cap,cleanup=cleanup,ui=ui and not cleanup)
        def register(raw):
            nonlocal owned
            owned=legacy['simulator_identity'](raw.decode().strip());record['owned_id']=owned
        try:
            result=process(argv,output=output,stage=stage,timeout=timeout,metadata=metadata,cleanup=cleanup,directory_fd=output_fd if boundary_ok else None,no_log=not boundary_ok,clock=budget.clock,stop_at=budget.operation_end(cleanup=cleanup,ui=ui and not cleanup))
        except Unavailable as failure:
            if stage=='create'and getattr(failure,'child_started',False):
                record['create_completion_uncertain']=True
                try:register(failure.private_stdout)
                except (ValueError,UnicodeError):record['create_identity_unavailable']=True
            raise
        if stage=='create':register(result['stdout'])
        if not cleanup:capture.check()
        need(budget.clock()<(budget.end if cleanup else min(budget.work_end,budget.ui_end if ui else budget.work_end)),'deadline')
        record['commands'].append({'stage':stage,'timeout':timeout,'bytes':result['bytes'],'sha256':result['sha256'],'logging_ok':result['logging_ok']})
        return result
    try:
        need(shutil.disk_usage(output.parent).free>=MIN_FREE,'capacity_reserve')
        raw=command(['/usr/sbin/sysctl','-n','hw.memsize','hw.logicalcpu'],5,'capacity')['stdout'].decode();capacity=legacy['host_capacity'](raw,shutil.disk_usage(output.parent).free);need(capacity['memory_bytes']>=MIN_RAM,'capacity_reserve');record['capacity']=capacity
        record['toolchain']=toolchain_identity(command(['/usr/bin/xcodebuild','-version'],15,'xcode-version')['stdout'].strip(),command(['/usr/bin/xcrun','--sdk','iphonesimulator','--show-sdk-version'],15,'sdk-version')['stdout'].strip())
        selected=runtime_profile(command(['/usr/bin/xcrun','simctl','list','runtimes','--json'],15,'runtimes')['stdout'],profile)
        record['sources_before']=source_map(legacy);payload=builder_files(builder);fixture=read_fixed(ROOT/'mobile/ios/Tests/SizeLayoutFlows.swift',65536);payload,record['payload']=derive_payload(payload,fixture)
        project=output/'project';project.mkdir(mode=0o700)
        for name,raw in sorted(payload.items()):
            path=Path(name);need(not path.is_absolute()and '..'not in path.parts,'producer_changed');target=project/path;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);write_private(target,raw)
        value=command(['/usr/bin/xcrun','simctl','create','AITrust-ID-Size-proof-'+uuid.uuid4().hex[:8],selected,RUNTIME],30,'create')['stdout'].decode().strip();owned=legacy['simulator_identity'](value)
        record['owned_id']=owned;command(['/usr/bin/xcrun','simctl','boot',owned],30,'boot');command(['/usr/bin/xcrun','simctl','bootstatus',owned,'-b','-d'],180,'bootstatus',metadata=False)
        base=['/usr/bin/xcodebuild','-project',str(project/'AITrustID.xcodeproj'),'-scheme','AITrustID','-sdk','iphonesimulator','-destination','platform=iOS Simulator,id='+owned,'-derivedDataPath',str(output/'derived'),'-parallel-testing-enabled','NO']
        command([*base,'build-for-testing','CODE_SIGNING_ALLOWED=NO','CODE_SIGNING_REQUIRED=NO','ONLY_ACTIVE_ARCH=YES'],600,'build',metadata=False)
        budget.begin_ui();ui=True
        for name,appearance,content in CONFIGS:
            command(['/usr/bin/xcrun','simctl','ui',owned,'appearance',appearance],15,name+'-appearance-set');readback=command(['/usr/bin/xcrun','simctl','ui',owned,'appearance'],15,name+'-appearance-read')['stdout'].decode().strip();need(readback==appearance,'configuration_mismatch')
            command(['/usr/bin/xcrun','simctl','ui',owned,'content_size',content],15,name+'-size-set');readback=command(['/usr/bin/xcrun','simctl','ui',owned,'content_size'],15,name+'-size-read')['stdout'].decode().strip();need(readback==content,'configuration_mismatch')
            result=output/(name+'.xcresult');command([*base,'-resultBundlePath',str(result),'-test-timeouts-enabled','YES','-default-test-execution-time-allowance','120','-maximum-test-execution-time-allowance','150','-only-testing:AITrustIDUITests/SizeLayoutFlows/testReadableControlsAndNotices','test-without-building','CODE_SIGNING_ALLOWED=NO','CODE_SIGNING_REQUIRED=NO','ONLY_ACTIVE_ARCH=YES'],300,name+'-ui',metadata=False)
            summary=json.loads(command(['/usr/bin/xcrun','xcresulttool','get','test-results','summary','--path',str(result),'--format','json'],30,name+'-summary')['stdout']);tree=json.loads(command(['/usr/bin/xcrun','xcresulttool','get','test-results','tests','--path',str(result)],30,name+'-tests')['stdout']);need(accepted(summary,tree,owned=owned,profile=profile),'layout_acceptance_failed');metrics=layout_metrics(read_fixed(output/(name+'-ui.log'),MAX_LOG));images=export_images(result,output,name,command,budget,capture);need(sum(x['bytes']for row in record['configurations']for x in row['images'])+sum(x['bytes']for x in images)<=32*1024**2,'screenshot_limit');record['configurations'].append({'metrics':metrics,'images':images,'configuration':name,'appearance':appearance,'content_size':content,'actual_test_count':1,'passed':1,'failed':0,'skipped':0})
        need(record['configurations'][2]['metrics']['titleh']>record['configurations'][0]['metrics']['titleh'],'content_size_not_observed')
        record['pass']=len(record['configurations'])==3
        need(all(read_fixed(project/n,len(raw)+1)==raw for n,raw in payload.items()),'derived_input_changed');budget.check(ui=True)
    except Exception as e:
        record['failed_stage']=record.get('active_stage','preflight');record['reason']=e.reason if isinstance(e,Unavailable)else 'unavailable';record['pass']=False
        # Read the actual failed result when available, without retrying a test.
        failed_config=next((n for n,_,_ in CONFIGS if record['failed_stage']==n+'-ui'),None)
        if failed_config is not None:
            try:
                result=output/(failed_config+'.xcresult');capture.directory(result)
                observed=json.loads(command(['/usr/bin/xcrun','xcresulttool','get','test-results','summary','--path',str(result),'--format','json'],30,failed_config+'-failed-summary')['stdout'])
                counts={k:observed.get(k)for k in ['totalTestCount','passedTests','failedTests','skippedTests']}
                need(all(type(x)is int and 0<=x<=100 for x in counts.values()),'failed_summary_unavailable')
                record['actual_failed_summary']={'result':observed.get('result')if observed.get('result')in('Passed','Failed','Unknown')else 'Unknown',**counts}
                record['failure_images']=export_images(result,output,failed_config+'-failure',command,budget,capture,required=False)
            except Exception:record['failure_diagnostics']='unavailable_within_original_budget; retained_xcresult_or_partial_logs'
    finally:
        ui=False;record['cleanup']=cleanup_owned(owned,command,legacy['simulator_absent'])
        if not record['cleanup']['removed']or not record['cleanup']['diagnostics_retained']or record.get('cleanup_boundary_uncertain'):record['pass']=False
        try:record['sources_after']=source_map(legacy);record['sources_unchanged']=record.get('sources_before')==record['sources_after']
        except Exception:record['sources_unchanged']=False
        if not record['sources_unchanged']:record['pass']=False
    try:
        if budget.clock()>=budget.end:record['pass']=False;record['reason']='deadline'
    except Unavailable:
        record['pass']=False;record['clock_uncertain']=True;record['reason']='clock_unavailable'
    record['physical_device']=False;record['human_accessibility']=False;record['seven_workflow_acceptance']=False;record['captured_at']=datetime.now(timezone.utc).isoformat();capture.save(output/'layout.json',record,MAX_META)
    if record['pass']:
        try:need(budget.clock()<budget.end,'deadline')
        except Unavailable:raise OutputUncertain('publication_clock_or_deadline')from None
    return record

def builder_files(builder):
    # Kept separate for inert producer-delta controls; no received code argument.
    return builder['files']()

def layout_metrics(raw):
    need(type(raw)is bytes and len(raw)<=MAX_LOG,'metadata_limit')
    rows=re.findall(rb'^LAYOUT_METRICS w=([0-9.]+) h=([0-9.]+) titleh=([0-9.]+) inputh=([0-9.]+)\r?$',raw,re.M)
    need(len(rows)==1,'layout_metrics_unavailable');values=[float(x)for x in rows[0]];need(all(math.isfinite(x)and 0<x<=4096 for x in values),'layout_metrics_unavailable');return dict(zip(['width','height','titleh','inputh'],values))


def export_images(result,output,name,command,budget,capture,required=True):
    target=output/(name+'-attachments')
    command(['/usr/bin/xcrun','xcresulttool','export','attachments','--path',str(result),'--output-path',str(target)],30,name+'-attachments',metadata=False)
    # SDK export is an OS operation, not a kernel storage quota. Inspect only the
    # fixed fixture's selected PNGs; automatic SDK attachments remain private.
    capture.directory(target);capture.check()
    manifest=read_fixed(target/'manifest.json',MAX_META);rows=json.loads(manifest)
    need(type(rows)is list and len(rows)<=4,'screenshot_unavailable');images=[];wanted={'size-layout-app','size-layout-notices','size-layout-evidence'}|({'size-layout-failure'}if not required else set())
    for row in rows:
        need(type(row)is dict and type(row.get('attachments'))is list and len(row['attachments'])<=1024,'screenshot_unavailable')
        for item in row['attachments']:
            namehint=item.get('suggestedHumanReadableName','');match=next((x for x in wanted if namehint==x or namehint.startswith(x+'_')),None)
            if match is None:continue
            filename=item.get('exportedFileName');need(type(filename)is str and Path(filename).name==filename and filename.endswith('.png'),'screenshot_unavailable')
            raw=read_fixed(target/filename,8*1024**2);need(len(raw)>=24 and raw[:8]==b'\x89PNG\r\n\x1a\n'and raw[12:16]==b'IHDR','screenshot_unavailable')
            width=int.from_bytes(raw[16:20],'big');height=int.from_bytes(raw[20:24],'big');need(0<width<=4096 and 0<height<=4096,'screenshot_unavailable')
            images.append({'role':match,'file':filename,'bytes':len(raw),'sha256':sha(raw),'pixel_width':width,'pixel_height':height})
    need(len(images)==len({x['role']for x in images}),'screenshot_unavailable')
    if required:need(len(images)==3 and {x['role']for x in images}==wanted,'screenshot_unavailable')
    need(sum(x['bytes']for x in images)<=32*1024**2,'screenshot_limit');budget.check(ui=True);return images


def complete_device(row):
    return (type(row)is dict and row.get('pass')is True and row.get('sources_unchanged')is True
        and row.get('cleanup',{}).get('removed')is True and row.get('cleanup',{}).get('diagnostics_retained')is True and not row.get('cleanup_boundary_uncertain')
        and [x.get('configuration')for x in row.get('configurations',[])]==[x[0]for x in CONFIGS]
        and all(type(x.get('actual_test_count'))is int and x['actual_test_count']==1 and x.get('passed')==1 and x.get('failed')==0 and x.get('skipped')==0 for x in row['configurations']))


def run(output,profiles):
    old_umask=os.umask(0o077)
    try:return _run(output,profiles)
    finally:os.umask(old_umask)


def _run(output,profiles):
    need(sys.platform=='darwin'and os.uname().machine=='arm64','unsupported_platform');need(type(profiles)is list and profiles and len(profiles)<=4 and len(set(profiles))==len(profiles),'unsupported_profile')
    for x in profiles:profile_type(x)
    legacy=pinned_module('scripts/verify-ios-share.py');builder=pinned_module('scripts/build-ios-project.py');evidence=pinned_module('tools/artifact_evidence_io.py');output=legacy['destination'](Path(output));need(shutil.disk_usage(output.parent).free>=MIN_FREE,'capacity_reserve')
    with evidence['Capture']() as capture:
        capture.parent(output)
        # Existing foundation refuses existing paths/Git roots; no stage deletion.
        legacy['create'](output,ROOT,{'context.json':b'{"synthetic_layout_only":true}\n'});capture.directory(output)
        records=[]
        for profile in profiles:
            capture.check();target=output/profile;target.mkdir(mode=0o700);capture.directory(target);row=one_device(profile,target,legacy,builder,capture);records.append(row)
            if not complete_device(row):row['pass']=False;break
        final_sources=source_map(legacy)
        need(all(x.get('sources_before')==x.get('sources_after')==final_sources for x in records),'source_changed')
        record={'format':'ios-representative-layout-matrix/v1','pass':len(records)==len(profiles)and all(x['pass']for x in records),'requested_profiles':profiles,'executed_profiles':[x['profile']for x in records],'devices':records,'scope':'Targeted layout software observations only; original14Plus7proof separate; not every model or physical/VoiceOver acceptance.','physical_device':False,'human_accessibility':False,'independent_accuracy':False,'new_original_closure':False,'visual_review_required':True,'visual_review_completed':False};capture.save(output/'matrix.json',record,MAX_META,prepublish=lambda:need(source_map(legacy)==final_sources,'source_changed'))
    if source_map(legacy)!=final_sources:raise OutputUncertain('source_changed_after_publication')
    return record
