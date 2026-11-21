#!/usr/bin/env python3
"""Render reviewable candidates only; no service/network/account activation."""
import argparse
import re
from pathlib import Path

HOST='vps-18ef1326.vps.ovh.us'
CADDY_VERSION='2.11.2-1~bpo13+1'
CADDY_SHA256='e11c13b0e0e62ec7b28a04add94b9af276c27fa8e7ee6c0da6165fb7cb8c3989'

def caddyfile(front_port=None, app_port=8790):
    if type(app_port) is not int or not 1024<=app_port<=65535:raise ValueError('Configuration refused')
    if front_port is not None and (type(front_port) is not int or not 1024<=front_port<=65535 or front_port==app_port):raise ValueError('Configuration refused')
    site=f'http://:{front_port}' if front_port else 'https://'+HOST
    bind='    bind 127.0.0.1\n' if front_port else ''
    tls='' if front_port else '''    tls {
        protocols tls1.2 tls1.3
        issuer acme {
            disable_http_challenge
        }
    }
'''
    proxy=f'''reverse_proxy 127.0.0.1:{app_port} {{
                header_up -Authorization
                header_up -Cookie
                header_up -Forwarded
                header_up -X-Forwarded-For
                header_up -X-Forwarded-Host
                header_up -X-Forwarded-Proto
                header_up -Proxy-Authorization
                transport http {{
                    dial_timeout 1s
                    response_header_timeout 13s
                    max_response_header 8192
                    max_conns_per_host 16
                    compression off
                    keepalive off
                }}
            }}'''
    forbidden=['Authorization','Proxy-Authorization','Cookie','Origin','Content-Encoding','Transfer-Encoding','Mcp-Session-Id','Last-Event-Id']
    rules='\n'.join(f'        @refuse{i} header {name} *\n        respond @refuse{i} "Request refused." 400' for i,name in enumerate(forbidden))
    return f'''{{
    admin off
    persist_config off
    auto_https disable_redirects
    log {{
        output discard
    }}
    grace_period 15s
    servers {{
        protocols h1 h2
        max_header_size 8192
        timeouts {{
            read_header 3s
            read_body 12s
            write 15s
            idle 5s
        }}
    }}
}}
{site} {{
{bind}{tls}    route {{
        header {{
            -Server
            Cache-Control "no-store"
            X-Content-Type-Options "nosniff"
            Referrer-Policy "no-referrer"
            Content-Security-Policy "default-src 'none'; frame-ancestors 'none'"
        }}
        @wronghost not host {HOST}
        respond @wronghost "Request refused." 403
        @query expression `{{http.request.uri.query}} != ""`
        respond @query "Request refused." 400
{rules}
        @read {{
            method GET
            path /healthz /v1/tags
        }}
        handle @read {{
            {proxy}
        }}
        @check {{
            method POST
            path /mcp /v1/check
        }}
        handle @check {{
            request_body {{
                max_size 256000
            }}
            {proxy}
        }}
        respond "Request unavailable." 404
    }}
    handle_errors {{
        header {{
            -Server
            Cache-Control "no-store"
            X-Content-Type-Options "nosniff"
            Content-Security-Policy "default-src 'none'; frame-ancestors 'none'"
        }}
        respond "Request unavailable." {{err.status_code}}
    }}
}}
'''

def units(commit):
    if type(commit) is not str or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Configuration refused')
    base='/opt/aitrustid-ai-tools/releases/'+commit
    common='''DynamicUser=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
LockPersonality=yes
RestrictNamespaces=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
UMask=0077
LimitNOFILE=256
LimitCORE=0
MemorySwapMax=0
CPUQuota=100%
TasksMax=64
OOMPolicy=kill
KillMode=control-group
TimeoutStopSec=20s
StandardOutput=null
StandardError=null
Restart=on-failure
RestartSec=5s
'''
    app=f'''[Unit]
Description=AI Trust ID isolated remote PS tools
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=3
[Service]
{common}User=aitrustid-ai-tools
WorkingDirectory={base}/source
ExecStart={base}/venv/bin/python -I -B {base}/source/scripts/remote-tag-server.py --port 8790 --allowed-host {HOST} --allowed-host {HOST}:443
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONNOUSERSITE=1
MemoryMax=384M
IPAddressDeny=any
IPAddressAllow=localhost
CapabilityBoundingSet=
AmbientCapabilities=
[Install]
WantedBy=multi-user.target
'''
    proxy=f'''[Unit]
Description=AI Trust ID isolated HTTPS entry point
After=network-online.target aitrustid-ai-tools.service
Wants=network-online.target
[Service]
{common}User=aitrustid-ai-tools-proxy
WorkingDirectory={base}
ExecStart={base}/caddy run --config {base}/Caddyfile --adapter caddyfile
Environment=XDG_DATA_HOME=/var/lib/aitrustid-ai-tools-proxy
Environment=XDG_CONFIG_HOME=/var/lib/aitrustid-ai-tools-proxy
StateDirectory=aitrustid-ai-tools-proxy
StateDirectoryMode=0700
MemoryMax=192M
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
[Install]
WantedBy=multi-user.target
'''
    return {'aitrustid-ai-tools.service':app,'aitrustid-ai-tools-proxy.service':proxy}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--loopback-port',type=int);a=p.parse_args()
    data={'Caddyfile':caddyfile(a.loopback_port),**units(a.commit)}
    a.output.mkdir(mode=0o700,parents=False,exist_ok=False)
    for name,text in data.items():
        with (a.output/name).open('x') as f:f.write(text)
if __name__=='__main__':main()
