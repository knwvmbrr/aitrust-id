"""Validate exact development-row identity and declared, bounded provenance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.categories import category_for_text,CATEGORY_VERSION
DEFAULT=ROOT/'eval/datasets/unsafe_code'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def verify(folder=DEFAULT, verify_history=False):
    folder=Path(folder);manifest=json.loads((folder/'manifest.json').read_text());sidecar=json.loads((folder/'provenance-v1.json').read_text())
    if sidecar.get('format')!='development-example-provenance/v1' or sidecar.get('independent_accuracy_evidence') is not False:raise ValueError('Unsupported provenance or independence claim')
    if sidecar.get('manifest_sha256')!=digest((folder/'manifest.json').read_bytes()):raise ValueError('Provenance manifest mismatch')
    if sidecar.get('category_version')!=CATEGORY_VERSION:raise ValueError('Unknown category contract')
    rows=sidecar['examples'];by={r['id']:r for r in rows}
    if len(by)!=len(rows):raise ValueError('Duplicate example identity')
    seen=[];checked_origins=set()
    for group in ('active','historical'):
        for file in manifest[group]:
            name=file['file']
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.jsonl',name):raise ValueError('Invalid source basename')
            raw=(folder/name).read_bytes()
            if digest(raw)!=file['sha256']:raise ValueError('Dataset revision mismatch')
            for line,raw_row in enumerate(raw.splitlines(),1):
                row=json.loads(raw_row);rid=name+':'+str(line);record=by.get(rid)
                if not record or record['dataset_group']!=group or record['source_file']!=name or record['source_row']!=line:raise ValueError('Missing or misplaced provenance row')
                if record['source_file_sha256']!=digest(raw) or record['row_sha256']!=digest(raw_row) or record['text_sha256']!=digest(row['text'].encode()):raise ValueError('Example identity mismatch')
                if record.get('development_category')!=category_for_text(row['text']):raise ValueError('Category provenance mismatch')
                if record['declared_labels']!=row['labels'] or record['label_basis']!='maintainer_supplied_development; not blind independent ground truth':raise ValueError('Invalid label provenance')
                if record['author_attribution'] is not None or record['independent_labeler'] is not False:raise ValueError('Unsupported author or independence attribution')
                origin=record['origin']
                if origin['kind']!='exact_published_source_snapshot' or not re.fullmatch(r'[a-f0-9]{40}',origin['commit']) or datetime.fromisoformat(origin['committed_at']).tzinfo is None:raise ValueError('Invalid source-origin record')
                key=(name,origin['commit'])
                if verify_history and key not in checked_origins:
                    canonical='eval/datasets/unsafe_code/'+name
                    published=subprocess.run(['git','show',origin['commit']+':'+canonical],cwd=ROOT,capture_output=True,check=True,timeout=10).stdout
                    committed=subprocess.run(['git','show','-s','--format=%cI',origin['commit']],cwd=ROOT,capture_output=True,text=True,check=True,timeout=10).stdout.strip()
                    if digest(published)!=digest(raw) or committed!=origin['committed_at']:raise ValueError('Source-origin evidence mismatch')
                    checked_origins.add(key)
                if 'source_row' in row:
                    old=row['source_row'];previous=json.loads((folder/old['file']).read_bytes().splitlines()[old['row']-1]);
                    if previous['text']!=row['text'] or record['supersedes_source_row']!=old:raise ValueError('Broken supersession provenance')
                seen.append(rid)
    if set(seen)!=set(by):raise ValueError('Orphan provenance record')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'examples':len(seen),'active_examples':sum(r['dataset_group']=='active' for r in rows),'historical_examples':sum(r['dataset_group']=='historical' for r in rows),'manifest_sha256':digest((folder/'manifest.json').read_bytes()),'provenance_sha256':digest((folder/'provenance-v1.json').read_bytes()),'source_history_verified':verify_history,'unknown_author_attribution_preserved':True,'independent_accuracy_evidence':False,'origin_scope':'exact source commit and recorded commit time; not original authorship or creation time'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=DEFAULT);p.add_argument('--verify-history',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();r=verify(a.folder,a.verify_history)
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
