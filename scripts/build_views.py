from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _pick_existing(data_dir: Path, candidates: list[str]) -> Path:
    for name in candidates:
        p = data_dir / name
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not find main stations file. Expected one of: "
        + ", ".join(candidates)
    )


def build_views(data_dir: Path, out_dir: Path) -> None:
    data_dir = data_dir.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    stations_path = _pick_existing(
        data_dir,
        ["charging_stations_world.csv", "charging_station.csv", "charging_stations.csv"],
    )
    df = pd.read_csv(stations_path)

    # Country summary
    country = (
        df.groupby("country_code")["id"]
        .size()
        .rename("stations")
        .reset_index()
        .sort_values(["stations", "country_code"], ascending=[False, True])
    )
    country_out = out_dir / "country_summary.csv"
    country.to_csv(country_out, index=False)

    # World summary (single row)
    power = pd.to_numeric(df.get("power_kw"), errors="coerce")
    ports = pd.to_numeric(df.get("ports"), errors="coerce")
    is_fast = df.get("is_fast_dc")
    if is_fast is not None:
        is_fast = is_fast.astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        is_fast = power.ge(50)

    world = pd.DataFrame(
        [
            {
                "countries": int(df["country_code"].nunique()),
                "stations": int(len(df)),
                "ports_sum": float(ports.fillna(0).sum()),
                "power_kw_max": float(power.max(skipna=True)) if power.notna().any() else None,
                "fast_dc_share": float(is_fast.mean()) if len(df) else None,
            }
        ]
    )
    world_out = out_dir / "world_summary.csv"
    world.to_csv(world_out, index=False)

    # ML-ready (compact subset)
    keep = [
        "id",
        "country_code",
        "latitude",
        "longitude",
        "ports",
        "power_kw",
        "is_fast_dc",
    ]
    keep = [c for c in keep if c in df.columns]
    ml = df[keep].copy()
    ml_out = out_dir / "charging_station_ml.csv"
    ml.to_csv(ml_out, index=False)

    print("✅ Wrote:")
    print(f"  - {country_out.relative_to(Path.cwd()) if country_out.exists() else country_out}")
    print(f"  - {world_out.relative_to(Path.cwd()) if world_out.exists() else world_out}")
    print(f"  - {ml_out.relative_to(Path.cwd()) if ml_out.exists() else ml_out}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build derived views from Global EV Infra dataset."
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing raw CSV files.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("generated"),
        help="Output directory for generated CSV files.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    build_views(args.data_dir, args.out_dir)


if __name__ == "__main__":
    main()
