"""Atomic public-report writing; committed run destinations cannot be overwritten."""
import json
import os
from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]

def write_report(target, record, root=ROOT, allow_external=False):
    root=Path(root).resolve();file=root/target if not Path(target).is_absolute() else Path(target)
    try:relative=file.relative_to(root)
    except ValueError:
        if not allow_external or not Path(target).is_absolute() or file.suffix!='.json' or '..' in file.parts:raise ValueError('Invalid report destination') from None
        relative=None
    if relative is not None and (not relative.parts or relative.parts[0] not in ('runs','output') or file.suffix!='.json' or '..' in relative.parts):
        raise ValueError('Invalid report destination')
    for current in [file,*file.parents]:
        if current==root:break
        if current.is_symlink():raise ValueError('Report symlink refused')
    text=json.dumps(record,indent=2,allow_nan=False)+'\n'
    file.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=file.parent,prefix='.report-',delete=False) as stream:
            temporary=Path(stream.name);stream.write(text);stream.flush();os.fsync(stream.fileno())
        if relative is None or relative.parts[0]=='runs':os.link(temporary,file);temporary.unlink()
        else:os.replace(temporary,file)
        temporary=None
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return file
