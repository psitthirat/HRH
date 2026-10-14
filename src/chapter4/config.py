"""Paths and the single authoritative configuration for Chapter 4.

Everything that decides a number (years, scopes, seeds, assumptions) is read from
config/analysis.toml.  Raw paths come from config/source_registry.toml.  Nothing here
scans data/cold_data/ or archive/.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


def _find_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "config" / "analysis.toml").exists():
            return p
    raise FileNotFoundError("config/analysis.toml not found above " + str(here))


ROOT = _find_root()
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
PROCESSED = DATA_DIR / "processed"
OUTPUTS = ROOT / "outputs"
SHARED_OUT = OUTPUTS / "shared"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
FONT_DIR = ROOT / "assets" / "fonts"
EXCLUDED_DIRS = (DATA_DIR / "cold_data", ROOT / "archive")

with open(CONFIG_DIR / "analysis.toml", "rb") as _fh:
    CFG: dict = tomllib.load(_fh)
with open(CONFIG_DIR / "source_registry.toml", "rb") as _fh:
    SOURCES: dict = tomllib.load(_fh)

BE = CFG["project"]["be_offset"]
SEED = CFG["project"]["random_seed"]
CADRES: list[str] = CFG["cadres"]["main"]
CADRE_EN: dict[str, str] = CFG["cadres"]["en"]
BANGKOK: str = CFG["geography"]["bangkok"]
Y0, Y1 = CFG["years"]["long_first"], CFG["years"]["long_last"]
YEARS = list(range(Y0, Y1 + 1))


def be(year) -> int:
    """Gregorian year -> Buddhist Era year."""
    return int(year) + BE


def source_path(source_id: str, **fmt) -> Path:
    """Absolute path of a registered source; refuses anything in an excluded folder."""
    s = SOURCES[source_id]
    p = ROOT / s["path"]
    if "pattern" in s and fmt:
        p = p / s["pattern"].format(**fmt)
    for ex in EXCLUDED_DIRS:
        if ex in p.parents:
            raise ValueError(f"{source_id} points into an excluded folder: {p}")
    return p


def source_fingerprint(source_id: str) -> str:
    """Content hash of a registered source.  A source that lists `files` inside a shared
    folder (data/epi holds several sources) is hashed on those files only, so adding an
    unrelated file to the folder does not invalidate it."""
    s = SOURCES[source_id]
    if "files" in s:
        h = hashlib.sha256()
        for f in sorted(s["files"]):
            h.update(f.encode())
            h.update(file_sha256(source_path(source_id) / f).encode())
        return h.hexdigest()
    return file_sha256(source_path(source_id))


def geo_path(name: str = "geo_prov.geojson") -> Path:
    """Boundary/crosswalk file: data/map/ (since 14 Oct 2026), falling back to the former output/map/
    so workspaces that still hold the old layout keep working."""
    for d in (DATA_DIR / "map", ROOT / "output" / "map"):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(f"{name} not found in data/map or output/map")


def section_dirs(section: str) -> dict[str, Path]:
    """Output folders for one section, e.g. section_dirs('4_3')."""
    base = OUTPUTS / f"chapter{section}"
    out = {"base": base, "tables": base / "tables", "figures": base / "figures",
           "figure_data": base / "figure_data"}
    for p in out.values():
        p.mkdir(parents=True, exist_ok=True)
    return out


def file_sha256(path: Path, limit_mb: int = 1000) -> str:
    path = Path(path)
    if path.is_dir():
        h = hashlib.sha256()
        for f in sorted(path.rglob("*")):
            if f.is_file() and f.name != ".DS_Store":
                h.update(f.name.encode())
                h.update(file_sha256(f).encode())
        return h.hexdigest()
    if not path.exists():
        return "missing"
    if path.stat().st_size > limit_mb * 1024 * 1024:
        st = path.stat()
        return f"size{st.st_size}_mtime{int(st.st_mtime)}"
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_hash() -> str:
    """Hash of the shared package source, used to key the processed-data cache."""
    h = hashlib.sha256()
    for f in sorted((ROOT / "src" / "chapter4").glob("*.py")):
        h.update(f.read_bytes())
    h.update((CONFIG_DIR / "analysis.toml").read_bytes())
    h.update((CONFIG_DIR / "source_registry.toml").read_bytes())
    return h.hexdigest()[:16]


def code_hash_ingest() -> str:
    """Hash of the ingestion code and source registry only: editing a model must not
    force a re-read of the raw workbooks, but editing a reader must."""
    h = hashlib.sha256()
    h.update((ROOT / "src" / "chapter4" / "ingest.py").read_bytes())
    h.update((CONFIG_DIR / "source_registry.toml").read_bytes())
    return h.hexdigest()[:16]


@dataclass
class Scenario:
    """A named exploratory override.  Writes to outputs/scenarios/<name>/, never canonical."""
    name: str
    cfg: dict

    def dirs(self, section: str) -> dict[str, Path]:
        base = OUTPUTS / "scenarios" / self.name / f"chapter{section}"
        out = {"base": base, "tables": base / "tables", "figures": base / "figures",
               "figure_data": base / "figure_data"}
        for p in out.values():
            p.mkdir(parents=True, exist_ok=True)
        return out


def scenario(name: str, **overrides) -> Scenario:
    """Return a copy of CFG with dotted-key overrides, e.g. scenario('ref2024', **{'models.reference_year': 2024})."""
    if name in ("", "canonical"):
        raise ValueError("a scenario needs its own name")
    cfg = copy.deepcopy(CFG)
    for k, v in overrides.items():
        node = cfg
        parts = k.split(".")
        for p in parts[:-1]:
            node = node[p]
        node[parts[-1]] = v
    return Scenario(name, cfg)


def effective_config(section: str) -> str:
    """Pretty JSON of the configuration blocks a section depends on, for display at the top of a notebook."""
    keys = {"4_1": ["years", "cadres", "sectors", "services"],
            "4_2": ["years", "cadres", "universes", "benchmark", "hdc_screen", "time_scenario",
                    "models", "age_weights"],
            "4_3": ["years", "geography", "inequality", "models"],
            "4_4": ["years", "geography", "flows"],
            "4_5": ["years", "geography", "burden", "models", "inequality"],
            "4_6": ["years", "geography", "cadres", "sectors"]}.get(section, list(CFG))
    return json.dumps({k: CFG[k] for k in keys if k in CFG} | {"random_seed": SEED},
                      ensure_ascii=False, indent=1)
