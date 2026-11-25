"""Archive transport dependency attribution files from cargo metadata; never build code.

Usage: cargo metadata --locked --format-version 1 ... > metadata.json
       python3 scripts/collect_licenses.py metadata.json output.tar.gz
"""

import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CRATES = {
    PROJECT_ROOT / "native_transport"
}
ATTRIBUTION_PREFIXES = (
    "license",
    "licence",
    "copying",
    "copyright",
    "notice",
    "authors",
    "third_party_notices",
)


def attribution_file(path):
    name = path.name.lower()
    return name.endswith(("-license", "-licence", "_license", "_licence")) or any(
        name == prefix or name.startswith(prefix + separator)
        for prefix in ATTRIBUTION_PREFIXES
        for separator in (".", "-", "_")
    )


def repository_root(directory):
    for parent in (directory, *directory.parents):
        if (parent / ".git").exists():
            return parent
    return directory


def add_bytes(archive, name, content):
    entry = tarfile.TarInfo(name)
    entry.size = len(content)
    entry.mode = 0o644
    archive.addfile(entry, io.BytesIO(content))


def collect(
    metadata,
    output,
    *,
    project_crates=PROJECT_CRATES,
    supplement_root=PROJECT_ROOT,
):
    if not metadata.get("resolve"):
        raise ValueError("Full cargo metadata with dependency resolution is required")
    resolved = {node["id"] for node in metadata["resolve"]["nodes"]}
    records = []
    files = {}
    for package in sorted(metadata["packages"], key=lambda p: p["id"]):
        crate_root = Path(package["manifest_path"]).resolve().parent
        if package["id"] not in resolved or crate_root in project_crates:
            continue
        label = f"{package['name']}-{package['version']}"
        # Cargo may resolve two sources with the same name and version.
        label = f"{len(records):04d}-{label}"
        candidates = {
            path: path.relative_to(crate_root)
            for path in crate_root.rglob("*")
            if path.is_file()
            and not {".git", "target"}.intersection(path.relative_to(crate_root).parts)
            and (
                attribution_file(path)
                or any(
                    part.lower()
                    in {"license", "licenses", "licence", "licences", "notices"}
                    for part in path.relative_to(crate_root).parts[:-1]
                )
            )
        }
        if package.get("license_file"):
            path = Path(package["license_file"])
            if not path.is_absolute():
                path = crate_root / path
            candidates[path] = Path("declared-license") / path.name
        revision = None
        # Workspace crates can inherit their licence and notices from the
        # repository root, whether Cargo resolves them by path or by Git.
        source = package.get("source")
        if source is None or source.startswith("git+"):
            root = repository_root(crate_root)
            for path in root.iterdir():
                if path.is_file() and attribution_file(path):
                    candidates[path] = Path("repository") / path.name
            third_party = root / "third_party"
            if third_party.is_dir():
                for path in third_party.rglob("*"):
                    if path.is_file() and attribution_file(path):
                        candidates[path] = Path("repository") / path.relative_to(root)
            if (root / ".git").exists():
                revision = subprocess.check_output(
                    ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
                ).strip()
                if source and revision != source.rsplit("#", 1)[-1]:
                    raise ValueError(
                        f"Checked-out Git revision differs for {package['id']}"
                    )
        if not candidates:
            supplement = (
                supplement_root / "third_party" / f"{package['name']}-{package['version']}"
            )
            provenance = supplement / "provenance.json"
            if provenance.is_file():
                record = json.loads(provenance.read_text())
                vcs = crate_root / ".cargo_vcs_info.json"
                if (
                    record["crate"] != package["name"]
                    or record["version"] != package["version"]
                    or (
                        "license" in record
                        and record["license"] != package.get("license")
                    )
                    or not vcs.is_file()
                    or json.loads(vcs.read_text())["git"]["sha1"] != record["commit"]
                ):
                    raise ValueError(
                        f"Attribution provenance differs for {package['id']}"
                    )
                for item in record["files"]:
                    path = supplement / item["file"]
                    if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                        raise ValueError(f"Attribution digest differs: {path}")
                    candidates[path] = Path("supplement") / path.name
                candidates[provenance] = Path("supplement/provenance.json")
            if not candidates:
                raise ValueError(
                    f"No attribution files found for {package['id']}; review required"
                )
        paths = []
        for path, relative in sorted(candidates.items()):
            name = f"third-party/{label}/{relative.as_posix()}"
            files[name] = path.read_bytes()
            paths.append(name)
        records.append(
            {
                "name": package["name"],
                "version": package["version"],
                "id": package["id"],
                "license": package.get("license"),
                "repository": package.get("repository"),
                "source": package.get("source"),
                "revision": revision,
                "files": paths,
            }
        )
    with tarfile.open(output, "w:gz") as archive:
        for name, content in sorted(files.items()):
            add_bytes(archive, name, content)
        add_bytes(
            archive,
            "third-party/packages.json",
            (json.dumps(records, indent=2) + "\n").encode(),
        )


if __name__ == "__main__":
    collect(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
