"""Download a wheel from the latest successful Confido client build on GitHub."""

import hashlib
import json
import platform
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


def fetch(url):
    """Fetch public build data without exposing remote error text in diagnostics."""
    request = urllib.request.Request(url, headers={
        "User-Agent": "confidential-ai-example/0.2.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            "Cannot download Confido client wheel. Retry the Docker image build, "
            "or run make build GENXT_DEMO_CLIENT_WHEEL=/path/to/wheel.whl."
        ) from error


def artifact_name(source):
    """Select the configured artifact for this interpreter and image platform."""
    target = (
        f"{platform.system().lower()}-{platform.machine().lower()}-"
        f"cp{sys.version_info.major}{sys.version_info.minor}"
    )
    if platform.python_implementation() != "CPython" or target not in source["artifacts"]:
        raise ValueError(
            f"No Confido client CI wheel configured for {target}. "
            "Use a supported CPython interpreter or supply GENXT_DEMO_CLIENT_WHEEL."
        )
    return source["artifacts"][target]


def latest_artifact(source, name):
    """Select one unexpired artifact from the latest successful branch push build."""
    api = f"https://api.github.com/repos/{source['repository']}/actions"
    query = urllib.parse.urlencode({
        "branch": source["branch"], "status": "success", "event": "push", "per_page": 1,
    })
    runs = json.loads(fetch(f"{api}/workflows/{source['workflow']}/runs?{query}"))[
        "workflow_runs"
    ]
    if not runs:
        raise ValueError("No successful Confido client build on the configured branch")
    run = runs[0]
    query = urllib.parse.urlencode({"name": name})
    artifacts = json.loads(fetch(f"{api}/runs/{run['id']}/artifacts?{query}"))["artifacts"]
    artifacts = [a for a in artifacts if a["name"] == name and not a["expired"]]
    if len(artifacts) != 1:
        raise ValueError(
            f"Latest successful Confido build {run['id']} has no unique unexpired {name}"
        )
    artifact = artifacts[0]
    digest = artifact.get("digest") or ""
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError("GitHub artifact has no SHA-256 digest")
    return run, artifact


def extract_wheel(archive, destination):
    """Unpack a verified artifact only when it contains one plain wheel filename."""
    archive_path = destination / "artifact.zip"
    archive_path.write_bytes(archive)
    with zipfile.ZipFile(archive_path) as bundle:
        entries = bundle.namelist()
        if (
            len(entries) != 1
            or Path(entries[0]).name != entries[0]
            or not entries[0].endswith(".whl")
        ):
            raise ValueError("Expected exactly one wheel in the GitHub artifact")
        bundle.extract(entries[0], destination)
    return destination / entries[0]


def download_latest(pin, destination):
    """Verify the selected GitHub archive digest before extracting its wheel.

    Return the wheel path and exact upstream provenance. Missing artifacts or a
    digest mismatch fail the build rather than selecting an older dependency.
    """
    source = pin["github"]
    name = artifact_name(source)
    run, artifact = latest_artifact(source, name)
    provenance = {
        "repository": source["repository"],
        "workflow": source["workflow"],
        "branch": source["branch"],
        "run_id": run["id"],
        "source_commit": run["head_sha"],
        "artifact_id": artifact["id"],
        "artifact_name": name,
        "archive_sha256": artifact["digest"].removeprefix("sha256:"),
    }
    print(f"Confido client: {source['repository']} run {run['id']} ({run['head_sha']})")
    # nightly.link redirects to the public GitHub artifact without requiring a token.
    archive = fetch(
        f"https://nightly.link/{source['repository']}/actions/artifacts/{artifact['id']}.zip"
    )
    if hashlib.sha256(archive).hexdigest() != provenance["archive_sha256"]:
        raise ValueError("Downloaded GitHub artifact SHA-256 differs from GitHub metadata")
    return extract_wheel(archive, destination), provenance
