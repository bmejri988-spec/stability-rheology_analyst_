import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from langchain.tools import tool


RHEOLOGY_ROOT = Path(__file__).resolve().parents[1] / "data" / "experimental_data" / "Rheological_data"
_RHEOLOGY_CACHE: list[dict[str, Any]] | None = None


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


def _read_two_header_csv(csv_path: Path) -> pd.DataFrame:
    raw = pd.read_csv(
        csv_path,
        header=None,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
        on_bad_lines="skip",
    )

    if raw.shape[0] < 3:
        raise ValueError(f"Unexpected format for {csv_path.name}: requires at least 3 rows")

    headers = [str(v).strip() for v in raw.iloc[1].tolist()]
    data = raw.iloc[2:].copy().reset_index(drop=True)
    data.columns = headers

    # Drop empty columns that can appear because of trailing delimiters.
    data = data.loc[:, [c for c in data.columns if str(c).strip() and not str(c).lower().startswith("unnamed")]]

    for col in data.columns:
        data[col] = data[col].map(_safe_float)

    data = data.dropna(how="all")
    return data


def _extract_nacl_pct(set_name: str) -> float | None:
    match = re.search(r"NaCl_([0-9]+(?:\.[0-9]+)?)", set_name, flags=re.IGNORECASE)
    if not match:
        return None
    return _safe_float(match.group(1))


def _log_slope(x: pd.Series, y: pd.Series) -> float | None:
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    valid = valid[(valid["x"] > 0) & (valid["y"] > 0)]
    if valid.shape[0] < 3:
        return None

    lx = np.log10(valid["x"].to_numpy())
    ly = np.log10(valid["y"].to_numpy())
    slope, _ = np.polyfit(lx, ly, deg=1)
    return float(slope)


def _summarize_set(set_dir: Path) -> dict[str, Any]:
    flow = _read_two_header_csv(set_dir / "flow_data.csv")
    ampl = _read_two_header_csv(set_dir / "ampl_sweeps.csv")
    freq = _read_two_header_csv(set_dir / "freq_sweeps.csv")
    normal = _read_two_header_csv(set_dir / "normal_stress.csv")

    flow_shear_col = next((c for c in flow.columns if "shear rate" in c.lower()), None)
    flow_visc_col = next((c for c in flow.columns if "viscosity" in c.lower()), None)

    low_visc = None
    high_visc = None
    shear_thinning_index = None

    if flow_shear_col and flow_visc_col:
        work = flow[[flow_shear_col, flow_visc_col]].dropna()
        low_band = work[work[flow_shear_col] <= 0.1][flow_visc_col]
        high_band = work[work[flow_shear_col] >= 10.0][flow_visc_col]

        if low_band.empty:
            low_band = work.nsmallest(max(1, min(5, len(work))), flow_shear_col)[flow_visc_col]
        if high_band.empty:
            high_band = work.nlargest(max(1, min(5, len(work))), flow_shear_col)[flow_visc_col]

        low_visc = _safe_float(low_band.median())
        high_visc = _safe_float(high_band.median())

        if low_visc and high_visc and high_visc > 0:
            shear_thinning_index = float(low_visc / high_visc)

    gp_col = next((c for c in ampl.columns if "storage modulus" in c.lower()), None)
    gpp_col = next((c for c in ampl.columns if "loss modulus" in c.lower()), None)
    gp_median = _safe_float(ampl[gp_col].median()) if gp_col else None
    gpp_median = _safe_float(ampl[gpp_col].median()) if gpp_col else None

    tan_delta = None
    if gp_median and gpp_median and gp_median > 0:
        tan_delta = float(gpp_median / gp_median)

    freq_x_col = next((c for c in freq.columns if "frequency" in c.lower()), None)
    freq_gp_col = next((c for c in freq.columns if "storage modulus" in c.lower()), None)
    freq_gpp_col = next((c for c in freq.columns if "loss modulus" in c.lower()), None)

    gp_freq_slope = _log_slope(freq[freq_x_col], freq[freq_gp_col]) if freq_x_col and freq_gp_col else None
    gpp_freq_slope = _log_slope(freq[freq_x_col], freq[freq_gpp_col]) if freq_x_col and freq_gpp_col else None

    normal_n1_col = next((c for c in normal.columns if "norm" in c.lower() and "diff" in c.lower()), None)
    n1_max = _safe_float(normal[normal_n1_col].max()) if normal_n1_col else None

    return {
        "set_name": set_dir.name,
        "nacl_pct": _extract_nacl_pct(set_dir.name),
        "flow_points": int(flow.shape[0]),
        "low_shear_viscosity_pa_s": low_visc,
        "high_shear_viscosity_pa_s": high_visc,
        "shear_thinning_index": shear_thinning_index,
        "gp_median_pa": gp_median,
        "gpp_median_pa": gpp_median,
        "tan_delta": tan_delta,
        "gp_freq_slope": gp_freq_slope,
        "gpp_freq_slope": gpp_freq_slope,
        "n1_max_pa": n1_max,
    }


