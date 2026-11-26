"""Reject a wheel that does not match the application's Confido client pin."""

import tempfile
import unittest
import zipfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch


from scripts import install_client_wheel as build


class ClientWheelTests(unittest.TestCase):
    def test_installation_record_is_published_only_after_pip_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "confido-client-wheel.json").write_text(json.dumps({
                "distribution": "confido-client", "version": "0.2.0",
            }))
            wheel = root / "candidate.whl"
            with zipfile.ZipFile(wheel, "w"):
                pass
            record = root / "installed.json"
            record.write_text("previous record")
            with (
                patch.object(build, "ROOT", root),
                patch.object(build, "INSTALL_RECORD", record),
                patch.object(build, "inspect_wheel"),
                patch.object(build, "probe", return_value={"build_info": {"client": "test-build"}}),
                patch.object(build.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "pip")) as pip,
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    build.install(wheel)
                self.assertEqual(record.read_text(), "previous record")
                pip.side_effect = None
                build.install(wheel)
            saved = json.loads(record.read_text())
            self.assertEqual(saved["wheel"], "candidate.whl")
            self.assertEqual(len(saved["wheel_sha256"]), 64)
            self.assertFalse((root / "build").exists())

    def test_distribution_version_and_native_module_are_checked(self):
        pin = {"distribution": "confido-client", "version": "0.2.0"}
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / "candidate.whl"
            for name, version, binary, accepted in (
                ("confido-client", "0.2.0", True, True),
                ("other-client", "0.2.0", True, False),
                ("confido-client", "", True, False),
                ("confido-client", "0.2.0", False, False),
            ):
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr(
                        "confido_client-0.2.0.dist-info/METADATA",
                        f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n",
                    )
                    if binary:
                        archive.writestr("confido_client/_native.so", b"binary")
                    archive.writestr("confido_client/__init__.py", b"pass\n")
                    archive.writestr("confido_client/httpx_transport.py", b"pass\n")
                    archive.writestr("confido_client/console.py", b"pass\n")
                if accepted:
                    build.inspect_wheel(wheel, pin)
                else:
                    with self.assertRaises(ValueError):
                        build.inspect_wheel(wheel, pin)


if __name__ == "__main__":
    unittest.main()
