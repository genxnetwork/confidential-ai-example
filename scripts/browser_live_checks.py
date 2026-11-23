#!/usr/bin/env python3
"""Opt-in public demo collection with packaged Chromium WASM.
The test copy pregrants exactly the manifest's four optional hosts on installation;
production retains optional permissions. No credentials or chat requests are sent.
"""
import json
import argparse
from pathlib import Path
import shutil
import tempfile
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--extension-dir',type=Path,default=ROOT.parent/'confido/extension/dist/chromium')
args=p.parse_args()
with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
    root=Path(tmp);ext=root/'extension';shutil.copytree(args.extension_dir,ext)
    manifest=json.loads((ext/'manifest.json').read_text())
    manifest['host_permissions']=manifest['optional_host_permissions']
    (ext/'manifest.json').write_text(json.dumps(manifest))
    ctx=p.chromium.launch_persistent_context(root/'profile',channel='chromium',headless=True,args=[f'--disable-extensions-except={ext}',f'--load-extension={ext}'])
    worker=ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event('serviceworker')
    page=ctx.new_page();page.goto('chrome-extension://'+worker.url.split('/')[2]+'/index.html')
    for name,status in [('match','verified'),('mismatch','policy_mismatch')]:
        page.locator('#policy').set_input_files(ROOT/f'profiles/verifier-{name}.json')
        page.locator('#origin').select_option('https://'+name+'.demo.genxt.network')
        page.locator('#live').click()
        try:expect(page.locator('#save')).to_be_enabled(timeout=150000)
        except Exception:raise RuntimeError(name+': '+page.locator('#status').inner_text()) from None
        result=json.loads(page.locator('#result').inner_text())
        assert result['status']==status,(name,result['reason'])
        assert result['scope']=='evidence_only' and 'application_admitted' not in result
        print('Chromium live '+name+': '+status+'; local WASM, ordinary browser TLS')
    ctx.close()
