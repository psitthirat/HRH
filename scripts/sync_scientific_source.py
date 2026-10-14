"""Hand the canonical scientific source to the presentation/Lab workspace.

The research tree (this repository) owns the scientific code and configuration; the authoring
workspace (workspaces/HRH-authoring) owns presentation, Lab interface and release assembly and
receives a byte-identical copy of the files below.  Decision recorded in
docs/decisions.md (section 10) and PROJECT_LOG.md.

    .venv/bin/python scripts/sync_scientific_source.py --check   # list differences, exit 1 if any
    .venv/bin/python scripts/sync_scientific_source.py --apply   # copy + write the manifest

`--apply` refuses to overwrite a target file that differs from BOTH the current canonical file
and the canonical file recorded in the target's previous manifest (an edit made in the
workspace that would be lost); bring such edits into the research tree first, or pass --force.
The target receives SCIENTIFIC_SOURCE_MANIFEST.json with per-file SHA-256, the research-tree
commit and whether that tree had uncommitted changes, so a Lab release can name the exact
scientific snapshot it packaged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "workspaces" / "HRH-authoring"
MANIFEST = "SCIENTIFIC_SOURCE_MANIFEST.json"
CANONICAL_GLOBS = ["src/chapter4/*.py", "src/chapter5/*.py", "src/services/*.py"]
CANONICAL_FILES = ["config/analysis.toml", "config/source_registry.toml", "config/chapter5.toml",
                   "config/chapter5_health_gain.toml", "config/validation.toml"]
# aggregate data artifacts handed to the Lab: research path -> workspace path
ARTIFACTS = {"outputs/services/service_population.json": "data/workforce_lab/service_population.json",
             "outputs/chapter5/validation/lab_validation.json": "data/workforce_lab/validation_summary.json"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_files() -> list[str]:
    files = [str(p.relative_to(ROOT)) for g in CANONICAL_GLOBS for p in sorted(ROOT.glob(g))]
    return files + [f for f in CANONICAL_FILES if (ROOT / f).exists()]


def git_state() -> dict:
    def run(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    files = canonical_files()
    status = run("status", "--porcelain", "--", *files)
    return dict(commit=run("rev-parse", "HEAD"), canonical_files_uncommitted=bool(status),
                uncommitted_entries=len(status.splitlines()) if status else 0)


def compare(target: Path) -> list[dict]:
    prev = {}
    if (target / MANIFEST).exists():
        prev = {f["path"]: f["sha256"] for f in json.loads((target / MANIFEST).read_text())["files"]}
    rows = []
    for rel in canonical_files():
        src, dst = ROOT / rel, target / rel
        s = sha256(src)
        d = sha256(dst) if dst.exists() else None
        if d == s:
            state = "same"
        elif d is None:
            state = "missing_in_target"
        elif prev.get(rel) == d:
            state = "outdated"                    # target holds the previously synced canonical file
        else:
            state = "edited_in_target"            # would be lost by an overwrite
        rows.append(dict(path=rel, state=state, canonical_sha256=s, target_sha256=d))
    canon = set(canonical_files())
    for g in CANONICAL_GLOBS:
        for p in sorted(target.glob(g)):
            rel = str(p.relative_to(target))
            if rel not in canon:
                rows.append(dict(path=rel, state="only_in_target", canonical_sha256=None, target_sha256=sha256(p)))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite files edited in the target")
    a = ap.parse_args(argv)
    target = a.target.resolve()
    if not target.is_dir():
        print(f"target not found: {target}", file=sys.stderr)
        return 2
    rows = compare(target)
    diff = [r for r in rows if r["state"] != "same"]
    for r in diff:
        print(f"{r['state']:<18} {r['path']}")
    if a.check:
        print(f"{len(rows) - len(diff)} identical, {len(diff)} different")
        return 1 if diff else 0
    edited = [r for r in diff if r["state"] == "edited_in_target"]
    if edited and not a.force:
        print(f"refusing: {len(edited)} file(s) were edited in the target; move those edits into the research "
              "tree or pass --force", file=sys.stderr)
        return 3
    only = [r for r in diff if r["state"] == "only_in_target"]
    if only:
        print(f"note: {len(only)} file(s) exist only in the target and are left untouched", file=sys.stderr)
    for r in diff:
        if r["state"] in ("outdated", "missing_in_target", "edited_in_target"):
            dst = target / r["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / r["path"], dst)
    for src_rel, dst_rel in ARTIFACTS.items():
        if (ROOT / src_rel).exists():
            dst = target / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or sha256(dst) != sha256(ROOT / src_rel):
                shutil.copy2(ROOT / src_rel, dst)
                print(f"artifact {src_rel} -> {dst_rel}")
    sys.path.insert(0, str(ROOT / "src"))
    from chapter4 import config as C4
    from chapter5 import reporting as R5
    manifest = dict(schema="hrh-scientific-source/1", synced_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    source_repository="research tree (HRH)", research_git=git_state(),
                    chapter4_code_hash=C4.code_hash(), chapter5_code_hash=R5.code_hash(),
                    files=[dict(path=rel, sha256=sha256(ROOT / rel)) for rel in canonical_files()],
                    artifacts=[dict(path=dst, source=src, sha256=sha256(ROOT / src)) for src, dst in ARTIFACTS.items()
                               if (ROOT / src).exists()])
    (target / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"synced {sum(r['state'] != 'only_in_target' for r in diff)} file(s); manifest -> {target / MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
