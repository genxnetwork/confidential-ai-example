"""Pin a signed registry reference into a local Confido v2 verifier policy.

The issuer policy is a local verifier-owner input. Registry contents are data,
never executable configuration or an authority list.
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SAFE = re.compile(r"[A-Za-z0-9_.-]+\Z")
MAX_FILE = 4 * 1024 * 1024
PREDICATE_TYPE = "https://teraveri.org/attestations/reference-manifest-publisher/v1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(data):
    return json.loads(data, object_pairs_hook=no_duplicate_keys)


def safe_path(value):
    return (
        isinstance(value, str)
        and bool(value)
        and all(
            part not in (".", "..") and SAFE.fullmatch(part)
            for part in value.split("/")
        )
    )


def repository_name(value):
    return (
        isinstance(value, str)
        and len(value.split("/")) == 2
        and all(
            SAFE.fullmatch(part) and part not in (".", "..")
            for part in value.split("/")
        )
    )


def fetch(registry, commit, path):
    if (
        not repository_name(registry)
        or not HEX40.fullmatch(commit)
        or not safe_path(path)
    ):
        raise ValueError("invalid immutable registry locator")
    url = f"https://api.github.com/repos/{registry}/contents/{path}?ref={commit}"
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "User-Agent": "confido-enrollment/0.2.0",
    }
    if token := os.environ.get("CONFIDO_TRS_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=20
    ) as response:
        data = response.read(MAX_FILE + 1)
    if not data or len(data) > MAX_FILE:
        raise ValueError(f"registry object size invalid: {path}")
    return data


def read_local(registry_dir, path):
    if not safe_path(path):
        raise ValueError("unsafe registry path")
    base = registry_dir.resolve(strict=True)
    file = (base / path).resolve(strict=True)
    if not file.is_relative_to(base) or not file.is_file():
        raise ValueError("registry object escapes checkout")
    data = file.read_bytes()
    if not data or len(data) > MAX_FILE:
        raise ValueError("registry object size invalid")
    return data


def validate_manifest(manifest_bytes, reference_bytes, entry):
    m = parse_json(manifest_bytes)
    if set(m) != {
        "schema_version",
        "id",
        "profile",
        "environment",
        "reference",
        "provenance",
        "coverage",
    }:
        raise ValueError("invalid manifest shape")
    if m["schema_version"] != 1 or m["profile"] != "azure-snp-vtpm-ima/1":
        raise ValueError("unsupported reference manifest")
    if not safe_path(entry) or m["id"] != entry.split("/")[-1]:
        raise ValueError("manifest identity mismatch")
    ref = m["reference"]
    expected_path = f"{entry}/reference.json"
    if set(ref) != {"path", "sha256", "ima_entries"} or ref["path"] != expected_path:
        raise ValueError("manifest reference path mismatch")
    if not isinstance(ref["sha256"], str) or not HEX64.fullmatch(ref["sha256"]):
        raise ValueError("invalid reference digest")
    if hashlib.sha256(reference_bytes).hexdigest() != ref["sha256"]:
        raise ValueError("reference digest mismatch")
    trs = parse_json(reference_bytes)
    if not isinstance(trs.get("ima_measurements"), list) or not trs["ima_measurements"]:
        raise ValueError("invalid IMA reference")
    if (
        type(ref["ima_entries"]) is not int
        or len(trs["ima_measurements"]) != ref["ima_entries"]
    ):
        raise ValueError("IMA count mismatch")
    if not isinstance(trs.get("pcr10_sha256"), str) or not HEX64.fullmatch(
        trs["pcr10_sha256"]
    ):
        raise ValueError("invalid PCR 10 reference")
    if m["coverage"] != ["boot_aggregate", "kernel_modules"]:
        raise ValueError("unsupported reference coverage")
    if m["provenance"]["review_status"] not in (
        "stage-candidate",
        "stage-approved",
        "approved",
    ):
        raise ValueError("unknown review status")
    if m["environment"]["tee"] != "AMD SEV-SNP" or m["environment"]["product"] not in (
        "Milan",
        "Genoa",
    ):
        raise ValueError("unsupported platform")
    return m


def verify_bundle(manifest_bytes, bundle_bytes, issuer, registry, manifest_path, gh):
    if (
        issuer["predicate_type"] != PREDICATE_TYPE
        or issuer["claim"] != "published-reference-manifest"
    ):
        raise ValueError("unsupported issuer claim")
    if not repository_name(issuer["repository"]):
        raise ValueError("invalid issuer repository")
    expected_workflow = f"{issuer['repository']}/.github/workflows/endorse-manifest.yml"
    if issuer["workflow"] != expected_workflow or issuer["source_ref"] not in (
        "refs/heads/main",
        "refs/heads/master",
    ):
        raise ValueError("invalid issuer workflow identity")
    with tempfile.TemporaryDirectory() as temp:
        manifest_file = Path(temp) / "manifest.json"
        bundle_file = Path(temp) / "bundle.json"
        manifest_file.write_bytes(manifest_bytes)
        bundle_file.write_bytes(bundle_bytes)
        command = [
            gh,
            "attestation",
            "verify",
            str(manifest_file),
            "--bundle",
            str(bundle_file),
            "--repo",
            issuer["repository"],
            "--signer-workflow",
            issuer["workflow"],
            "--source-ref",
            issuer["source_ref"],
            "--predicate-type",
            issuer["predicate_type"],
            "--deny-self-hosted-runners",
            "--format",
            "json",
        ]
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=60
        )
    records = json.loads(result.stdout)
    if not isinstance(records, list):
        raise TypeError("unexpected attestation verification output")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    name = f"{registry}/{manifest_path}"
    for record in records:
        statement = record.get("verificationResult", {}).get("statement", {})
        subjects = statement.get("subject", [])
        predicate = statement.get("predicate", {})
        if subjects == [{"name": name, "digest": {"sha256": digest}}] and predicate == {
            "schema_version": 1,
            "claim": "published-reference-manifest",
            "publisher": issuer["name"],
            "registry_repository": registry,
            "manifest_path": manifest_path,
            "manifest_sha256": digest,
        }:
            return digest
    raise ValueError("signed subject or publisher claim mismatch")


def verify_manual_bundle(manifest_bytes, bundle_bytes, issuer, registry, manifest_path):
    """Verify the explicitly pinned, one-use GENXT stage key and exact claim."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if (
        issuer.get("method") != "ed25519-stage"
        or issuer.get("predicate_type") != PREDICATE_TYPE
    ):
        raise ValueError("unsupported manual issuer")
    if (
        issuer.get("claim") != "published-reference-manifest"
        or issuer.get("publisher") != "GENXT"
    ):
        raise ValueError("unsupported manual issuer claim")
    if not repository_name(issuer.get("repository")):
        raise ValueError("invalid manual issuer repository")
    try:
        public_key = base64.b64decode(issuer["public_key"], validate=True)
    except (KeyError, ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("invalid pinned public key") from exc
    if len(public_key) != 32 or hashlib.sha256(public_key).hexdigest() != issuer.get(
        "public_key_sha256"
    ):
        raise ValueError("pinned public key digest mismatch")
    bundle = parse_json(bundle_bytes)
    if not isinstance(bundle, dict) or set(bundle) != {
        "schema_version",
        "algorithm",
        "key_id",
        "statement",
        "signature",
    }:
        raise ValueError("invalid manual endorsement bundle")
    if (
        type(bundle["schema_version"]) is not int
        or bundle["schema_version"] != 1
        or bundle["algorithm"] != "Ed25519"
    ):
        raise ValueError("unsupported manual endorsement format")
    if bundle["key_id"] != issuer["public_key_sha256"]:
        raise ValueError("manual endorsement key mismatch")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    if (
        issuer.get("manifest_path") != manifest_path
        or issuer.get("manifest_sha256") != digest
    ):
        raise ValueError("manual issuer is not pinned to this manifest")
    expected_statement = {
        "_type": STATEMENT_TYPE,
        "subject": [
            {"name": f"{registry}/{manifest_path}", "digest": {"sha256": digest}}
        ],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "schema_version": 1,
            "claim": "published-reference-manifest",
            "publisher": "GENXT",
            "registry_repository": registry,
            "manifest_path": manifest_path,
            "manifest_sha256": digest,
        },
    }
    if bundle["statement"] != expected_statement:
        raise ValueError("manual signed subject or publisher claim mismatch")
    try:
        signature = base64.b64decode(bundle["signature"], validate=True)
        if len(signature) != 64:
            raise ValueError("invalid manual signature length")
        message = json.dumps(
            bundle["statement"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    except (InvalidSignature, ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("manual endorsement signature invalid") from exc
    return digest


def enroll(
    registry, commit, entry, issuer_policy, platform, reader, gh, issuer_name="GENXT"
):
    if (
        not repository_name(registry)
        or not isinstance(commit, str)
        or not HEX40.fullmatch(commit)
    ):
        raise ValueError("invalid registry commit")
    if not safe_path(entry) or not entry.startswith("entries/"):
        raise ValueError("invalid entry path")
    if (
        not isinstance(issuer_name, str)
        or not SAFE.fullmatch(issuer_name)
        or issuer_name in (".", "..")
    ):
        raise ValueError("invalid issuer name")
    if (
        set(issuer_policy) != {"schema_version", "registry_repository", "issuers"}
        or issuer_policy["schema_version"] != 1
        or issuer_policy["registry_repository"] != registry
    ):
        raise ValueError("local issuer policy does not authorize registry")
    matches = [i for i in issuer_policy["issuers"] if i["name"] == issuer_name]
    if len(matches) != 1:
        raise ValueError("issuer is not uniquely authorized")
    issuer = matches[0]
    manifest_path = f"{entry}/manifest.json"
    reference_path = f"{entry}/reference.json"
    method = issuer.get("method", "github-actions")
    if method not in ("github-actions", "ed25519-stage"):
        raise ValueError("unsupported issuer method")
    bundle_ext = "ed25519.json" if method == "ed25519-stage" else "sigstore.json"
    bundle_path = f"{entry}/endorsements/{issuer_name.lower()}.{bundle_ext}"
    manifest_bytes = reader(manifest_path)
    reference_bytes = reader(reference_path)
    bundle_bytes = reader(bundle_path)
    m = validate_manifest(manifest_bytes, reference_bytes, entry)
    if (
        m["profile"] not in issuer["profiles"]
        or m["provenance"]["review_status"] not in issuer["review_statuses"]
    ):
        raise ValueError("issuer is not authorized for this reference scope")
    if m["environment"]["product"] != platform["product"]:
        raise ValueError("platform product and manifest differ")
    if method == "ed25519-stage":
        verify_manual_bundle(
            manifest_bytes, bundle_bytes, issuer, registry, manifest_path
        )
    else:
        verify_bundle(manifest_bytes, bundle_bytes, issuer, registry, manifest_path, gh)
    if set(platform) != {"product", "ark_sha256", "minimum_tcb", "launch_measurement"}:
        raise ValueError("invalid local platform policy")
    if not HEX64.fullmatch(platform["ark_sha256"]) or not re.fullmatch(
        r"[0-9a-f]{96}", platform["launch_measurement"]
    ):
        raise ValueError("invalid platform enrollment")
    if len(platform["minimum_tcb"]) != 4 or not all(
        type(x) is int and 0 <= x <= 255 for x in platform["minimum_tcb"]
    ):
        raise ValueError("invalid minimum TCB")
    return {
        "schema_version": 2,
        "profile": m["profile"],
        "platform": platform,
        "reference": {
            "repository": registry,
            "commit": commit,
            "path": reference_path,
            "sha256": m["reference"]["sha256"],
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", default="teraveri/reference-value-registry")
    p.add_argument(
        "--commit",
        required=True,
        help="Full registry commit with the manifest and publisher bundle",
    )
    p.add_argument("--entry", required=True, help="entries/<profile>/<environment>")
    p.add_argument(
        "--registry-dir",
        type=Path,
        help="Read objects from this trusted local checkout instead of GitHub",
    )
    p.add_argument(
        "--issuer-policy",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "profiles/reference-issuers-stage.json",
    )
    p.add_argument(
        "--platform",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "profiles/platform-genoa-stage.json",
    )
    p.add_argument("--gh", default=shutil.which("gh") or "gh")
    p.add_argument("--issuer", default="GENXT", help="Locally trusted publisher name")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    issuer_policy = parse_json(args.issuer_policy.read_bytes())
    platform = parse_json(args.platform.read_bytes())
    if args.registry_dir:
        checkout = args.registry_dir.resolve(strict=True)
        head = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(checkout), "status", "--porcelain=v1"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if head != args.commit or dirty:
            raise ValueError(
                "local registry checkout must be clean at the selected commit"
            )
        reader = lambda path: read_local(args.registry_dir, path)
    else:
        reader = lambda path: fetch(args.registry, args.commit, path)
    policy = enroll(
        args.registry,
        args.commit,
        args.entry,
        issuer_policy,
        platform,
        reader,
        args.gh,
        args.issuer,
    )
    output = json.dumps(policy, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)
    print(
        f"enrolled {policy['reference']['repository']}@{policy['reference']['commit']} {policy['reference']['path']}"
    )


if __name__ == "__main__":
    main()
