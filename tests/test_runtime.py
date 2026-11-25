"""Reject a mixed or stale client wheel before contacting an endpoint."""

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from demo import runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "build/wheels").mkdir(parents=True)
        self.binary = self.root / "_native.so"
        self.binary.write_bytes(b"client binary")
        self.adapter = self.root / "httpx_transport.py"
        self.adapter.write_text("client adapter")
        self.wheel = self.root / "build/wheels/confido_client-0.2.0-test.whl"
        self.wheel.write_bytes(b"client wheel")
        self.info = {
            "client": {
                "core": {
                    "version": "0.2.0",
                    "pipeline_revision": 2,
                    "source_sha256": "core-source",
                },
                "wrapper": {"version": "0.2.0", "source_sha256": "client-source"},
            },
            "wrapper": {"version": "0.2.0", "source_sha256": "binding-source"},
        }
        self.pin = {
            "distribution": "confido-client",
            "version": "0.2.0",
            "core_source_sha256": "core-source",
            "client_source_sha256": "client-source",
            "wrapper_source_sha256": "binding-source",
        }
        (self.root / "confido-client-wheel.json").write_text(json.dumps(self.pin))
        self.manifest = {
            "schema_version": 2,
            "pipeline_revision": 2,
            "client_distribution": "confido-client==0.2.0",
            "sources": {"application": "application-source"},
            "artifact": {
                "binary_sha256": runtime.file_digest(self.binary),
                "python_files": {"httpx_transport.py": runtime.file_digest(self.adapter)},
                "wheel_sha256": runtime.file_digest(self.wheel),
                "wheel": self.wheel.name,
                "build_info": self.info,
            },
        }
        (self.root / "build/runtime.json").write_text(json.dumps(self.manifest))
        self.module = SimpleNamespace(
            __file__=str(self.binary), build_info=lambda: self.info
        )

    def check(self, *, source="application-source", packaged=False):
        with (
            patch.object(runtime, "ROOT", self.root),
            patch.object(runtime.importlib, "import_module", return_value=self.module),
            patch.object(runtime, "source_digest", return_value=source),
            patch.dict(runtime.os.environ, {
                "CONFIDO_RUNTIME_MODE": "packaged" if packaged else "development"
            }),
        ):
            return runtime.ensure_runtime()

    def test_loaded_wheel_and_packaged_runtime(self):
        self.assertEqual(self.check()["pipeline_revision"], 2)
        self.wheel.unlink()
        self.assertEqual(self.check(packaged=True)["pipeline_revision"], 2)
        with self.assertRaisesRegex(RuntimeError, "Local wheel differs"):
            self.check()

    def test_changed_binary_source_or_pin_is_rejected(self):
        self.binary.write_bytes(b"different binary")
        with self.assertRaisesRegex(RuntimeError, "binary differs"):
            self.check(packaged=True)
        self.binary.write_bytes(b"client binary")
        self.adapter.write_text("changed adapter")
        with self.assertRaisesRegex(RuntimeError, "Python adapter differs"):
            self.check(packaged=True)
        self.adapter.write_text("client adapter")
        with self.assertRaisesRegex(RuntimeError, "Caller sources differ"):
            self.check(source="changed")
        self.pin["client_source_sha256"] = "other-source"
        (self.root / "confido-client-wheel.json").write_text(json.dumps(self.pin))
        with self.assertRaisesRegex(RuntimeError, "sources differ from pin"):
            self.check(packaged=True)

    def test_changed_sources_during_preparation_preserve_existing_manifest(self):
        script = Path(__file__).resolve().parents[1] / "scripts/prepare_client_wheel.py"
        spec = importlib.util.spec_from_file_location("prepare_client_wheel", script)
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        candidate = self.root / "confido_client-0.2.0-test.whl"
        with zipfile.ZipFile(candidate, "w") as archive:
            archive.writestr(
                "confido_client-0.2.0.dist-info/METADATA",
                "Metadata-Version: 2.4\nName: confido-client\nVersion: 0.2.0\n",
            )
            archive.writestr("confido_client/_native.so", b"new binary")
            archive.writestr("confido_client/__init__.py", b"pass\n")
            archive.writestr("confido_client/httpx_transport.py", b"pass\n")
        previous = (self.root / "build/runtime.json").read_bytes()
        with (
            patch.object(build, "ROOT", self.root),
            patch.object(
                build,
                "source_digest",
                side_effect=("application-source", "changed-source"),
            ),
            patch.object(build, "probe_build_info", return_value=self.info),
        ):
            with self.assertRaisesRegex(RuntimeError, "changed during"):
                build.prepare(candidate)
        self.assertEqual((self.root / "build/runtime.json").read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
