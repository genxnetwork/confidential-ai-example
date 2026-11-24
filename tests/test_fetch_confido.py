"""The demo build must use the pinned Confido commit, even after main advances."""

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.fetch_confido import ensure_checkout


def run_git(directory, *arguments):
    return subprocess.check_output(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", *arguments],
        cwd=directory,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


class FetchConfidoTests(unittest.TestCase):
    def test_pinned_commit_is_reused_offline_and_local_edits_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            run_git(source, "init", "-b", "main")
            (source / "scripts").mkdir()
            (source / "scripts/source_fingerprint.py").write_text("# test fixture\n")
            sample = source / "lib.txt"
            sample.write_text("pinned\n")
            run_git(source, "add", ".")
            run_git(source, "commit", "-m", "pinned")
            revision = run_git(source, "rev-parse", "HEAD")
            sample.write_text("later main\n")
            run_git(source, "commit", "-am", "later")

            checkout = root / "cache" / "confido-src"
            with redirect_stdout(io.StringIO()):
                ensure_checkout(str(source), revision, checkout)
            self.assertEqual((checkout / "lib.txt").read_text(), "pinned\n")
            self.assertEqual(run_git(checkout, "rev-parse", "HEAD"), revision)

            source.rename(root / "source-offline")
            with redirect_stdout(io.StringIO()):
                ensure_checkout(str(source), revision, checkout)
            (checkout / "lib.txt").write_text("local edit\n")
            with self.assertRaisesRegex(RuntimeError, "local changes"):
                ensure_checkout(str(source), revision, checkout)


if __name__ == "__main__":
    unittest.main()
