"""Run full Unicode NFC conformance in Python and Node plus measured regressions."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

def verify():
    source=ROOT/'eval/vectors/unicode/NormalizationTest-15.0.0.txt'
    rows=[]
    for line in source.read_text().splitlines():
        line=line.split('#')[0].strip()
        if not line or line.startswith('@'):continue
        cols=[''.join(chr(int(cp,16)) for cp in field.split()) for field in line.split(';')[:5]]
        expected=[cols[1],cols[1],cols[1],cols[3],cols[3]]
        for value,wanted in zip(cols,expected):assert normalize_nfc(value)==wanted,repr(cols)
        rows.append([cols,expected])
    gap=json.loads((ROOT/'runs/2026-10-10-normalization-version-gap.json').read_text())
    regressions=gap['examples']
    for row in regressions:assert normalize_nfc(row['input'])==row['python_nfc']
    rows.extend([[[row['input']],[row['python_nfc']]] for row in regressions])
    program='''const {normalizeNFC}=require('./protocol/normalization.cjs');
const rows=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
let checks=0;for(const [values,expected] of rows)for(let i=0;i<values.length;i++){
 if(normalizeNFC(values[i])!==expected[i])throw Error('NFC conformance mismatch');checks++;
} process.stdout.write(JSON.stringify({checks, unicode:process.versions.unicode}));'''
    result=subprocess.run(['node','-e',program],cwd=ROOT,input=json.dumps(rows),capture_output=True,text=True,check=True,timeout=60)
    node=json.loads(result.stdout)
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'normalization_id':NORMALIZATION_ID,
        'official_source':'https://www.unicode.org/Public/15.0.0/ucd/NormalizationTest.txt',
        'official_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'official_vectors':len(rows)-len(regressions),'NFC_checks_per_implementation':(len(rows)-len(regressions))*5,
        'measured_version_regressions':len(regressions),'node':node,
        'tables_sha256':hashlib.sha256((ROOT/'protocol/unicode15-data.json').read_bytes()).hexdigest(),
        'independent_accuracy_evidence':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=verify()
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
