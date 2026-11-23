#!/usr/bin/env python3
"""Validate observed ServiceInfo against frozen GA4GH v1 plus the TEE extension."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import urllib.request
import yaml
from jsonschema import Draft4Validator, FormatChecker, RefResolver

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('metadata',help='JSON file or explicit http(s) URL')
    p.add_argument('--confido-root',type=Path,default=ROOT.parent/'confido')
    p.add_argument('--sidecar',type=Path,default=ROOT.parent/'ga4gh_service_info_sidecar_gsoc_2026')
    args=p.parse_args()
    provenance=json.loads((args.confido_root/'schemas/provenance.json').read_text())
    raw=(args.confido_root/'schemas/ga4gh-service-info-v1.0.0.yaml').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==provenance['sha256'],'Frozen GA4GH schema digest mismatch'
    ga4gh=yaml.safe_load(raw)
    extension=yaml.safe_load((args.sidecar/'docs/tee-report-extension.yaml').read_text())
    resolver=RefResolver.from_schema(extension,store={provenance['source']:ga4gh})
    data=json.load(urllib.request.urlopen(args.metadata,timeout=5)) if args.metadata.startswith(('http://','https://')) else json.loads(Path(args.metadata).read_text())
    validator=Draft4Validator(extension['components']['schemas']['ServiceWithTEEReport'],resolver=resolver,format_checker=FormatChecker())
    validator.validate(data)
    for mutate in [lambda d:d.pop('id'),lambda d:d['teeReport'].pop('profile'),lambda d:d['teeReport'].__setitem__('wireVersion',2),lambda d:d['teeReport']['sessionBinding'].__setitem__('supported',True)]:
        altered=copy.deepcopy(data);mutate(altered)
        assert not validator.is_valid(altered),'Invalid metadata escaped contract validation'
    print('PASS: GA4GH v1.0.0 + Confido advertisement; four invalid mutations rejected')


if __name__=='__main__':main()