def _load_summaries() -> list[dict[str, Any]]:
    global _RHEOLOGY_CACHE
    if _RHEOLOGY_CACHE is not None:
        return _RHEOLOGY_CACHE

    if not RHEOLOGY_ROOT.exists():
        raise FileNotFoundError(f"Rheology dataset root not found: {RHEOLOGY_ROOT}")

    summaries: list[dict[str, Any]] = []
    for set_dir in sorted(p for p in RHEOLOGY_ROOT.iterdir() if p.is_dir()):
        required = [
            set_dir / "flow_data.csv",
            set_dir / "ampl_sweeps.csv",
            set_dir / "freq_sweeps.csv",
            set_dir / "normal_stress.csv",
        ]
        if not all(p.exists() for p in required):
            continue

        try:
            summaries.append(_summarize_set(set_dir))
        except Exception:
            continue

    _RHEOLOGY_CACHE = summaries
    return summaries


def _extract_formula_signal(formula_json: str) -> dict[str, float | None]:
    try:
        payload = json.loads(formula_json)
    except Exception:
        return {"nacl_pct": None, "xanthan_pct": None}

    ingredients = payload.get("ingredients", [])
    if not isinstance(ingredients, list):
        return {"nacl_pct": None, "xanthan_pct": None}

    nacl_pct = 0.0
    xanthan_pct = 0.0
    nacl_seen = False
    xanthan_seen = False

    for ing in ingredients:
        if not isinstance(ing, dict):
            continue

        name = str(ing.get("inci_name", "")).strip().lower()
        wt = _safe_float(ing.get("wt_pct"))
        if wt is None:
            continue

        if "sodium chloride" in name or name == "nacl":
            nacl_seen = True
            nacl_pct += wt

        if "xanthan" in name:
            xanthan_seen = True
            xanthan_pct += wt

    return {
        "nacl_pct": nacl_pct if nacl_seen else None,
        "xanthan_pct": xanthan_pct if xanthan_seen else None,
    }


def _rank_matches(summaries: list[dict[str, Any]], target_nacl: float | None, top_k: int) -> list[dict[str, Any]]:
    ranked = []

    for item in summaries:
        set_nacl = item.get("nacl_pct")
        if target_nacl is not None and set_nacl is not None:
            score = 1.0 / (1.0 + abs(target_nacl - set_nacl))
        else:
            score = 0.4

        ranked.append((score, item))

    ranked.sort(key=lambda x: x[0], reverse=True)

    output = []
    for score, item in ranked[: max(1, min(10, top_k))]:
        enriched = dict(item)
        enriched["match_score"] = round(float(score), 4)
        output.append(enriched)

    return output


@tool
def experimental_rheology_tool(formula_json: str, top_k: int = 3) -> str:
    """
    Match formula composition to experimental rheology datasets and return empirical rheology metrics.
    Pass FORMULA_JSON as a string; tool extracts sodium chloride and xanthan gum signals for matching.
    """
    if not formula_json or not str(formula_json).strip():
        return json.dumps({"error": "formula_json is required"}, ensure_ascii=True)

    try:
        summaries = _load_summaries()
    except Exception as exc:
        return json.dumps({"error": f"Failed to load rheology datasets: {exc}"}, ensure_ascii=True)

    if not summaries:
        return json.dumps({"error": "No rheology experiment sets were parsed successfully."}, ensure_ascii=True)

    features = _extract_formula_signal(formula_json)
    ranked = _rank_matches(summaries, features.get("nacl_pct"), top_k=top_k)

    result = {
        "formula_features": features,
        "dataset_root": str(RHEOLOGY_ROOT),
        "matches": ranked,
        "notes": [
            "Matches are ranked mainly by NaCl concentration proximity when available.",
            "Use shear_thinning_index, tan_delta, and n1_max_pa as empirical rheology indicators.",
        ],
    }
    return json.dumps(result, ensure_ascii=True)
