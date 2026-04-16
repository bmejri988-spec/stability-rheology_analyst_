import json

from langchain.tools import tool

from tools.experimental_rheology_tool import experimental_rheology_tool
from tools.settling_analysis_tool import settling_analysis_tool


@tool
def experimental_bridge_tool(formula_json: str, top_k: int = 3) -> str:
    """
    Combine rheology and settling experimental evidence into a single cross-dataset view for formula stability assessment.
    Pass FORMULA_JSON as a string.
    """
    if not formula_json or not str(formula_json).strip():
        return json.dumps({"error": "formula_json is required"}, ensure_ascii=True)

    try:
        rheology_raw = experimental_rheology_tool.invoke({"formula_json": formula_json, "top_k": top_k})
    except Exception as exc:
        rheology_raw = json.dumps({"error": f"experimental_rheology_tool failed: {exc}"}, ensure_ascii=True)

    try:
        settling_raw = settling_analysis_tool.invoke({"formula_json": formula_json, "top_k": top_k})
    except Exception as exc:
        settling_raw = json.dumps({"error": f"settling_analysis_tool failed: {exc}"}, ensure_ascii=True)

    try:
        rheology = json.loads(rheology_raw)
    except Exception:
        rheology = {"raw": str(rheology_raw)}

    try:
        settling = json.loads(settling_raw)
    except Exception:
        settling = {"raw": str(settling_raw)}

    rheology_by_set = {
        item.get("set_name"): item
        for item in rheology.get("matches", [])
        if isinstance(item, dict) and item.get("set_name")
    }
    settling_by_set = {
        item.get("set_name"): item
        for item in settling.get("matches", [])
        if isinstance(item, dict) and item.get("set_name")
    }

    overlap = sorted(set(rheology_by_set.keys()) & set(settling_by_set.keys()))
    cross = []
    for set_name in overlap[: max(1, min(10, top_k))]:
        r = rheology_by_set[set_name]
        s = settling_by_set[set_name]
        cross.append(
            {
                "set_name": set_name,
                "nacl_pct": r.get("nacl_pct") if r.get("nacl_pct") is not None else s.get("nacl_pct"),
                "rheology": {
                    "match_score": r.get("match_score"),
                    "shear_thinning_index": r.get("shear_thinning_index"),
                    "tan_delta": r.get("tan_delta"),
                    "n1_max_pa": r.get("n1_max_pa"),
                },
                "settling": {
                    "match_score": s.get("match_score"),
                    "mean_velocity_pix_per_s": s.get("mean_velocity_pix_per_s"),
                    "std_velocity_pix_per_s": s.get("std_velocity_pix_per_s"),
                    "valid_velocity_runs": s.get("valid_velocity_runs"),
                },
            }
        )

    return json.dumps(
        {
            "rheology": rheology,
            "settling": settling,
            "cross_dataset_overlap": cross,
            "notes": [
                "Cross entries show experiment sets present in both rheology and settling corpora.",
                "Use this output to support empirical links between rheology profile and settling tendency.",
            ],
        },
        ensure_ascii=True,
    )
