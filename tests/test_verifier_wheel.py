"""Reject an unexpected distribution before installing a downloaded verifier wheel."""

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "build_wheels", Path(__file__).resolve().parents[1] / "scripts/build_wheels.py"
)
build_wheels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_wheels)


class VerifierWheelTests(unittest.TestCase):
    def test_distribution_and_version_must_match_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / "verifier.whl"
            for name, version, valid in (
                ("confido-verifier", "0.2.0", True),
                ("other-verifier", "0.2.0", False),
                ("confido-verifier", "0.3.0", False),
            ):
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr(
                        "confido_verifier-0.2.0.dist-info/METADATA",
                        f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n",
                    )
                if valid:
                    build_wheels.check_verifier_wheel(wheel, "0.2.0")
                else:
                    with self.assertRaises(ValueError):
                        build_wheels.check_verifier_wheel(wheel, "0.2.0")
