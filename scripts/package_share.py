"""Build a local source package with pilot evidence, excluding environments and raw market data."""
import argparse
import hashlib
import json
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ("README.md", "LICENSE", ".gitattributes", "requirements-design.lock", "requirements-pilot.lock", "pyproject.toml", ".gitignore")
FOLDERS = ("backend", "docs", "fixtures", "frontend", "middleware", "schemas", "scripts", "references", "pilot", "evidrava", "sebi_benchmark", "tests")
EXCLUDED = {"__pycache__", "node_modules", "_work", ".work", ".git"}


def share_files():
    paths = [ROOT / x for x in FILES if (ROOT / x).is_file()]
    for folder in FOLDERS:
        base = ROOT / folder
        if base.exists():
            paths.extend(p for p in base.rglob("*") if p.is_file())
    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f"Linked or external input is not permitted: {relative}")
        if any(x in EXCLUDED or x.startswith(".venv") for x in relative.parts):
            continue
        if relative.parts[:2] == ("pilot", "market_data"):
            continue
        if path.suffix.lower() in {".pyc", ".pyo", ".zip", ".tmp", ".log"}:
            continue
        yield path, relative.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="New local ZIP path; existing files are not overwritten")
    args = parser.parse_args()
    target = args.out.resolve()
    if target.suffix.lower() != ".zip":
        raise SystemExit("Output must be a ZIP file.")
    if not target.is_relative_to(ROOT.resolve()):
        raise SystemExit("Output must be inside this project.")
    if target.exists():
        raise SystemExit("Output already exists; choose a new filename.")
    target.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in share_files():
            data = path.read_bytes()
            archive.writestr(relative, data)
            entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        manifest = {"project": project["name"], "version": project["version"],
                    "package_kind": "source-and-pilot", "publication": "local_only",
                    "excludes": ["virtual environments", "caches", "raw market data", "working copies", "generated runs", "other ZIP files"],
                    "entries": entries}
        archive.writestr("PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert not any(part.startswith(".venv") or part in EXCLUDED
                       for name in archive.namelist() for part in Path(name).parts)
        for entry in entries:
            assert hashlib.sha256(archive.read(entry["path"])).hexdigest() == entry["sha256"]
    print(json.dumps({"output": str(target), "files": len(entries) + 1, "bytes": target.stat().st_size,
                      "environment_included": False, "published": False}, indent=2))


if __name__ == "__main__":
    main()
