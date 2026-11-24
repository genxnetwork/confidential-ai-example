"""Check the installed client and, optionally, its external attestation endpoint."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--confido-root", type=Path, default=ROOT / ".artifacts/confido-src")
    args = parser.parse_args()
    from demo.runtime import ensure_runtime

    runtime = ensure_runtime(args.confido_root / "lib")
    print(
        "PASS: installed verifier and transport pipeline "
        + str(runtime["pipeline_revision"])
    )
    if args.online:
        if not args.policy:
            parser.error("--online requires --policy")
        from demo import admission, collection

        policy = collection.load_policy(args.policy)
        run = collection.collect_and_verify(policy)
        result = run.result
        admission.authenticate(policy, result, run=run)
        run.consume(policy, result)
        print(json.dumps(result, indent=2))
        print("PASS: compatible report and intended HTTPS peer")
    print("Client check complete; no inference request sent.")


if __name__ == "__main__":
    main()
