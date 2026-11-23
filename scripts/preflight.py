#!/usr/bin/env python3
"""Read-only deployment preflight; never sends credentials or inference requests."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--confido-root", type=Path, default=ROOT.parent / "confido")
    parser.add_argument("--flint", type=Path, help="Optionally compare a deployment Nginx configuration")
    args = parser.parse_args()
    from demo.runtime import ensure_runtime
    runtime = ensure_runtime(args.confido_root / "lib")
    print("PASS: installed verifier and transport pipeline " + str(runtime["pipeline_revision"]))
    canonical = (ROOT / "deploy/genxt-demo/nginx.conf").read_bytes()
    if canonical.count(b"location = /tee-report") != 2:
        raise SystemExit("FAIL: demo routing must expose only the direct attestation endpoint")
    if args.flint and (args.flint / "nginx/flint.conf").read_bytes() != canonical:
        raise SystemExit("FAIL: deployment Nginx routing differs from the application template")
    print("PASS: direct attestation routing; sha256=" + hashlib.sha256(canonical).hexdigest())
    if not (ROOT / "deploy/genxt-demo/systemd-confido.service").is_file():
        raise SystemExit("FAIL: demo collector unit missing")
    print("PASS: demo collector unit available")
    if args.online:
        if not args.policy:
            parser.error("--online requires --policy")
        from demo import collection, admission
        policy = collection.load_policy(args.policy)
        run = collection.collect_and_verify(policy)
        result = run.result
        session = admission.authenticate(policy, result, run=run)
        run.consume(policy, result)
        print(json.dumps(result, indent=2))
        for path, expected in [("/aTLS", 404)]:
            status, _, _ = session.request("GET", policy["origin"] + path, [], b"")
            if status != expected:
                raise SystemExit(f"FAIL: retired route {path}: HTTP {status}")
        print("PASS: compatible report, intended HTTPS peer and retired /aTLS route")
    print("Preflight complete; no application credential or inference request sent.")


if __name__ == "__main__":
    main()
