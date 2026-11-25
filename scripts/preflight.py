"""Check the installed client and, optionally, its external attestation endpoint."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    from demo.runtime import ensure_runtime

    runtime = ensure_runtime()
    print(
        "PASS: installed Confido client pipeline "
        + str(runtime["pipeline_revision"])
    )
    if args.online:
        if not args.policy:
            parser.error("--online requires --policy")
        import confido_client
        from demo import admission, policy as app_policy

        policy = app_policy.load_policy(args.policy)
        attempt = confido_client.appraise(
            policy["origin"],
            policy["verifier_bytes"],
            policy.get("allow_untrusted_bootstrap", False),
        )
        result = attempt.result
        admission.authenticate(policy, result, attempt=attempt)
        print("Evidence status:", result["status"])
        print("PASS: compatible report and intended HTTPS peer")
    print("Client check complete; no inference request sent.")


if __name__ == "__main__":
    main()
