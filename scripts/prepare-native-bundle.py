#!/usr/bin/env python3
"""Prepare exact public assets for native engine verification; not an installable iPhone app."""
import argparse
import io
import json
from pathlib import Path
import sys
import zipfile
from native_bundle import assets, ROOT

sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        payload = assets()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            for name, raw in sorted(payload.items()):
                if Path(name).is_absolute() or '..' in Path(name).parts:
                    raise ValueError('Unsafe resource path')
                item = zipfile.ZipInfo(name); item.external_attr = 0o100600 << 16
                package.writestr(item, raw, compress_type=zipfile.ZIP_DEFLATED)
        create(a.output, ROOT, {'AI-Trust-ID-native-assets.zip': archive.getvalue()})
        print(json.dumps({'pass': True, 'public_files_written': len(payload),
                          'credentials_generated': False, 'phone_signing_configured': False,
                          'installable_app': False, 'independent_accuracy_evidence': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, PacketError):
        print('Native bundle unavailable: prepare current public assets and choose a new private folder outside the checkout.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
