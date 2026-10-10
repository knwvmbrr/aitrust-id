"""Deterministic offline single-file editor; no dependency or remote resource."""
import argparse
import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build(root=ROOT):
    folder = root/'tools/composition'
    core = (folder/'core.cjs').read_text()
    editor = (folder/'editor.js').read_text()
    style = (folder/'style.css').read_text()
    def policy_hash(text):
        return "'sha256-"+base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()+"'"
    csp = "default-src 'none'; script-src "+policy_hash(core)+' '+policy_hash(editor)+"; style-src "+policy_hash(style)+"; connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
    html = (folder/'editor.html').read_text()
    for key, value in {'__CORE__':core,'__EDITOR__':editor,'__STYLE__':style,'__CSP__':csp,'__METHOD_SHA__':hashlib.sha256(core.encode()).hexdigest()}.items():
        html = html.replace(key,value)
    return html.encode()

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='output/composition/editor.html');args=parser.parse_args()
    target=ROOT/args.output
    if Path(args.output).is_absolute() or '..' in Path(args.output).parts or not args.output.startswith('output/') or target.suffix!='.html':parser.error('Output must be an HTML file under output/')
    if any(p.is_symlink() for p in [target,*target.parents]):parser.error('Symlink destination refused')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(build())
    print('Built offline editor:',args.output)
