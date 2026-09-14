#!/usr/bin/env python3
"""Preserve an approved local draft; approval-ref records, not authenticates, consent."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def view_directory(folder: Path) -> Path:
    name = "deliverables"
    for ancestor in (folder, *folder.parents):
        manifest = ancestor / ".agents/harness.yaml"
        if manifest.is_file():
            config = json.loads(manifest.read_text(encoding="utf-8"))
            name = config.get("artifact_chain", {}).get("deliverables", {}).get("dir", name)
            break
    path = Path(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("deliverables.dir must be relative to the change folder")
    for i in range(1, len(path.parts) + 1):
        if folder.joinpath(*path.parts[:i]).is_symlink():
            raise ValueError("deliverables must not contain symlinks")
    return folder / path


def verify(snapshot: Path) -> list[str]:
    try:
        if snapshot.is_symlink() or (snapshot / "snapshot.json").is_symlink():
            raise ValueError("symlink baseline")
        data = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))
        if data.get("version") != 1 or not str(data.get("approval_ref", "")).strip():
            raise ValueError("missing version/approval reference")
        files = data.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("empty file manifest")
        problems = []
        for rel, expected in files.items():
            parts = Path(rel).parts
            if Path(rel).is_absolute() or ".." in parts or not parts:
                raise ValueError("invalid baseline path")
            path = snapshot / rel
            if any((snapshot.joinpath(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1)):
                raise ValueError("symlink baseline file")
            if not path.is_file() or digest(path) != expected:
                problems.append(f"approved baseline changed or missing: {rel}")
        return problems
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return [f"invalid agreement snapshot: {exc}"]


def freeze(folder: Path, revision: str, approval_ref: str) -> Path:
    if not re.fullmatch(r"[0-9]{3,}", revision) or not approval_ref.strip():
        raise ValueError("use a numeric revision (001) and a real approval reference")
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("change folder must be a real directory")
    sources = [folder / name for name in ("intent.md", "spec.md", "plan.md", "scope.json") if (folder / name).exists()]
    if not any(p.name in ("spec.md", "plan.md") for p in sources):
        raise ValueError("a spec or plan must exist before preserving agreement")
    views = view_directory(folder)
    sources += sorted(views.glob("*.html")) if views.is_dir() else []
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size == 0 for p in sources):
        raise ValueError("draft files must be nonempty regular files")
    agreements = folder / "agreements"
    if agreements.is_symlink():
        raise ValueError("agreements must not be a symlink")
    agreements.mkdir(exist_ok=True)
    target = agreements / revision
    if target.exists() or target.is_symlink():
        raise ValueError(f"revision {revision} already exists; preserve it and use a new revision")
    staging = Path(tempfile.mkdtemp(prefix=".draft-", dir=agreements))
    try:
        files = {}
        for source in sources:
            rel = source.relative_to(folder)
            dest = staging / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            files[rel.as_posix()] = digest(dest)
        (staging / "snapshot.json").write_text(json.dumps({
            "version": 1, "approval_ref": approval_ref.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(), "files": files,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Reserve the destination exclusively; a simultaneous writer cannot replace it.
        target.mkdir()
        try:
            for child in staging.iterdir():
                shutil.move(str(child), target / child.name)
        except Exception:
            shutil.rmtree(target)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="change folder; with --check, snapshot folder")
    parser.add_argument("--revision", default="001")
    parser.add_argument("--approval-ref")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            problems = verify(args.folder)
            print("\n".join(problems) if problems else "PASS: agreement snapshot integrity")
            return int(bool(problems))
        path = freeze(args.folder, args.revision, args.approval_ref or "")
        print(f"Agreement-Ref: agreements/{path.name}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"agreement-snapshot: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
