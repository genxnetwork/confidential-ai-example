"""Prepare the pinned JAN Confido source used to build the verifier wheel."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "confido-source.json"


def git(*arguments, cwd=None):
    environment = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    result = subprocess.run(
        ["git", *map(str, arguments)],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def checkout_revision(directory, revision):
    git("cat-file", "-e", f"{revision}^{{commit}}", cwd=directory)
    try:
        git("merge-base", "--is-ancestor", revision, "refs/remotes/origin/main", cwd=directory)
    except RuntimeError as error:
        raise RuntimeError("Pinned Confido commit is not on the fetched main branch") from error
    if git("status", "--porcelain", cwd=directory):
        raise RuntimeError(f"Confido source has local changes: {directory}")
    if git("rev-parse", "HEAD", cwd=directory) != revision or git(
        "branch", "--show-current", cwd=directory
    ):
        git("checkout", "--quiet", "--detach", revision, cwd=directory)
    if not (directory / "scripts/source_fingerprint.py").is_file():
        raise RuntimeError(f"Pinned Confido source is incomplete: {directory}")


def ensure_checkout(repository, revision, directory):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Confido revision must be a full Git commit SHA")
    directory = Path(directory).resolve()
    directory.parent.mkdir(parents=True, exist_ok=True)
    if directory.exists():
        if not (directory / ".git").is_dir():
            raise RuntimeError(f"Confido source directory is not a Git checkout: {directory}")
        if git("rev-parse", "--verify", "HEAD", cwd=directory) != revision:
            git("fetch", "--quiet", "origin", "main", cwd=directory)
        checkout_revision(directory, revision)
    else:
        with tempfile.TemporaryDirectory(prefix="confido-fetch-", dir=directory.parent) as staging:
            candidate = Path(staging) / "checkout"
            git(
                "clone", "--quiet", "--no-tags", "--single-branch",
                "--branch", "main", repository, candidate,
            )
            checkout_revision(candidate, revision)
            candidate.rename(directory)
    print(f"JAN Confido source {revision[:12]}: {directory}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(SOURCE.read_text())
    try:
        ensure_checkout(source["repository"], source["commit"], args.directory)
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Unable to prepare pinned JAN Confido source: {error}\n")


if __name__ == "__main__":
    main()
