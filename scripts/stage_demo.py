#!/usr/bin/env python3
"""Isolated hardware-backed acceptance run. Never replaces public listeners.
Requires compatible verifier and application transport wheels, a built
collector, Nginx and access to the TPM.
The downstream chat responder is explicitly synthetic: no external inference.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import subprocess
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def wait_port(port, process=None):
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f'Staging process exited {process.returncode}')
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2): return
        except OSError: time.sleep(.1)
    raise RuntimeError(f'Listener {port} did not start')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--confido-root',type=Path,default=ROOT.parent/'confido')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--container',help='Also exercise this frozen client image')
    parser.add_argument('--match-verifier-policy',type=Path,default=ROOT/'profiles/verifier-match.json')
    parser.add_argument('--mismatch-verifier-policy',type=Path,default=ROOT/'profiles/verifier-mismatch.json')
    args=parser.parse_args()
    collector=(args.confido_root.resolve()/'server/target/debug/confido-server')
    verifier_policy_paths={'match':args.match_verifier_policy,'mismatch':args.mismatch_verifier_policy}
    verifier_policy_bytes={name:path.read_bytes() for name,path in verifier_policy_paths.items()}
    verifier_policies={name:json.loads(data) for name,data in verifier_policy_bytes.items()}
    for name,policy in verifier_policies.items():
        if policy.get('schema_version')!=2 or policy.get('profile')!='azure-snp-vtpm-ima/1':
            raise ValueError(f'Invalid {name} verifier policy')
    if verifier_policies['match']['platform']!=verifier_policies['mismatch']['platform']:
        raise ValueError('Stage policies must use the same platform enrollment')
    if verifier_policies['match']['reference']==verifier_policies['mismatch']['reference']:
        raise ValueError('Stage policies must use different references')
    args.out.mkdir(mode=0o700,parents=True,exist_ok=False)
    stage=args.out.resolve()
    for port in [18001,18443,18444,14000]:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0: raise RuntimeError(f'Port {port} already in use')
    policies=stage/'profiles'; policies.mkdir()
    certdir=stage/'certs';certdir.mkdir()
    # Pre-create as the invoking user so sudo preserves readable ownership.
    (stage/'server.pid').touch(mode=0o600)
    captures=[]
    class Responder(BaseHTTPRequestHandler):
        def do_POST(self):
            size=int(self.headers.get('Content-Length','0')); self.rfile.read(size)
            captures.append({'path':self.path,'authorization_present':bool(self.headers.get('Authorization'))})
            body=json.dumps({'id':'synthetic-stage','object':'chat.completion','created':int(time.time()),'model':'llama-default','choices':[{'index':0,'message':{'role':'assistant','content':'Synthetic downstream accepted the admitted request.'},'finish_reason':'stop'}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args): pass
    responder=ThreadingHTTPServer(('127.0.0.1',14000),Responder)
    threading.Thread(target=responder.serve_forever,daemon=True).start()
    processes=[]
    def start(command, log, env=None):
        with (stage/log).open('wb') as out:
            p=subprocess.Popen(command,stdout=out,stderr=subprocess.STDOUT,env=env)
        processes.append(p);return p
    results=[]
    started=datetime.now(timezone.utc).isoformat()
    try:
        server=start(['sudo','-n','sh','-c','umask 077; echo $$ > "$1"; shift; exec "$@"','confido-stage',str(stage/'server.pid'),str(collector),'127.0.0.1:18001',str(certdir),'sha256','--tls-hostname','localhost'],'server.log')
        wait_port(18001,server)
        for name,tls_port in [('match',18443),('mismatch',18444)]:
            policy=json.loads((ROOT/'profiles'/f'{name}.json').read_text());policy['origin']=f'https://localhost:{tls_port}'
            (policies/f'{name}.json').write_text(json.dumps(policy,indent=2))
            (policies/policy['verifier_policy']).write_bytes(verifier_policy_bytes[name])
        nginx='''worker_processes 1;
pid PATH/nginx.pid;
error_log PATH/nginx-error.log;
events {worker_connections 64;}
http {
  map $http_authorization $has_auth {default 1; "" 0;}
  log_format stage '$server_port $request_method $uri $status auth=$has_auth';
  access_log PATH/nginx-access.log stage;
'''.replace('PATH',str(stage))
        for tls_port in (18443,18444):
            nginx+=f'''server {{
 listen 127.0.0.1:{tls_port} ssl;
 server_name localhost;
 ssl_certificate {certdir}/certificate.pem;
 ssl_certificate_key {certdir}/private_key.pem;
 ssl_protocols TLSv1.2 TLSv1.3;
 location = /tee-report {{client_max_body_size 1k;proxy_read_timeout 25s;proxy_pass http://127.0.0.1:18001/tee-report;}}
 location = /aTLS {{return 404;}}
 location /v1/ {{proxy_pass http://127.0.0.1:14000;}}
}}
'''
        nginx+='}\n';(stage/'nginx.conf').write_text(nginx)
        proxy=start(['sudo','-n','nginx','-c',str(stage/'nginx.conf'),'-p',str(stage),'-g','daemon off;'],'nginx-stdout.log')
        wait_port(18443,proxy);wait_port(18444,proxy)
        os.environ['CONFIDO_POLICY_DIR']=str(policies);os.environ['CONFIDO_RUN_DIR']=str(stage/'runs')
        # Sentinel credentials only, never production credentials/provider keys.
        os.environ['CONFIDO_USERNAME']='stage-only';os.environ['CONFIDO_PASSWORD']='stage-only-sentinel'
        sys.path.insert(0,str(ROOT))
        spec=importlib.util.spec_from_file_location('chat_demo',ROOT/'confai-promter.py')
        demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
        from demo import collection, admission
        def connect(policy, path):
            run=collection.collect_and_verify(policy)
            result, archive=run.result, run.archive
            assert result["status"] == "verified", "Transport case must start with verified evidence"
            admission.save_private(path,archive)
            session=admission.authenticate(policy,result,run=run)
            run.consume(policy,result)
            return session
        for name,expected in [('match',True),('mismatch',False)]:
            before=len(captures)
            with patch('builtins.input',return_value=''):
                client=demo.setup_client(name)
            assert (client is not None)==expected,(name,'unexpected admission')
            assert len(captures)==before,'Application request was sent during appraisal'
            if client:
                reply=client.chat.completions.create(model='llama-default',messages=[{'role':'user','content':'Synthetic admission test.'}])
                assert reply.choices[0].message.content.startswith('Synthetic')
                client.close()
            observed=len(captures)-before
            assert observed==int(expected)
            results.append({'id':f'installed_wheel_{name}','expected_admitted':expected,'observed_admitted':client is not None,'application_requests':observed})
        # A shared certificate cannot transfer admission to another origin.
        policy=collection.load_policy(policies/'match.json')
        admitted=connect(policy,stage/'scope-test.json')
        before=len(captures)
        for origin in ['https://localhost:18444','http://localhost:18443','https://127.0.0.1:18443']:
            try: admitted.request('POST',origin+'/v1/chat/completions',[('authorization','stage-only-sentinel')],b'{}')
            except RuntimeError as e: assert 'outside' in str(e)
            else: raise AssertionError('Cross-origin request accepted')
        assert len(captures)==before
        results.append({'id':'origin_scope_shared_certificate','rejected_targets':3,'application_requests':0})
        # Fresh real evidence is insufficient when the TLS name is wrong.
        bad=dict(policy,origin='https://127.0.0.1:18443')
        try: connect(bad,stage/'wrong-host.json')
        except (RuntimeError,ValueError): pass
        else: raise AssertionError('Wrong TLS hostname admitted')
        r={'reason':'https_authentication_failed'}
        results.append({'id':'wrong_tls_hostname','observed':r['reason'],'application_requests':0})
        if args.container:
            # The container uses the same isolated public contract and new wheel.
            before=len(captures)
            for name,expected in [('match',True),('mismatch',False)]:
                command=['sudo','-n','docker','run','--rm','--network','host','--user',f'{os.getuid()}:{os.getgid()}',
                         '-e','CONFIDO_POLICY_DIR=/stage/profiles','-e','CONFIDO_RUN_DIR=/stage/container-runs','-e','CONFIDO_USERNAME=stage-only','-e','CONFIDO_PASSWORD=stage-only-sentinel',
                         '-v',f'{stage}:/stage',args.container,'python3','scripts/container_acceptance.py',name,str(expected).lower()]
                subprocess.run(command,check=True)
            assert len(captures)-before==1
            results.append({'id':'container_pair','match_requests':1,'mismatch_requests':0,'image':args.container})
        access=(stage/'nginx-access.log').read_text().splitlines()
        assert not any('auth=1' in line and '/tee-report ' in line for line in access)
        results.append({'id':'no_credentials_during_appraisal','report_requests':sum('/tee-report ' in l for l in access),'credential_bearing_report_requests':0})
        report={'started_at':started,'ended_at':datetime.now(timezone.utc).isoformat(),'tests':results,'downstream':'synthetic OpenAI-compatible responder; no inference evaluated','hardware':'live VM TPM collector and AMD-endorsed SNP evidence','requests':captures}
        (stage/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        if (stage/'nginx.pid').exists():
            subprocess.run(['sudo','-n','nginx','-s','quit','-c',str(stage/'nginx.conf'),'-p',str(stage)],check=False)
        responder.shutdown()
        responder.server_close()
        # sudo may use a monitor/PTY. Signal the recorded workload PID, not
        # merely the sudo wrapper; verify its identity before any signal.
        if (stage/'server.pid').exists():
            pid=int((stage/'server.pid').read_text())
            def own_collector():
                try: argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                except FileNotFoundError:return False
                return argv[0]==str(collector).encode() and str(certdir).encode() in argv
            if own_collector():
                subprocess.run(['sudo','-n','kill','-TERM',str(pid)],check=False)
                for _ in range(30):
                    if not own_collector():break
                    time.sleep(.1)
                if own_collector():subprocess.run(['sudo','-n','kill','-KILL',str(pid)],check=True)

        for process in reversed(processes):
            if process.poll() is None:
                subprocess.run(['sudo','-n','kill','-TERM',str(process.pid)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: subprocess.run(['sudo','-n','kill','-KILL',str(process.pid)],check=False)
        # Check that no isolated listener survives cleanup.
        for port in [18001,18443,18444,14000]:
            for _ in range(20):
                with socket.socket() as sock:
                    if sock.connect_ex(('127.0.0.1',port))!=0:break
                time.sleep(.1)
            else: raise RuntimeError(f'Staging listener {port} survived cleanup')
        subprocess.run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(stage)],check=True)
        for file in stage.rglob('*'):
            if file.is_file():file.chmod(0o600)


if __name__=='__main__':
    main()
