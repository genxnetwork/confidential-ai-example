"""Reject a wheel that does not match the application's Confido client pin."""

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "prepare_client_wheel",
    Path(__file__).resolve().parents[1] / "scripts/prepare_client_wheel.py",
)
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class ClientWheelTests(unittest.TestCase):
    def test_distribution_version_and_native_module_are_checked(self):
        pin = {"distribution": "confido-client", "version": "0.2.0"}
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / "candidate.whl"
            for name, version, binary, accepted in (
                ("confido-client", "0.2.0", True, True),
                ("other-client", "0.2.0", True, False),
                ("confido-client", "0.3.0", True, False),
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
                if accepted:
                    self.assertEqual(build.inspect_wheel(wheel, pin)[0],
                                     "confido_client/_native.so")
                else:
                    with self.assertRaises(ValueError):
                        build.inspect_wheel(wheel, pin)


if __name__ == "__main__":
    unittest.main()
