"""Optional private quotation export. No observation, annotation or tag execution."""
import os
from pathlib import Path
import stat
import sys

FILENAME='mobile-authority-quotation.json'
MAX_BYTES=8*1024*1024
class ExportRefused(ValueError):
    def __init__(self):super().__init__('Private quotation export unavailable.')
class ExportUncertain(ExportRefused):
    def __init__(self):ValueError.__init__(self,'Private output may remain; do not use it as accepted evidence.')

def target_path(path):
    """Only fixed OS aliases may change; final leaf and other links are not resolved."""
    path=Path(path).expanduser().absolute()
    if '..' in path.parts or len(path.parts)<2 or len(str(path))>4096:
        raise ExportRefused()
    # The alias must be a PARENT component, never the selected final leaf.
    if len(path.parts)>2 and path.parts[1] in ('tmp','var'):
        alias=Path('/')/path.parts[1]
        info=alias.lstat()
        if stat.S_ISLNK(info.st_mode):
            name=path.parts[1]
            if (sys.platform!='darwin' or info.st_uid!=0
                    or os.readlink(alias) not in ('private/'+name,'/private/'+name)):
                raise ExportRefused()
            path=Path('/private')/name/Path(*path.parts[2:])
    return path

def save_details(path,raw):
    """Fixed filename, explicit owner-held private parent, no overwrite or unsafe rollback."""
    capture=None
    try:
        if type(raw)is not bytes or not 0<len(raw)<=MAX_BYTES:raise ExportRefused()
        target=target_path(path)
        from tools import mt_label_io as private_io
        capture=private_io.Capture()
        with capture:
            capture.create(target,{FILENAME:raw})
    except BaseException:
        # Capture tracks uncertainty even after real close or attempted rollback.
        if capture is not None and capture.output_may_exist:
            raise ExportUncertain() from None
        raise ExportRefused() from None
