import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from langchain.tools import tool


SETTLING_ROOT = Path(__file__).resolve().parents[1] / "data" / "experimental_data" / "Settling_experiments"
_SETTLING_CACHE: list[dict[str, Any]] | None = None


def _safe_float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        number = float(text)
        if np.isnan(number) or np.isinf(number):
            return None
        return number
    except Exception:
        return None


def _extract_nacl_pct(set_name: str) -> float | None:
    match = re.search(r"NaCl_([0-9]+(?:\.[0-9]+)?)", set_name, flags=re.IGNORECASE)
    if not match:
        return None
    return _safe_float(match.group(1))


def _read_conditions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.lower().startswith("unnamed")]]
    return df


def _parse_particle_token(file_name: str, set_name: str) -> str:
    # Example: NaCl_0.1_XG_D1.5_run_1.csv -> D1.5
    prefix = f"{set_name}_"
    suffix = ".csv"
    if file_name.startswith(prefix) and file_name.endswith(suffix):
        core = file_name[len(prefix) : -len(suffix)]
        token = core.split("_run_")[0]
        return token
    return "unknown"


def _run_velocity_stats(run_csv: Path) -> dict[str, float | None]:
    df = pd.read_csv(run_csv, dtype=str, keep_default_na=False, encoding="utf-8")
    df.columns = [str(c).strip().strip('"') for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.lower().startswith("unnamed")]]

    # Known columns are x, z, t; keep fallback for slight naming differences.
    z_col = next((c for c in df.columns if c.lower() == "z"), None)
    t_col = next((c for c in df.columns if c.lower() in {"t", "time", "t[s]"}), None)

    if not z_col or not t_col:
        return {"velocity_pix_per_s": None, "delta_z_pix": None, "delta_t_s": None}

    z = df[z_col].map(_safe_float).dropna()
    t = df[t_col].map(_safe_float).dropna()

    if z.shape[0] < 2 or t.shape[0] < 2:
        return {"velocity_pix_per_s": None, "delta_z_pix": None, "delta_t_s": None}

    n = min(z.shape[0], t.shape[0])
    dz = float(z.iloc[n - 1] - z.iloc[0])
    dt = float(t.iloc[n - 1] - t.iloc[0])

    if dt <= 0:
        return {"velocity_pix_per_s": None, "delta_z_pix": dz, "delta_t_s": dt}

    return {
        "velocity_pix_per_s": float(dz / dt),
        "delta_z_pix": dz,
        "delta_t_s": dt,
    }


def _summarize_set(set_dir: Path) -> dict[str, Any]:
    set_name = set_dir.name
    conditions_file = set_dir / f"{set_name}_conditions.csv"

    if not conditions_file.exists():
        raise FileNotFoundError(f"Missing conditions file for {set_name}")

    conditions = _read_conditions(conditions_file)
    fps_col = next((c for c in conditions.columns if "frame_rate" in c.lower()), None)

    fps_values = conditions[fps_col].map(_safe_float).dropna() if fps_col else pd.Series(dtype=float)
    fps_median = _safe_float(fps_values.median()) if not fps_values.empty else None

    run_files = sorted(
        p
        for p in set_dir.glob("*.csv")
        if p.name.lower() != f"{set_name.lower()}_conditions.csv"
    )

    velocities = []
    by_particle: dict[str, list[float]] = {}

    for run_file in run_files:
        stats = _run_velocity_stats(run_file)
        velocity = stats.get("velocity_pix_per_s")
        if velocity is None:
            continue

        velocities.append(float(velocity))
        particle = _parse_particle_token(run_file.name, set_name)
        by_particle.setdefault(particle, []).append(float(velocity))

    particle_summary = {}
    for particle, values in by_particle.items():
        arr = np.array(values, dtype=float)
        particle_summary[particle] = {
            "mean_velocity_pix_per_s": float(arr.mean()),
            "std_velocity_pix_per_s": float(arr.std(ddof=0)),
            "runs": int(arr.shape[0]),
        }

    if velocities:
        arr = np.array(velocities, dtype=float)
        mean_velocity = float(arr.mean())
        std_velocity = float(arr.std(ddof=0))
    else:
        mean_velocity = None
        std_velocity = None

    return {
        "set_name": set_name,
        "nacl_pct": _extract_nacl_pct(set_name),
        "conditions_rows": int(conditions.shape[0]),
        "fps_median": fps_median,
        "run_count": int(len(run_files)),
        "valid_velocity_runs": int(len(velocities)),
        "mean_velocity_pix_per_s": mean_velocity,
        "std_velocity_pix_per_s": std_velocity,
        "particle_velocity_summary": particle_summary,
    }


