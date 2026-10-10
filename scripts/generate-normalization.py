"""Generate frozen Unicode 15.0 tables using a matching Python, or check JS drift."""
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
path=ROOT/'protocol/unicode15-data.json'
if not args.check:
    if unicodedata.unidata_version != '15.0.0':raise SystemExit('Unicode 15.0.0 builder required')
    data={'unicode_version':'15.0.0','combining_classes':{},'canonical_decompositions':{},'compositions':{}}
    for cp in range(0x110000):
        if 0xD800<=cp<=0xDFFF:continue
        char=chr(cp);ccc=unicodedata.combining(char);decomp=unicodedata.decomposition(char)
        if ccc:data['combining_classes'][str(cp)]=ccc
        if decomp and not decomp.startswith('<'):
            values=[int(x,16) for x in decomp.split()];data['canonical_decompositions'][str(cp)]=values
            if len(values)==2 and unicodedata.normalize('NFC',''.join(map(chr,values)))==char:
                data['compositions'][','.join(map(str,values))]=cp
    path.write_text(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n')
raw=path.read_bytes();data=json.loads(raw);assert data['unicode_version']=='15.0.0'
body=(ROOT/'protocol/normalization-core.js').read_text()
header='// Generated; run scripts/generate-normalization.py. Unicode data license retained.\nconst TABLES = '+raw.decode().strip()+';\n'
for extension,export in [('mjs','export { normalizeNFC, NORMALIZATION_ID };\n'),('cjs','module.exports = { normalizeNFC, NORMALIZATION_ID };\n')]:
    target=ROOT/('protocol/normalization.'+extension);expected=header+body+'\n'+export
    if args.check:
        assert target.read_text()==expected,'Generated JavaScript drift'
    else:target.write_text(expected)
print(json.dumps({'unicode_version':'15.0.0','data_sha256':hashlib.sha256(raw).hexdigest(),'pass':True}))
