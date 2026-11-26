"""Check successful build selection and downloaded artifact integrity."""

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import download_client_wheel as download


class DownloadClientWheelTests(unittest.TestCase):
    def setUp(self):
        self.pin = json.loads(
            (Path(__file__).resolve().parents[1] / "confido-client-wheel.json").read_text()
        )
        self.name = "client-wheel-ubuntu-22.04-py3.15"
        self.wheel = "confido_client-0.2.0-cp315-cp315-manylinux_2_34_x86_64.whl"
        self.runs = {"workflow_runs": [{"id": 42, "head_sha": "a" * 40}]}
        self.payload = self.bundle(self.wheel)
        self.artifacts = {"artifacts": [{
            "id": 7, "name": self.name, "expired": False,
            "digest": "sha256:" + hashlib.sha256(self.payload).hexdigest(),
        }]}

    @staticmethod
    def bundle(name):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(name, b"wheel bytes")
        return buffer.getvalue()

    def run_download(self, directory, payload=None):
        with (
            patch.object(download, "artifact_name", return_value=self.name),
            patch.object(download, "fetch", side_effect=[
                json.dumps(self.runs).encode(), json.dumps(self.artifacts).encode(),
                self.payload if payload is None else payload,
            ]) as fetch,
        ):
            result = download.download_latest(self.pin, Path(directory))
        return result, [call.args[0] for call in fetch.call_args_list]

    def test_latest_successful_main_push_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            (wheel, source), urls = self.run_download(directory)
            self.assertEqual(wheel.read_bytes(), b"wheel bytes")
        self.assertIn("/workflows/client-wheel.yml/runs?", urls[0])
        self.assertIn("branch=main&status=success&event=push&per_page=1", urls[0])
        self.assertIn("/runs/42/artifacts?", urls[1])
        self.assertEqual(urls[2], "https://nightly.link/jandigitrust/confido/actions/artifacts/7.zip")
        self.assertEqual(source["run_id"], 42)
        self.assertEqual(source["source_commit"], "a" * 40)
        self.assertEqual(source["archive_sha256"], hashlib.sha256(self.payload).hexdigest())

    def test_corrupted_download_is_rejected_before_opening_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
                self.run_download(directory, b"corrupted archive")
            self.assertEqual(list(Path(directory).iterdir()), [])

if __name__ == "__main__":
    unittest.main()