def _load_summaries() -> list[dict[str, Any]]:
    global _SETTLING_CACHE
    if _SETTLING_CACHE is not None:
        return _SETTLING_CACHE

    if not SETTLING_ROOT.exists():
        raise FileNotFoundError(f"Settling dataset root not found: {SETTLING_ROOT}")

    summaries: list[dict[str, Any]] = []
    for set_dir in sorted(p for p in SETTLING_ROOT.iterdir() if p.is_dir()):
        try:
            summaries.append(_summarize_set(set_dir))
        except Exception:
            continue

    _SETTLING_CACHE = summaries
    return summaries


def _extract_formula_nacl(formula_json: str) -> float | None:
    try:
        payload = json.loads(formula_json)
    except Exception:
        return None

    ingredients = payload.get("ingredients", [])
    if not isinstance(ingredients, list):
        return None

    nacl_pct = 0.0
    seen = False
    for ing in ingredients:
        if not isinstance(ing, dict):
            continue

        name = str(ing.get("inci_name", "")).strip().lower()
        wt = _safe_float(ing.get("wt_pct"))
        if wt is None:
            continue

        if "sodium chloride" in name or name == "nacl":
            nacl_pct += wt
            seen = True

    return nacl_pct if seen else None


def _rank_matches(summaries: list[dict[str, Any]], target_nacl: float | None, top_k: int) -> list[dict[str, Any]]:
    ranked = []

    for item in summaries:
        set_nacl = item.get("nacl_pct")
        velocity = item.get("mean_velocity_pix_per_s")
        velocity_penalty = 0.0 if velocity is None else min(0.25, abs(float(velocity)) / 150.0)

        if target_nacl is not None and set_nacl is not None:
            score = (1.0 / (1.0 + abs(target_nacl - set_nacl))) - velocity_penalty
        else:
            score = 0.4 - velocity_penalty

        ranked.append((score, item))

    ranked.sort(key=lambda x: x[0], reverse=True)

    output = []
    for score, item in ranked[: max(1, min(10, top_k))]:
        enriched = dict(item)
        enriched["match_score"] = round(float(score), 4)
        output.append(enriched)

    return output


@tool
def settling_analysis_tool(formula_json: str, top_k: int = 3) -> str:
    """
    Match formula composition to settling experiment datasets and return trajectory-derived settling summaries.
    Pass FORMULA_JSON as a string; tool extracts sodium chloride signal for matching.
    """
    if not formula_json or not str(formula_json).strip():
        return json.dumps({"error": "formula_json is required"}, ensure_ascii=True)

    try:
        summaries = _load_summaries()
    except Exception as exc:
        return json.dumps({"error": f"Failed to load settling datasets: {exc}"}, ensure_ascii=True)

    if not summaries:
        return json.dumps({"error": "No settling experiment sets were parsed successfully."}, ensure_ascii=True)

    nacl_pct = _extract_formula_nacl(formula_json)
    ranked = _rank_matches(summaries, target_nacl=nacl_pct, top_k=top_k)

    result = {
        "formula_features": {"nacl_pct": nacl_pct},
        "dataset_root": str(SETTLING_ROOT),
        "matches": ranked,
        "notes": [
            "mean_velocity_pix_per_s is a trajectory-derived settling proxy (z displacement over time).",
            "Lower absolute settling velocity can indicate better resistance to rapid settling for tested particles.",
        ],
    }
    return json.dumps(result, ensure_ascii=True)
