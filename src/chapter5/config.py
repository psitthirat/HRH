"""Configuration, paths and the effective-configuration export for Chapter 5.

`load(overrides)` returns a validated copy of config/chapter5.toml.  Overrides use dotted
keys (``{"supply.annual_path": 2500}``) and send every output to a separately named scenario
folder, so a what-if run can never overwrite the canonical plans.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from chapter4 import config as C4

ROOT = C4.ROOT
CONFIG_PATH = ROOT / "config" / "chapter5.toml"
OUT_CANONICAL = ROOT / "outputs" / "chapter5"
OUT_SCENARIOS = ROOT / "outputs" / "chapter5_scenarios"
BE = C4.BE

with open(CONFIG_PATH, "rb") as _fh:
    RAW: dict = tomllib.load(_fh)

UNITS = {
    "supply.annual_path": "accepted starts per year (managed 76-province system)",
    "supply.national_graduates": "graduates per year (national)",
    "targets.reference_per_1000": "physicians per 1,000 population or equivalent units",
    "allocation.cap_fraction_of_opening_stock": "fraction of opening headcount per year",
    "allocation.main_transfer_fraction": "fraction of eligible opening headcount per year",
    "allocation.national_transfer_budget_fraction": "fraction of national eligible opening headcount per year",
    "allocation.protected_survivor_fraction": "fraction of expected surviving opening headcount",
    "services.op_minutes": "minutes per OP visit (allocation weight)",
    "services.adjrw_minutes": "minutes per AdjRW (allocation weight)",
    "departures.workload_departure_elasticity": "log-log, resignations on OP visits per physician",
}


def be(year: int) -> int:
    return int(year) + BE


@dataclass
class Settings:
    cfg: dict
    name: str = "canonical"
    overrides: dict = field(default_factory=dict)

    # ---- convenience
    def get(self, dotted: str):
        node = self.cfg
        for p in dotted.split("."):
            node = node[p]
        return node

    @property
    def base_year(self) -> int:
        return int(self.cfg["project"]["baseline_year_ce"])

    @property
    def years(self) -> list[int]:
        p = self.cfg["project"]
        return list(range(int(p["allocation_first_ce"]), int(p["allocation_last_ce"]) + 1))

    @property
    def seed(self) -> int:
        return int(self.cfg["project"]["random_seed"])

    @property
    def out(self) -> Path:
        base = OUT_CANONICAL if self.name == "canonical" else OUT_SCENARIOS / self.name
        return base

    def dirs(self) -> dict[str, Path]:
        d = {k: self.out / k for k in ["tables", "figures", "plot_data", "plans", "validation", "cache"]}
        d["base"] = self.out
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.cfg, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def effective_table(self):
        """One row per leaf value with its provenance class and unit."""
        import pandas as pd
        prov = self.cfg.get("provenance", {})
        rows = []

        def walk(node, prefix):
            for k, v in node.items():
                key = f"{prefix}.{k}" if prefix else k
                if key == "provenance":
                    continue
                if isinstance(v, dict) and not key.startswith("demography.migration_scenarios"):
                    walk(v, key)
                else:
                    rows.append(dict(key=key, value=json.dumps(v, ensure_ascii=False),
                                     provenance=prov.get(key, "convention" if key.split(".")[0] in
                                                         ("project", "figures", "evaluation") else "setting"),
                                     unit=UNITS.get(key, ""),
                                     overridden=key in self.overrides))
        walk(self.cfg, "")
        return pd.DataFrame(rows)


def _set(cfg: dict, dotted: str, value):
    node = cfg
    parts = dotted.split(".")
    for p in parts[:-1]:
        if p not in node:
            raise KeyError(f"unknown configuration key {dotted!r}")
        node = node[p]
    if parts[-1] not in node:
        raise KeyError(f"unknown configuration key {dotted!r}")
    old = node[parts[-1]]
    if isinstance(old, bool):
        value = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes")
    elif isinstance(old, int) and not isinstance(value, (list, dict)):
        value = int(float(value)) if float(value).is_integer() else float(value)
    elif isinstance(old, float) and not isinstance(value, (list, dict)):
        value = float(value)
    node[parts[-1]] = value


def validate(cfg: dict) -> list[str]:
    """Hard errors for impossible settings; returns warnings (e.g. a floor the pool cannot meet)."""
    warn = []
    p = cfg["project"]
    n = int(p["allocation_last_ce"]) - int(p["allocation_first_ce"]) + 1
    if n != 15 or int(p["allocation_first_ce"]) != int(p["baseline_year_ce"]) + 1:
        raise ValueError(f"the plan must have exactly 15 allocation years after the baseline; got {n}")
    a = cfg["allocation"]
    for k in ["cap_fraction_of_opening_stock", "main_transfer_fraction", "national_transfer_budget_fraction",
              "protected_survivor_fraction"]:
        if not 0 <= float(a[k]) <= 1:
            raise ValueError(f"allocation.{k} must be a fraction in [0, 1]")
    if a["cap_mode"] not in ("gross_arrivals", "net_growth"):
        raise ValueError("allocation.cap_mode must be gross_arrivals or net_growth")
    if a["origin_protection_mode"] not in ("limited_drawdown", "surplus_only"):
        raise ValueError("allocation.origin_protection_mode must be limited_drawdown or surplus_only")
    if a["eligibility_network"] not in ("complete_76", "within_health_region"):
        raise ValueError("allocation.eligibility_network must be complete_76 or within_health_region")
    s = cfg["supply"]
    if s["input_mode"] not in ("available_appointments", "national_graduates", "student_intake"):
        raise ValueError("supply.input_mode is not a supported mode")
    path = s["annual_path"]
    vals = path if isinstance(path, list) else [path]
    if isinstance(path, list) and len(path) != n:
        raise ValueError("supply.annual_path as a list must have one value per allocation year")
    if any(float(v) < 0 for v in vals):
        raise ValueError("supply.annual_path must be non-negative")
    floor = int(a["universal_new_appointment_floor"])
    if s["input_mode"] == "available_appointments" and any(float(v) < 76 * floor for v in vals):
        warn.append(f"annual pool below 76 x floor ({76 * floor}): the universal floor is infeasible in at least one year")
    if float(cfg["targets"]["reference_per_1000"]) <= 0:
        raise ValueError("targets.reference_per_1000 must be positive")
    for lam in cfg["feedback"]["response_strengths"]:
        if float(lam) < 0:
            raise ValueError("feedback.response_strengths must be non-negative")
    return warn


def load(overrides: dict | None = None, name: str | None = None) -> Settings:
    cfg = copy.deepcopy(RAW)
    overrides = dict(overrides or {})
    for k, v in overrides.items():
        _set(cfg, k, v)
    validate(cfg)
    if overrides and (name in (None, "", "canonical")):
        name = "scenario_" + hashlib.sha256(json.dumps(overrides, sort_keys=True, default=str).encode()).hexdigest()[:8]
    return Settings(cfg=cfg, name=name or "canonical", overrides=overrides)


def parse_overrides(pairs: list[str] | None) -> dict:
    """['supply.annual_path=2500', 'allocation.cap_mode=net_growth'] -> dict (JSON values allowed)."""
    out = {}
    for s in pairs or []:
        k, _, v = s.partition("=")
        try:
            out[k.strip()] = json.loads(v)
        except json.JSONDecodeError:
            out[k.strip()] = v.strip()
    return out
