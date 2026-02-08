from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

# ---------------------------
# Helpers
# ---------------------------

def _fail(msg: str) -> None:
    print(f"❌ {msg}")
    raise SystemExit(1)

def _warn(msg: str, strict: bool) -> None:
    if strict:
        _fail(msg)
    print(f"⚠️  {msg}")

def _pick_existing(data_dir: Path, candidates: Iterable[str]) -> Path | None:
    for name in candidates:
        p = data_dir / name
        if p.exists():
            return p
    return None

def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception as e:
        _fail(f"Failed to read {path.as_posix()}: {e}")
    raise AssertionError

def _require_cols(df: pd.DataFrame, required: Iterable[str], table: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        _fail(f"{table}: missing required columns: {missing}")

def _assert_regex(series: pd.Series, pattern: str, name: str, strict: bool) -> None:
    s = series.dropna().astype(str)
    bad = s[~s.str.match(pattern)]
    if len(bad) > 0:
        sample = bad.head(5).tolist()
        _warn(
            f"{name}: {len(bad)} values do not match regex {pattern}. Sample: {sample}",
            strict,
        )

def _assert_range(series: pd.Series, lo: float, hi: float, name: str, strict: bool) -> None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    bad = s[(s < lo) | (s > hi)]
    if len(bad) > 0:
        sample = bad.head(5).tolist()
        _warn(
            f"{name}: {len(bad)} values out of range [{lo}, {hi}]. Sample: {sample}",
            strict,
        )

def _assert_nonneg(series: pd.Series, name: str, strict: bool) -> None:
    s = pd.to_numeric(series, errors="coerce")
    bad = s[s < 0]
    if len(bad) > 0:
        _warn(f"{name}: {len(bad)} values are negative. Sample: {bad.head(5).tolist()}", strict)

def _assert_unique(series: pd.Series, name: str, strict: bool) -> None:
    s = series.dropna()
    dups = s[s.duplicated()]
    if len(dups) > 0:
        sample = dups.head(5).tolist()
        _warn(
            f"{name}: {len(dups)} duplicate IDs detected. Sample: {sample}",
            strict,
        )

def _bool_like(series: pd.Series) -> pd.Series:
    # Accept common representations
    if series.dtype == "bool":
        return series
    s = series.astype(str).str.strip().str.lower()
    mapping = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
    return s.map(mapping)

# ---------------------------
# Main validation
# ---------------------------

def validate(data_dir: Path, strict: bool) -> None:
    data_dir = data_dir.resolve()
    if not data_dir.exists():
        _fail(f"--data-dir does not exist: {data_dir}")

    stations_path = _pick_existing(
        data_dir,
        [
            "charging_stations_world.csv",
            "charging_station.csv",
            "charging_stations.csv",
        ],
    )
    if stations_path is None:
        expected = [
            "charging_stations_world.csv",
            "charging_station.csv",
            "charging_stations.csv",
        ]
        _fail(
            "Could not find main stations file. Expected one of: "
            + ", ".join(expected)
        )

    # Main stations file
    stations = _read_csv(stations_path)
    required = [
        "id",
        "name",
        "city",
        "country_code",
        "state_province",
        "latitude",
        "longitude",
        "ports",
        "power_kw",
        "power_class",
        "is_fast_dc",
    ]
    _require_cols(stations, required, stations_path.name)

    _assert_unique(stations["id"], f"{stations_path.name}.id", strict)
    _assert_regex(
        stations["country_code"],
        r"^[A-Z]{2}$",
        f"{stations_path.name}.country_code",
        strict,
    )
    _assert_range(stations["latitude"], -90, 90, f"{stations_path.name}.latitude", strict)
    _assert_range(stations["longitude"], -180, 180, f"{stations_path.name}.longitude", strict)
    _assert_nonneg(stations["ports"], f"{stations_path.name}.ports", strict)
    _assert_nonneg(stations["power_kw"], f"{stations_path.name}.power_kw", strict)

    # power_class sanity
    pc = stations["power_class"].astype(str).str.strip().str.lower()
    allowed = {"slow", "fast", "hpc"}
    bad_pc = pc[~pc.isin(allowed)]
    if len(bad_pc) > 0:
        allowed_sorted = sorted(allowed)
        sample = bad_pc.head(5).tolist()
        msg = (
            f"{stations_path.name}.power_class: {len(bad_pc)} values not in {allowed_sorted}. "
            f"Sample: {sample}"
        )
        _warn(msg, strict)

    # Optional companion files
    country_path = _pick_existing(data_dir, ["country_summary.csv"])
    if country_path is not None:
        country = _read_csv(country_path)
        if "country_code" in country.columns:
            # count columns can be stations or count
            if "stations" in country.columns:
                count_col = "stations"
            elif "count" in country.columns:
                count_col = "count"
            else:
                count_col = None
            if count_col is None:
                _warn(
                    f"{country_path.name}: expected a count column named 'stations' or 'count'",
                    strict,
                )
            else:
                computed = stations.groupby("country_code")["id"].size().rename("computed")
                merged = country.set_index("country_code")[[count_col]].join(computed, how="left")
                merged["computed"] = merged["computed"].fillna(0).astype(int)
                diff = (merged[count_col].astype(int) - merged["computed"]).abs()
                bad = diff[diff > 0]
                if len(bad) > 0:
                    sample = bad.head(5).to_dict(orient="records")
                    msg = (
                        f"{country_path.name}: {len(bad)} countries differ "
                        f"from computed station counts. Sample: {sample}"
                    )
                    _warn(msg, strict)
