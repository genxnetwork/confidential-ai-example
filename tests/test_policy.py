"""Application policy files select an HTTPS origin and a local verifier policy."""

import json
import tempfile
import unittest
from pathlib import Path

from demo.policy import load_policy


class PolicyTests(unittest.TestCase):
    def test_local_verifier_policy_is_loaded_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "verifier.json").write_text('{"schema_version": 2}')
            (root / "app.json").write_text(json.dumps({
                "schema_version": 2,
                "origin": "https://example.test",
                "verifier_policy": "verifier.json",
            }))
            app = load_policy(root / "app.json")
            self.assertEqual(app["origin"], "https://example.test")
            self.assertEqual(app["verifier_bytes"], b'{"schema_version": 2}')

    def test_origin_and_verifier_path_cannot_escape_local_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.json").write_text(json.dumps({
                "schema_version": 2,
                "origin": "https://example.test/path",
                "verifier_policy": "verifier.json",
            }))
            with self.assertRaisesRegex(ValueError, "bare HTTPS origin"):
                load_policy(root / "app.json")

            (root / "app.json").write_text(json.dumps({
                "schema_version": 2,
                "origin": "https://example.test",
                "verifier_policy": "../outside.json",
            }))
            with self.assertRaisesRegex(ValueError, "must be local"):
                load_policy(root / "app.json")


if __name__ == "__main__":
    unittest.main()
