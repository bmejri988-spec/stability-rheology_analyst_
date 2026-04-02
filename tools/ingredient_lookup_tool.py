import json
from pathlib import Path
from typing import Any

import pandas as pd
from langchain.tools import tool


DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "COSING_Ingredients-Fragrance Inventory_v2.csv"
_DF_CACHE: pd.DataFrame | None = None


def _find_header_row(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for idx, line in enumerate(handle):
            if line.strip().startswith("COSING Ref No,INCI name"):
                return idx
    raise ValueError("Could not find COSING header row in dataset.")


def _load_dataset() -> pd.DataFrame:
    global _DF_CACHE
    if _DF_CACHE is not None:
        return _DF_CACHE

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    header_row = _find_header_row(DATASET_PATH)
    df = pd.read_csv(
        DATASET_PATH,
        skiprows=header_row,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
        encoding="utf-8",
    )

    # Normalize column names and key text columns.
    df.columns = [str(col).strip() for col in df.columns]
    for col in ["INCI name", "Chem/IUPAC Name / Description", "Function", "Restriction"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    _DF_CACHE = df
    return df


def _compute_rating(restriction: str, function: str) -> str:
    restriction_norm = restriction.upper().strip()
    function_norm = function.strip()

    if not restriction_norm and function_norm:
        return "generally_allowed"

    restricted_markers = ["CMR", "ANNEX", "II/", "III/", "IV/", "V/", "VI/"]
    if any(marker in restriction_norm for marker in restricted_markers):
        return "restricted"

    if restriction_norm:
        return "review_required"

    return "insufficient_data"


def ingredient_lookup(ingredient_name: str) -> dict[str, Any]:
    """Lookup an ingredient in the COSING dataset and return core formulation-relevant fields."""
    query = ingredient_name.strip()
    if not query:
        return {"error": "ingredient_name is required"}

    try:
        df = _load_dataset()
    except Exception as exc:
        return {"error": f"Failed to load ingredient dataset: {exc}"}

    if "INCI name" not in df.columns:
        return {"error": "Dataset schema missing 'INCI name' column"}

    query_norm = query.lower()
    exact = df[df["INCI name"].str.lower() == query_norm]
    if exact.empty:
        approx = df[df["INCI name"].str.lower().str.contains(query_norm, regex=False)]
    else:
        approx = exact

    if approx.empty:
        return {
            "ingredient": query,
            "found": False,
            "description": "Not found in COSING dataset",
            "function": "",
            "rating": "insufficient_data",
        }

    row = approx.iloc[0]
    description = str(row.get("Chem/IUPAC Name / Description", "")).strip()
    function = str(row.get("Function", "")).strip()
    restriction = str(row.get("Restriction", "")).strip()

    return {
        "ingredient": str(row.get("INCI name", query)).strip(),
        "found": True,
        "description": description,
        "function": function,
        "rating": _compute_rating(restriction=restriction, function=function),
        "restriction": restriction,
        "source": "COSING_Ingredients-Fragrance Inventory_v2.csv",
    }


@tool
def ingredient_lookup_tool(ingredient_name: str) -> str:
    """Lookup a cosmetic ingredient from COSING and return description, function, and safety/regulatory rating."""
    return json.dumps(ingredient_lookup(ingredient_name), ensure_ascii=True)
