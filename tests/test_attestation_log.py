"""Terminal presentation of a verifier result, including failed evidence."""

import io
import json
import os
import unittest
from unittest.mock import patch

from demo import attestation_log


class Terminal(io.StringIO):
    def isatty(self):
        return True


class AttestationLogTests(unittest.TestCase):
    def test_standard_green_is_visible_on_a_terminal_with_dumb_term(self):
        output = Terminal()
        with (
            patch.object(attestation_log.sys, "stdout", output),
            patch.dict(os.environ, {"TERM": "dumb"}, clear=True),
        ):
            attestation_log.log("  PASSED snp_signature: valid")
        self.assertIn("\033[32mPASSED\033[0m", output.getvalue())
        self.assertIn("snp_signature: valid", output.getvalue())

    def test_explicit_color_overrides_no_color_in_an_interactive_demo(self):
        output = Terminal()
        with (
            patch.object(attestation_log.sys, "stdout", output),
            patch.dict(
                os.environ, {"NO_COLOR": "1", "CONFIDO_COLOR": "always"}, clear=True
            ),
        ):
            attestation_log.log("  PASSED snp_signature: valid")
        self.assertIn("\033[32mPASSED\033[0m", output.getvalue())

    def result(self, *checks, **extra):
        return {
            "evaluated_at": 0,
            "report_sha256": "a" * 64,
            "policy_sha256": "b" * 64,
            "checks": [
                {"stage": s, "status": status, "reason": "test", "detail": detail}
                for s, status, detail in checks
            ],
            **extra,
        }

    def test_every_received_module_is_shown_after_an_early_failure(self):
        report = {
            "evidence": {
                "ima_measurements": [
                    {
                        "name": f"module-{i}.ko",
                        "filedata_alg": "sha256",
                        "filedata_hash": "a" * 64,
                    }
                    for i in range(300)
                ]
            }
        }
        result = self.result(("snp_signature", "failed", "bad signature"))
        lines = []
        attestation_log.describe_verification(
            result, json.dumps(report).encode(), emit=lines.append
        )
        self.assertLess(
            next(i for i, line in enumerate(lines) if "FAILED" in line),
            next(i for i, line in enumerate(lines) if line.startswith("module 000")),
        )
        self.assertEqual(
            sum("Received IMA entries (unverified)" in line for line in lines), 1
        )
        modules = [line for line in lines if line.startswith("module ")]
        self.assertEqual(len(modules), 300)
        self.assertIn("module-299.ko", modules[-1])
        self.assertIn("a" * 64 + "  UNVERIFIED", modules[-1])
        self.assertFalse(any("PASSED" in line for line in modules))

    def test_matching_and_mismatching_modules_show_full_hashes_and_verdicts(self):
        def entry(name, digest):
            return {
                "name": name,
                "PCR": 10,
                "template_hash": "c" * 64,
                "ima_template": "ima-ng",
                "filedata_alg": "sha256",
                "filedata_hash": digest,
                "filename_hint": name,
            }

        trusted = [entry("boot_aggregate", "a" * 64), entry("module.ko", "b" * 64)]
        observed = [trusted[0], entry("module.ko", "d" * 64)]
        result = self.result(
            ("reference", "passed", "pinned"),
            ("ima_reference", "failed", "one changed module"),
        )
        result["checks"][-1]["reason"] = "measurement_mismatch"
        output = Terminal()
        with (
            patch.object(attestation_log.sys, "stdout", output),
            patch.dict(os.environ, {"CONFIDO_COLOR": "always"}, clear=True),
        ):
            attestation_log.describe_verification(
                result,
                {"evidence": {"ima_measurements": observed}},
                json.dumps({"ima_measurements": trusted}).encode(),
            )
        rendered = output.getvalue()
        self.assertIn(
            "\033[32mMATCH\033[0m  \033[38;5;240m000\033[0m  "
            "boot_aggregate  sha256:" + "a" * 64,
            rendered,
        )
        self.assertIn(
            "\033[31mMISMATCH\033[0m  \033[38;5;240m001\033[0m  "
            "module.ko  sha256:" + "d" * 64,
            rendered,
        )
        self.assertFalse(any("…" in row for row in rendered.splitlines() if "sha256:" in row))

    def test_failed_reference_does_not_label_received_modules_as_matching(self):
        result = self.result(("reference", "failed", "wrong digest"))
        lines = []
        attestation_log.describe_verification(
            result,
            {"evidence": {"ima_measurements": [{"name": "module.ko"}]}},
            json.dumps({"ima_measurements": [{"name": "module.ko"}]}),
            emit=lines.append,
        )
        self.assertIn("UNVERIFIED", next(x for x in lines if x.startswith("module ")))
        self.assertFalse(any("MATCH" in x for x in lines))

    def test_module_numbers_share_a_column_for_all_verdicts(self):
        output = Terminal()
        with (
            patch.object(attestation_log.sys, "stdout", output),
            patch.dict(os.environ, {"CONFIDO_COLOR": "never"}, clear=True),
        ):
            for number, verdict in (
                ("015", "MATCH"),
                ("018", "MISMATCH"),
                ("020", "UNVERIFIED"),
            ):
                attestation_log.line(f"module {number} module.ko  sha256:abc  {verdict}")
        rows = output.getvalue().splitlines()
        positions = [
            row.index(number) for row, number in zip(rows, ("015", "018", "020"))
        ]
        self.assertEqual(positions, [17] * 3)
        self.assertLess(rows[1].index("MISMATCH"), rows[0].index("MATCH"))

    def test_reference_label_and_link_are_blue(self):
        output = Terminal()
        with (
            patch.object(attestation_log.sys, "stdout", output),
            patch.dict(os.environ, {"CONFIDO_COLOR": "always"}, clear=True),
        ):
            print(attestation_log.color("Reference: https://example.test", "reference"))
        self.assertIn(
            "\033[34mReference: https://example.test\033[0m", output.getvalue()
        )

    def test_modules_precede_reference_verdict_and_summary_not_duplicated(self):
        report = {
            "evidence": {
                "ima_measurements": [
                    {"name": "boot_aggregate", "filename_hint": "boot_aggregate"},
                    {"name": "test.ko"},
                ]
            }
        }
        result = self.result(
            ("reference", "passed", "pinned"),
            ("ima_reference", "passed", "ordered"),
            ("boot_aggregate", "passed", "boot PCRs"),
            ("pcr10", "passed", "enrolled"),
        )
        lines = []
        attestation_log.describe_verification(result, report, emit=lines.append)
        self.assertIn(
            "2 — 1 boot aggregate, 1 modules",
            next(x for x in lines if x.startswith("IMA entries")),
        )
        index = next(i for i, x in enumerate(lines) if x.startswith("module 001"))
        self.assertIn("IMA reference", lines[index + 1])
        self.assertEqual(sum("PASSED" in x for x in lines), 4)
        self.assertFalse(any(x.startswith("[") for x in lines))
        self.assertIn("01.01.1970 00:00:00 UTC", lines[0])

    def test_partial_ak_artifact_and_legacy_result_are_supported(self):
        result = self.result(
            ("hcl_key", "passed", "bound"),
            ("quote_signature", "failed", "bad signature"),
            verified_artifacts={"vtpm_key_sha256": "c" * 64},
        )
        lines = []
        attestation_log.describe_verification(result, {}, emit=lines.append)
        self.assertTrue(any("AK SHA-256" in x for x in lines))
        self.assertFalse(
            any("certificate DER" in x or "cannot be displayed" in x for x in lines)
        )
        lines.clear()
        attestation_log.describe_verification(
            self.result(("quote", "passed", "legacy")), {}, emit=lines.append
        )
        self.assertTrue(any("Legacy result" in x for x in lines))

    def test_module_names_and_details_cannot_inject_terminal_controls(self):
        output = Terminal()
        with (
            patch.object(attestation_log.sys, "stdout", output),
            patch.dict(os.environ, {"CONFIDO_COLOR": "never"}),
        ):
            attestation_log.line("module 001 evil\x1b[31m\nname")
        self.assertNotIn("\x1b", output.getvalue())
        self.assertIn(r"evil\x1b[31m\x0aname", output.getvalue())


if __name__ == "__main__":
    unittest.main()
