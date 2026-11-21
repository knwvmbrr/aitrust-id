#!/usr/bin/env python3
"""Serve remote PS tools on loopback behind an operator-reviewed HTTPS proxy."""
import argparse
import logging
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('Operator configuration refused')

def main(argv=None):
    import uvicorn
    from tools.remote_tag_server import Application
    parser=Parser(description=__doc__)
    parser.add_argument('--port',type=int,default=8790)
    parser.add_argument('--allowed-host',action='append')
    parser.add_argument('--allowed-origin',action='append',default=[])
    args=parser.parse_args(argv)
    if not 1024<=args.port<=65535:raise ValueError('Refused')
    app=Application(args.allowed_host or ['127.0.0.1:'+str(args.port)],args.allowed_origin)
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False,log_config=None,log_level='critical',proxy_headers=False,server_header=False,date_header=False,limit_concurrency=16,timeout_keep_alive=2,timeout_graceful_shutdown=15)
if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt):
        print('AI Trust ID remote connector closed or unavailable.',file=sys.stderr);raise SystemExit(1)
