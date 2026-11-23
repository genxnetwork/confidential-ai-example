import base64
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import enroll_reference as er

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "entries/azure-snp-vtpm-ima-1/azure-genoa-ubuntu2204-kernel-1071-stage"
COMMIT = "a" * 40


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.issuer_policy = json.loads(
            (ROOT / "profiles/reference-issuers-stage.json").read_text()
        )
        self.platform = json.loads(
            (ROOT / "profiles/platform-genoa-stage.json").read_text()
        )
        self.manifest_path = f"{ENTRY}/manifest.json"
        self.reference = json.dumps(
            {"ima_measurements": [{"PCR": 10}], "pcr10_sha256": "0" * 64}
        ).encode()
        self.manifest = json.dumps(
            {
                "schema_version": 1,
                "id": "azure-genoa-ubuntu2204-kernel-1071-stage",
                "profile": "azure-snp-vtpm-ima/1",
                "environment": {"tee": "AMD SEV-SNP", "product": "Genoa"},
                "reference": {
                    "path": f"{ENTRY}/reference.json",
                    "sha256": hashlib.sha256(self.reference).hexdigest(),
                    "ima_entries": 1,
                },
                "provenance": {"review_status": "stage-candidate"},
                "coverage": ["boot_aggregate", "kernel_modules"],
            }
        ).encode()
        self.bundle = b"bundle-test-placeholder"
        self.objects = {
            self.manifest_path: self.manifest,
            f"{ENTRY}/reference.json": self.reference,
            f"{ENTRY}/endorsements/genxt.sigstore.json": self.bundle,
        }

    def reader(self, path):
        return self.objects[path]

    def verification(self, predicate=None):
        digest = hashlib.sha256(self.manifest).hexdigest()
        expected = {
            "schema_version": 1,
            "claim": "published-reference-manifest",
            "publisher": "GENXT",
            "registry_repository": "teraveri/reference-value-registry",
            "manifest_path": self.manifest_path,
            "manifest_sha256": digest,
        }
        record = [
            {
                "verificationResult": {
                    "statement": {
                        "subject": [
                            {
                                "name": f"teraveri/reference-value-registry/{self.manifest_path}",
                                "digest": {"sha256": digest},
                            }
                        ],
                        "predicate": predicate or expected,
                    }
                }
            }
        ]
        return SimpleNamespace(stdout=json.dumps(record))

    def manual_bundle(self):
        policy = copy.deepcopy(self.issuer_policy)
        issuer = next(i for i in policy["issuers"] if i["name"] == "GENXT-manual")
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        key_id = hashlib.sha256(public).hexdigest()
        issuer["public_key"] = base64.b64encode(public).decode()
        issuer["public_key_sha256"] = key_id
        digest = hashlib.sha256(self.manifest).hexdigest()
        issuer["manifest_path"] = self.manifest_path
        issuer["manifest_sha256"] = digest
        statement = {
            "_type": er.STATEMENT_TYPE,
            "subject": [
                {
                    "name": f"teraveri/reference-value-registry/{self.manifest_path}",
                    "digest": {"sha256": digest},
                }
            ],
            "predicateType": er.PREDICATE_TYPE,
            "predicate": {
                "schema_version": 1,
                "claim": "published-reference-manifest",
                "publisher": "GENXT",
                "registry_repository": "teraveri/reference-value-registry",
                "manifest_path": self.manifest_path,
                "manifest_sha256": digest,
            },
        }
        message = json.dumps(
            statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        bundle = {
            "schema_version": 1,
            "algorithm": "Ed25519",
            "key_id": key_id,
            "statement": statement,
            "signature": base64.b64encode(key.sign(message)).decode(),
        }
        path = f"{ENTRY}/endorsements/genxt-manual.ed25519.json"
        self.objects[path] = json.dumps(bundle).encode()
        return policy, bundle, path

    @patch("enroll_reference.subprocess.run")
    def test_enrolls_only_verified_publisher_statement(self, run):
        run.return_value = self.verification()
        policy = er.enroll(
            "teraveri/reference-value-registry",
            COMMIT,
            ENTRY,
            self.issuer_policy,
            self.platform,
            self.reader,
            "gh",
        )
        self.assertEqual(
            policy["reference"]["sha256"], hashlib.sha256(self.reference).hexdigest()
        )
        command = run.call_args.args[0]
        self.assertIn("--signer-workflow", command)
        self.assertIn("--source-ref", command)
        self.assertIn("--predicate-type", command)
        self.assertTrue(run.call_args.kwargs["check"])

    @patch("enroll_reference.subprocess.run")
    def test_rejects_signed_wrong_claim(self, run):
        run.return_value = self.verification({"claim": "unrelated"})
        with self.assertRaisesRegex(
            ValueError, "signed subject or publisher claim mismatch"
        ):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                self.issuer_policy,
                self.platform,
                self.reader,
                "gh",
            )

    @patch("enroll_reference.subprocess.run")
    def test_rejects_reference_change_before_signature_check(self, run):
        self.objects[f"{ENTRY}/reference.json"] += b" "
        with self.assertRaisesRegex(ValueError, "reference digest mismatch"):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                self.issuer_policy,
                self.platform,
                self.reader,
                "gh",
            )
        run.assert_not_called()

    @patch("enroll_reference.subprocess.run")
    def test_rejects_unapproved_publisher(self, run):
        with self.assertRaisesRegex(ValueError, "issuer is not uniquely authorized"):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                self.issuer_policy,
                self.platform,
                self.reader,
                "gh",
                "other",
            )
        run.assert_not_called()

    @patch("enroll_reference.subprocess.run")
    def test_rejects_unsafe_publisher_name(self, run):
        with self.assertRaisesRegex(ValueError, "invalid issuer name"):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                self.issuer_policy,
                self.platform,
                self.reader,
                "gh",
                "../other",
            )
        run.assert_not_called()

    def test_stage_negative_uses_same_genoa_platform_and_alternate_reference(self):
        negative = json.loads(
            (ROOT / "profiles/verifier-genoa-stage-mismatch.json").read_text()
        )
        self.assertEqual(negative["platform"], self.platform)
        self.assertNotEqual(
            negative["reference"]["sha256"], hashlib.sha256(self.reference).hexdigest()
        )

    def test_manual_stage_key_verifies_exact_manifest(self):
        policy, _, _ = self.manual_bundle()
        enrolled = er.enroll(
            "teraveri/reference-value-registry",
            COMMIT,
            ENTRY,
            policy,
            self.platform,
            self.reader,
            "unused",
            "GENXT-manual",
        )
        self.assertEqual(
            enrolled["reference"]["sha256"], hashlib.sha256(self.reference).hexdigest()
        )

    def test_manual_stage_key_rejects_modified_claim(self):
        policy, bundle, path = self.manual_bundle()
        bundle["statement"]["predicate"]["publisher"] = "other"
        self.objects[path] = json.dumps(bundle).encode()
        with self.assertRaisesRegex(
            ValueError, "manual signed subject or publisher claim mismatch"
        ):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                policy,
                self.platform,
                self.reader,
                "unused",
                "GENXT-manual",
            )

    def test_manual_stage_key_rejects_modified_signature(self):
        policy, bundle, path = self.manual_bundle()
        bundle["signature"] = base64.b64encode(b"0" * 64).decode()
        self.objects[path] = json.dumps(bundle).encode()
        with self.assertRaisesRegex(ValueError, "manual endorsement signature invalid"):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                policy,
                self.platform,
                self.reader,
                "unused",
                "GENXT-manual",
            )

    def test_manual_stage_key_rejects_unpinned_manifest(self):
        policy, _, _ = self.manual_bundle()
        issuer = next(i for i in policy["issuers"] if i["name"] == "GENXT-manual")
        issuer["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            ValueError, "manual issuer is not pinned to this manifest"
        ):
            er.enroll(
                "teraveri/reference-value-registry",
                COMMIT,
                ENTRY,
                policy,
                self.platform,
                self.reader,
                "unused",
                "GENXT-manual",
            )


if __name__ == "__main__":
    unittest.main()
