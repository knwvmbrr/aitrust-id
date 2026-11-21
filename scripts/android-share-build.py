#!/usr/bin/env python3
"""Prepare verified offline Android PS assets and compile with an existing SDK; never install tools."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.corpus import read_regular
from scripts.asset_notices import runtime_origin, RUNTIME_FILES

OUTPUT=ROOT/'output/android-share'
PROFILE='ai-trust-id-android-assets/v1'

def require(condition):
    if not condition:raise ValueError('Android preparation refused an unsupported source or build boundary.')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def load(path,limit=2097152):return json.loads(read_regular(Path(path),limit))
def write(path,raw):
    require(not any(p.is_symlink() for p in [path,*path.parents]))
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():require(path.is_file())
    path.write_bytes(raw)

def prepare(runtime):
    runtime=Path(runtime).resolve(strict=True)
    require(load(runtime/'package.json')['version']=='314.0.7')
    retained=load(ROOT/'sbom/assets/notices.json')
    require(retained['profile']=='selected-asset-notices/v1' and retained['runtime_origin']==runtime_origin(ROOT))
    members=retained['runtime_members'];require(len(members)==5 and {x['name'] for x in members}==set(RUNTIME_FILES))
    payload={}
    for row in members:
        require(set(row)=={'name','member','sha256','bytes'} and row['member']=='package/'+row['name'] and type(row['bytes']) is int and 0<row['bytes']<=33554432)
        raw=read_regular(runtime/row['name'],33554432)
        require(len(raw)==row['bytes'] and digest(raw)==row['sha256']);payload['runtime/'+row['name']]=raw
    spec=importlib.util.spec_from_file_location('android_projection',ROOT/'scripts/build-device-detector.py')
    projection=importlib.util.module_from_spec(spec);spec.loader.exec_module(projection)
    method,method_hash=projection.project(read_regular(ROOT/'services/evaluator/app.py',2097152))
    manifest={'method_sha256':method_hash,'bundle_sha256':digest(method),'path':'/device/method-'+digest(method)+'.py','runtime':'314.0.7','max_codepoints':20000,'normalization_id':'NFC-Unicode-15.0.0/v1','normalization_data_sha256':digest(read_regular(ROOT/'protocol/unicode15-data.json',2097152))}
    payload['method.py']=method
    payload['device-manifest.json']=(json.dumps(manifest,sort_keys=True)+'\n').encode()
    for name in ('index.html','bridge.mjs'):payload[name]=read_regular(ROOT/'mobile/android/web'/name,65536)
    inventory={'format':PROFILE,'method_sha256':method_hash,'files':{name:{'sha256':digest(raw),'bytes':len(raw)} for name,raw in sorted(payload.items())}}
    inventory_raw=(json.dumps(inventory,sort_keys=True)+'\n').encode()
    payload['asset-manifest.json']=inventory_raw
    notice_paths=['site/public/device-licenses/'+name for name in ('pyodide-MPL-2.0.txt','python-license.txt','source.txt','unicode-license.txt')]
    for name in notice_paths:
        raw=read_regular(ROOT/name,2097152)
        observed=next((x for x in [*retained['assets'],*(n for row in retained['assets'] for n in row['notices'])] if x['path']==name),None)
        require(observed is not None and observed['sha256']==digest(raw) and observed['bytes']==len(raw))
        payload['notices/'+Path(name).name]=raw
    require(payload['notices/unicode-license.txt']==read_regular(ROOT/'eval/vectors/unicode/LICENSE.txt',2097152))
    payload['notices/Apache-2.0.txt']=read_regular(ROOT/'LICENSE',65536)
    assets=OUTPUT/'assets'
    if assets.exists():
        require(not assets.is_symlink())
        old={p.relative_to(assets).as_posix() for p in assets.rglob('*') if p.is_file()}
        require(old<=set(payload) and not any(p.is_symlink() for p in assets.rglob('*')))
    for name,raw in payload.items():write(assets/name,raw)
    identity=('package com.aitrustid.android;\nfinal class BuildIdentity {\n static final String METHOD_SHA256="'+method_hash+'";\n static final String ASSET_MANIFEST_SHA256="'+digest(inventory_raw)+'";\n}\n').encode()
    write(OUTPUT/'generated/com/aitrustid/android/BuildIdentity.java',identity)
    result={'format':'ai-trust-id-android-preparation/v1','pass':True,'method_sha256':method_hash,'bundle_sha256':digest(method),'runtime':'314.0.7','verified_runtime_members':5,'assets':len(payload),'asset_bytes':sum(len(x) for x in payload.values()),'asset_manifest_sha256':digest(inventory_raw),'notices_consistency_only':True,'license_clearance':False,'independent_accuracy_evidence':False}
    write(OUTPUT/'preparation.json',(json.dumps(result,indent=2)+'\n').encode())
    return result

def command(argv,timeout=120):
    p=subprocess.run([str(x) for x in argv],cwd=ROOT,capture_output=True,timeout=timeout)
    if p.returncode:raise ValueError('Android SDK compilation failed; inspect private local build output rather than publishing input or host paths.')
    return p.stdout

def activity_sources(stage,intake_probe=False):
    """The diagnostic variant changes only one exact class declaration.

    Default builds never read or compile the wrapper. Method bodies, manifest,
    permissions and resources are shared, but the probe APK is a distinct variant.
    """
    original=ROOT/'mobile/android/src/com/aitrustid/android/CheckActivity.java'
    sources=sorted((ROOT/'mobile/android/src').rglob('*.java'))
    if not intake_probe:return sources,None
    raw=read_regular(original,65536)
    declaration=b'public final class CheckActivity extends Activity {'
    require(raw.count(declaration)==1 and raw.count(b'CheckActivity')==1)
    overlay=Path(stage)/'intake-probe';overlay.mkdir()
    base=overlay/'IntakeActivityBase.java'
    base.write_bytes(raw.replace(declaration,b'class IntakeActivityBase extends Activity {',1))
    wrapper=read_regular(ROOT/'tests/android/CheckActivity.java',16384)
    target=overlay/'CheckActivity.java';target.write_bytes(wrapper)
    return [p for p in sources if p!=original]+[base,target],{
        'variant':'intake-provenance-only/v1','production_activity_sha256':digest(raw),
        'wrapper_sha256':digest(wrapper),'compiled_base_sha256':digest(base.read_bytes()),
        'production_equivalent_apk':False,
    }


def verify_probe_dex(apk,intake_probe):
    """Refuse a mislabeled variant using fixed markers in the compiled DEX."""
    raw=read_regular(Path(apk),64*1024*1024)
    with io.BytesIO(raw) as stream:
        require(len(raw)>=22)
        # Bound classic ZIP entry count before ZipFile allocates its file list.
        stream.seek(max(0,len(raw)-65557));tail=stream.read(65557)
        index=tail.rfind(b'PK\x05\x06');require(index>=0 and len(tail)-index>=22)
        signature,disk,central_disk,disk_count,count,size,offset,comment=struct.unpack('<4s4H2LH',tail[index:index+22])
        require(disk==central_disk==0 and disk_count==count and 1<=count<=64)
        require(len(tail)-index==22+comment and offset+size==len(raw)-22-comment)
        with zipfile.ZipFile(stream) as archive:
            rows=archive.infolist();names=[row.filename for row in rows]
            require(len(rows)==count and len(set(names))==count and all(row.orig_filename==row.filename for row in rows))
            require(sum(row.file_size for row in rows)<=64*1024*1024)
            members=[row for row in rows if '/' not in row.filename and row.filename.lower().endswith('.dex')]
            require(sorted(row.filename for row in members)==['classes.dex','classes2.dex','classes3.dex','classes4.dex'][:len(members)])
            require(1<=len(members)<=4 and sum(row.file_size for row in members)<=16*1024*1024)
            payload=b''.join(archive.read(row) for row in members)
    present=[marker in payload for marker in (b'AITRUST_INTAKE_V1:',b'Lcom/aitrustid/android/IntakeActivityBase;')]
    require(present==[intake_probe,intake_probe])


def compile_apk(sdk,java_home,intake_probe=False):
    sdk=Path(sdk).resolve(strict=True);java_home=Path(java_home).resolve(strict=True)
    tools=sdk/'build-tools/36.0.0';platform=sdk/'platforms/android-36/android.jar'
    required=[tools/name for name in ('aapt2','d8','zipalign','apksigner')]+[platform,java_home/'bin/java',java_home/'bin/javac']
    require(all(path.is_file() for path in required))
    require((OUTPUT/'preparation.json').is_file())
    # Never invoke sdkmanager, accept a license, download an SDK or write outside output.
    env={**os.environ,'JAVA_HOME':str(java_home),'PATH':str(java_home/'bin')+os.pathsep+os.environ.get('PATH','')}
    def run(argv):
        process=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,capture_output=True,timeout=120)
        write(OUTPUT/'last-build.log',process.stdout+process.stderr)
        if process.returncode:raise ValueError('Android SDK compilation failed; inspect output/android-share/last-build.log locally.')
        return process.stdout
    with tempfile.TemporaryDirectory(prefix='compile-',dir=OUTPUT) as temporary:
        stage=Path(temporary);generated=stage/'generated';classes=stage/'classes';dex=stage/'dex'
        for directory in (generated,classes,dex):directory.mkdir()
        run([tools/'aapt2','compile','--dir',ROOT/'mobile/android/res','-o',stage/'resources.zip'])
        run([tools/'aapt2','link','-o',stage/'resources.apk','-I',platform,'--manifest',ROOT/'mobile/android/AndroidManifest.xml','--java',generated,'-A',OUTPUT/'assets',stage/'resources.zip'])
        sources,probe=activity_sources(stage,intake_probe)
        sources+=sorted((OUTPUT/'generated').rglob('*.java'))+sorted(generated.rglob('*.java'))
        # The Android stub JAR supplies platform types, not javac's compiler
        # bootstrap classes. D8 checks the Android platform and min API below.
        run([java_home/'bin/javac','-encoding','UTF-8','--release','8','-classpath',platform,'-d',classes,*sources])
        run([tools/'d8','--release','--min-api','29','--lib',platform,'--output',dex,*sorted(classes.rglob('*.class'))])
        unsigned=stage/'unpacked.apk';shutil.copyfile(stage/'resources.apk',unsigned)
        with zipfile.ZipFile(unsigned,'a',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(dex.glob('*.dex')):archive.write(path,path.name)
        destination=OUTPUT/('ai-trust-id-intake-probe-unsigned.apk' if intake_probe else 'ai-trust-id-unsigned.apk')
        if destination.exists():require(destination.is_file() and not destination.is_symlink());destination.unlink()
        run([tools/'zipalign','-f','-P','16','4',unsigned,destination])
        verify_probe_dex(destination,intake_probe)
        permissions=run([tools/'aapt2','dump','permissions',destination]).decode()
        require('uses-permission:' not in permissions and 'uses-permission-sdk-' not in permissions)
        result={'format':'ai-trust-id-android-build/v1','pass':True,'apk_sha256':digest(destination.read_bytes()),'apk_bytes':destination.stat().st_size,'sdk_platform':'android-36','build_tools':'36.0.0','permission_count':0,'signed':False,'preparation_sha256':digest((OUTPUT/'preparation.json').read_bytes()),'method_sha256':load(OUTPUT/'preparation.json')['method_sha256'],'emulator_executed':False,'physical_device_evidence':False,'independent_accuracy_evidence':False,'sources':{p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in sorted((ROOT/'mobile/android').rglob('*')) if p.is_file()}}
        if probe is not None:result['diagnostic_variant']=probe
        write(OUTPUT/'build.json',(json.dumps(result,indent=2)+'\n').encode());return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-directory',required=True)
    parser.add_argument('--compile',action='store_true')
    parser.add_argument('--intake-probe',action='store_true',help='Compile a separately named diagnostic APK; never a production-equivalent proof.')
    parser.add_argument('--sdk-root');parser.add_argument('--java-home')
    args=parser.parse_args()
    try:
        result=prepare(args.runtime_directory)
        require(not args.intake_probe or args.compile)
        if args.compile:
            if not args.sdk_root or not args.java_home:raise ValueError('Compilation requires an existing SDK root and JDK home; nothing was downloaded.')
            result=compile_apk(args.sdk_root,args.java_home,args.intake_probe)
        print(json.dumps(result,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,StopIteration,subprocess.SubprocessError):
        print('Android build unavailable: required installed tools or verified assets are missing or unsupported. No toolchain was downloaded.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
