"""Runtime checks public compatibility without retaining build artifacts."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from demo import runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "confido-client-wheel.json").write_text(json.dumps({"version": "0.2.0"}))
        self.info = {
            "client": {"core": {"version": "0.2.0", "pipeline_revision": 2},
                       "wrapper": {"version": "0.2.0"}},
            "wrapper": {"version": "0.2.0"},
        }
        self.console = SimpleNamespace(print_verification=lambda _: None)
        modules = {
            "confido_client": SimpleNamespace(appraise=lambda: None, build_info=lambda: self.info),
            "confido_client.console": self.console,
            "confido_client.httpx_transport": SimpleNamespace(ScopedTransport=lambda: None),
        }
        for patcher in (patch.object(runtime, "ROOT", self.root),
                        patch.object(runtime.importlib, "import_module", side_effect=modules.__getitem__)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_compatible_client_needs_no_manifest_wheel_or_source_fingerprint(self):
        self.assertEqual(runtime.ensure_runtime()["pipeline_revision"], 2)
        (self.root / "application.py").write_text("edited source")
        self.assertEqual(runtime.ensure_runtime()["build_info"], self.info)
        self.assertFalse((self.root / "build").exists())

    def test_incompatible_pipeline_or_missing_api_is_rejected(self):
        self.info["client"]["core"]["pipeline_revision"] = None
        with self.assertRaisesRegex(RuntimeError, "Unsupported verifier pipeline.*run --update"):
            runtime.ensure_runtime()
        self.info["client"]["core"]["pipeline_revision"] = 2
        self.console.print_verification = None
        with self.assertRaisesRegex(RuntimeError, "missing print_verification"):
            runtime.ensure_runtime()

    def test_alpha_sdk_accepts_native_semver_but_requires_the_pinned_python_version(self):
        pin = {"version": "0.2.1a1"}
        (self.root / "confido-client-wheel.json").write_text(json.dumps(pin))
        for part in (self.info["client"]["core"], self.info["client"]["wrapper"]):
            part["version"] = "0.2.1-alpha.1"
        self.info["wrapper"]["version"] = pin["version"]
        self.assertEqual(runtime.ensure_runtime()["client_distribution"], "confido-client==0.2.1a1")
        self.info["wrapper"]["version"] = "0.2.1a2"
        with self.assertRaisesRegex(RuntimeError, "version is incompatible"):
            runtime.ensure_runtime()


if __name__ == "__main__":
    unittest.main()
