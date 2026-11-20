#!/usr/bin/env python3
"""Compile and execute the Android session controller with an existing JDK only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--java-home',required=True);args=parser.parse_args()
    try:
        home=Path(args.java_home).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix='aitrust-android-session-') as temp:
            compile=subprocess.run([str(home/'bin/javac'),'-encoding','UTF-8','-d',temp,str(ROOT/'mobile/android/src/com/aitrustid/android/ShareSession.java'),str(ROOT/'mobile/android/tests/ShareSessionTest.java')],capture_output=True,timeout=30)
            if compile.returncode:raise ValueError()
            run=subprocess.run([str(home/'bin/java'),'-ea','-cp',temp,'com.aitrustid.android.ShareSessionTest'],capture_output=True,timeout=10)
            if run.returncode:raise ValueError()
        print(json.dumps({'pass':True,'runtime':'actual installed JVM','checks':['Unicode/codepoint input bounds','no automatic checking','edit invalidates pending result','duplicate/stale result refusal','cancel preserves editable input','clear/background invalidates result and text','invalid input cannot start'],'android_runtime_executed':False,'independent_accuracy_evidence':False}));return 0
    except (OSError,ValueError,subprocess.SubprocessError):
        print('Android session verification unavailable: an existing supported JDK and passing controls are required.');return 2
if __name__=='__main__':raise SystemExit(main())
