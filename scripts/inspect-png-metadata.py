#!/usr/bin/env python3
"""Read local PNG details without showing embedded text or uploading an image."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys

ROOT=Path(__file__).resolve().parents[1]
PROFILE='png-metadata-preflight/1.0.0'
class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('invalid_request')

def worker(tool):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(2,2))
    if sys.platform=='linux':resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    raw=sys.stdin.buffer.read(tool.MAX_INPUT+1)
    try:result=tool.inspect_bytes(raw)
    except tool.ImageError as error:result=tool.unavailable(error.reason,raw)
    encoded=json.dumps(result,ensure_ascii=True,separators=(',',':')).encode()
    if len(encoded)>tool.MAX_OUTPUT:return 2
    sys.stdout.buffer.write(encoded);return 0

def main(argv=None):
    mode='text';tool=None
    try:
        parser=Parser(description=__doc__);parser.add_argument('--image',help='Explicit selected local PNG');parser.add_argument('--format',choices=('text','json'),default='text',help='JSON includes a linkable file hash; default text omits it');parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args(argv);mode=args.format
        sys.path.insert(0,str(ROOT));from tools import png_metadata as tool
        if tool.PROFILE!=PROFILE:raise ValueError('worker_unavailable')
        if args.worker:
            if args.image is not None or args.format!='text':raise ValueError('invalid_request')
            return worker(tool)
        if args.image is None:raise ValueError('invalid_request')
        result=tool.inspect_file(args.image)
        if mode=='json':
            result['implementation_sha256']=hashlib.sha256(Path(tool.__file__).read_bytes()).hexdigest();result['sharing_warning']='The file hash can link a private image. Raw metadata is omitted.'
            print(json.dumps(result,ensure_ascii=True,indent=2))
        else:print(tool.text_result(result))
        return 0 if result['state']=='OBSERVED'else 2
    except Exception as error:
        reason=error.reason if tool is not None and isinstance(error,tool.ImageError)else 'invalid_request'if type(error)is ValueError and str(error)=='invalid_request'else'worker_unavailable'
        result={'profile':PROFILE,'state':'UNAVAILABLE','reason':reason,'metadata_values_returned':False,'watermark_verified':False,'C2PA_inspected':False,'AI_origin':'unknown','content_truth_established':False,'tags':[]}
        if mode=='json':print(json.dumps(result))
        else:
            # Do not depend on a failed optional module to present its failure.
            messages={'unsupported_format':'This file format is not supported. Choose a PNG.','unsupported_variant':'This PNG variant is not supported by this reader.','corrupt_container':'The PNG structure could not be read.','corrupt_image_data':'The PNG image data could not be read.','corrupt_text_metadata':'A stored text section could not be read.','input_limit':'This image exceeds the supported size limits.','metadata_limit':'The stored metadata exceeds the supported limits.','source_unavailable':'The selected regular file could not be read.','invalid_request':'Choose a supported local PNG file.'}
            print('AI TRUST ID · PNG details\n'+messages.get(reason,'The image check did not complete.')+'\nAI origin: Unknown. No tag issued.')
        return 2
if __name__=='__main__':raise SystemExit(main())
