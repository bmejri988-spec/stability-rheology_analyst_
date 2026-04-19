import time
import json
import requests
from typing import Any

from config import (
    FIRECRAWL_API_KEY,
    FIRECRAWL_MODEL,
    FIRECRAWL_TIMEOUT_SECONDS,
    FIRECRAWL_URL,
)

MAX_POLL_ATTEMPTS = 60
POLL_INTERVAL_SEC = 3


# -----------------------------
# SAFE JSON HANDLER
# -----------------------------
def _safe_json(response: requests.Response, context: str, job_id: str | None = None) -> dict[str, Any]:
    try:
        text = response.text.strip()

        if not text:
            return {"error": f"{context}: empty response", "job_id": job_id}

        try:
            return response.json()
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])

        return {
            "error": f"{context}: invalid JSON from Firecrawl",
            "job_id": job_id,
            "raw": text[:1500],
        }

    except Exception as e:
        return {"error": f"{context}: {str(e)}", "job_id": job_id}


def _coerce_json_value(raw_value: Any) -> dict[str, Any] | None:
    if isinstance(raw_value, dict):
        return raw_value

    if not isinstance(raw_value, str):
        return None

    text = raw_value.strip()
    if not text:
        return None

    fenced = text
    if fenced.startswith("```") and fenced.endswith("```"):
        fenced = fenced.split("\n", 1)[1] if "\n" in fenced else ""
        fenced = fenced.rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(fenced)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None

    return None


def _iter_payload_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def _add(candidate: Any) -> None:
        if isinstance(candidate, dict) and candidate not in candidates:
            candidates.append(candidate)

    _add(payload)

    for key in ("data", "result"):
        value = payload.get(key)
        _add(value)
        _add(_coerce_json_value(value))

    for candidate in list(candidates):
        for key in ("response", "output", "result", "data"):
            _add(_coerce_json_value(candidate.get(key)))

    return candidates


def _extract_safety_result(payload: dict[str, Any]) -> dict[str, Any]:
    for candidate in _iter_payload_candidates(payload):
        report = candidate.get("safety_report")
        if not isinstance(report, dict):
            report = candidate.get("report")
        if not isinstance(report, dict):
            report = candidate.get("structured_report")
        if not isinstance(report, dict):
            report = _coerce_json_value(report)

        summary = candidate.get("summary")
        if not isinstance(summary, str):
            summary = ""

        references = candidate.get("references")
        if not isinstance(references, list):
            references = []

        if report or summary or references:
            if not isinstance(report, dict):
                report = {}
            return {
                "safety_report": report,
                "summary": summary,
                "references": references,
            }

    return {"safety_report": {}, "summary": "", "references": []}


# -----------------------------
# STRICT PROMPT (FIXED)
# -----------------------------
def _build_safety_prompt(report: dict[str, Any], formula: dict[str, Any] | None) -> str:
    return f"""
You are a cosmetic environmental safety expert.

RETURN STRICT JSON ONLY (no extra keys, no nulls).

FORMAT:
{{
  "safety_report": {{
    "ingredient_origin_and_renewability": [],
    "biodegradability_and_ecotoxicity": [],
    "packaging_and_waste_impact": [],
    "process_and_energy_footprint": [],
    "safer_or_lower_impact_alternatives": [],
    "confidence_level": "low|medium|high",
    "references": []
  }},
  "summary": ""
}}

FORMULA:
{json.dumps(formula, indent=2)}

REPORT:
{json.dumps(report, indent=2)}
"""


# -----------------------------
# SCHEMA
# -----------------------------
def _safety_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "safety_report": {"type": "object"},
            "summary": {"type": "string"},
        },
    }


# -----------------------------
# BLOCKING FIRECRAWL EXECUTION
# -----------------------------
def _wait_for_completion(job_id: str, api_key: str, base_url: str) -> dict[str, Any]:
    base = base_url.rstrip("/")

    if base.endswith("/v2/agent"):
        url = f"{base}/{job_id}"
    else:
        url = f"{base}/v2/agent/{job_id}"

    last = None

    for _ in range(MAX_POLL_ATTEMPTS):
        try:
            res = requests.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
        except Exception as e:
            return {"error": f"Polling failed: {str(e)}", "job_id": job_id}

        payload = _safe_json(res, "polling", job_id)

        if "error" in payload and "invalid JSON" in payload.get("error", ""):
            return payload

        last = payload
        status = str(payload.get("status") or "").lower()

        if status == "completed":
            return payload

        if status in {"failed", "cancelled", "canceled"}:
            return {"error": "job failed", "job_id": job_id, "details": payload}

        time.sleep(POLL_INTERVAL_SEC)

    return {"error": "timeout", "job_id": job_id, "last": last}


# -----------------------------
# MAIN MCP TOOL FUNCTION
# -----------------------------
def process_safety_request(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if not FIRECRAWL_API_KEY:
        return {"error": "Missing FIRECRAWL_API_KEY"}, 500

    report = payload.get("report")
    formula = payload.get("formula")

    if not isinstance(report, dict):
        return {"error": "report must be object"}, 400

    body = {
        "prompt": _build_safety_prompt(report, formula),
        "urls": payload.get("urls", []),
        "schema": _safety_schema(),
        "strictConstrainToURLs": True,
        "maxCredits": 20,
        "model": FIRECRAWL_MODEL,
    }

    # -----------------------------
    # CREATE JOB
    # -----------------------------
    try:
        res = requests.post(
            FIRECRAWL_URL,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=FIRECRAWL_TIMEOUT_SECONDS,
        )
    except Exception as e:
        return {"error": str(e)}, 502

    init = _safe_json(res, "job creation")

    if "error" in init:
        return init, 502

    job_id = init.get("id")
    if not job_id:
        return {"error": "No job_id returned"}, 502

    # -----------------------------
    # BLOCKING EXECUTION
    # -----------------------------
    final = _wait_for_completion(job_id, FIRECRAWL_API_KEY, FIRECRAWL_URL)

    if "error" in final:
        return {
            "status": "failed",
            "job_id": job_id,
            "error": final["error"],
            "debug": final,
        }, 500

    data = final.get("data") or final
    extracted = _extract_safety_result(data if isinstance(data, dict) else final)

    return {
        "status": "completed",
        "job_id": job_id,
        "safety_report": extracted["safety_report"],
        "summary": extracted["summary"],
        "references": extracted["references"],
    }, 200