import json
import time
from typing import Any
from urllib.parse import urlparse

import requests

from config import FIRECRAWL_API_KEY, FIRECRAWL_MODEL, FIRECRAWL_TIMEOUT_SECONDS, FIRECRAWL_URL


def _coerce_json_dict(raw_output: Any) -> dict[str, Any] | None:
    if isinstance(raw_output, dict):
        return raw_output

    if not isinstance(raw_output, str):
        return None

    text = raw_output.strip()
    if not text:
        return None

    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    try:
        parsed = json.loads(text)
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


def _extract_reference_urls(report: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    references = report.get("references", []) if isinstance(report.get("references"), list) else []
    for item in references:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if url.startswith("http://") or url.startswith("https://"):
            if url not in urls:
                urls.append(url)
    return urls


def _extract_safety_reference_urls(safety_report: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    references = safety_report.get("references", []) if isinstance(safety_report.get("references"), list) else []
    for item in references:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if url.startswith("http://") or url.startswith("https://"):
            if url not in urls:
                urls.append(url)
    return urls


def _collect_crawl_reference_urls(primary: dict[str, Any], fallback: dict[str, Any] | None = None) -> list[str]:
    urls = _extract_safety_reference_urls(primary)
    if urls:
        return urls

    if isinstance(fallback, dict):
        return _extract_safety_reference_urls(fallback)

    return []


def _formula_snapshot(formula: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(formula, dict):
        return {}

    return {
        "product_name": formula.get("product_name"),
        "product_type": formula.get("product_type"),
        "target_ph": formula.get("target_ph"),
        "assessment_goal": formula.get("assessment_goal"),
        "ingredients": formula.get("ingredients") if isinstance(formula.get("ingredients"), list) else [],
        "process_conditions": formula.get("process_conditions") if isinstance(formula.get("process_conditions"), dict) else {},
        "packaging": formula.get("packaging") if isinstance(formula.get("packaging"), dict) else {},
        "storage_conditions": formula.get("storage_conditions") if isinstance(formula.get("storage_conditions"), list) else [],
    }


def _safety_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "safety_report": {
                "type": "object",
                "properties": {
                    "ingredient_origin_and_renewability": {"type": "array", "items": {"type": "string"}},
                    "biodegradability_and_ecotoxicity": {"type": "array", "items": {"type": "string"}},
                    "packaging_and_waste_impact": {"type": "array", "items": {"type": "string"}},
                    "process_and_energy_footprint": {"type": "array", "items": {"type": "string"}},
                    "safer_or_lower_impact_alternatives": {"type": "array", "items": {"type": "string"}},
                    "confidence_level": {"type": "string"},
                    "references": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                                "relevance": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "summary": {"type": "string"},
        },
    }


def _simple_main_report(report: dict[str, Any]) -> dict[str, Any]:
    exec_sum = report.get("executive_summary", {}) if isinstance(report.get("executive_summary"), dict) else {}
    risks = report.get("stability_risk_assessment", {}) if isinstance(report.get("stability_risk_assessment"), dict) else {}
    packaging = report.get("packaging_compatibility", {}) if isinstance(report.get("packaging_compatibility"), dict) else {}

    return {
        "executive_summary": {
            "risk_level": exec_sum.get("risk_level"),
            "confidence_level": exec_sum.get("confidence_level"),
            "launch_decision": exec_sum.get("launch_decision"),
        },
        "main_risk_drivers": {
            "ph_sensitivity": risks.get("ph_sensitivity", []),
            "thermal_sensitivity": risks.get("thermal_sensitivity", []),
            "electrolyte_sensitivity": risks.get("electrolyte_sensitivity", []),
        },
        "packaging_notes": {
            "material_compatibility": packaging.get("material_compatibility", []),
            "oxygen_water_barrier": packaging.get("oxygen_water_barrier", []),
        },
    }


def _build_safety_prompt(report: dict[str, Any], formula: dict[str, Any] | None) -> str:
    return (
        "You are a cosmetic sustainability and environmental safety assessor.\n"
        "Task: Produce one safety report aligned to sustainable development for formulation teams.\n"
        "Base the analysis on the current formula and the current rheology/stability report below.\n"
        "Tie each claim back to the specific formula ingredients, process, packaging, and the report's main risk signals.\n"
        "Use only sources retrieved by the crawl agent for the safety references; do not reuse the main report references unless the crawl agent independently cites them.\n"
        "Keep claims conservative and evidence-based. If uncertain, say so clearly.\n"
        "Do not provide medical advice.\n\n"
        "Return JSON matching this exact safety schema fields: ingredient_origin_and_renewability, "
        "biodegradability_and_ecotoxicity, packaging_and_waste_impact, process_and_energy_footprint, "
        "safer_or_lower_impact_alternatives, confidence_level, references, summary.\n\n"
        "CURRENT_FORMULA_JSON:\n"
        + json.dumps(_formula_snapshot(formula), ensure_ascii=True)
        + "\n\nCURRENT_SIMPLE_MAIN_REPORT:\n"
        + json.dumps(_simple_main_report(report), ensure_ascii=True)
        + "\n\nCURRENT_FULL_REPORT_JSON:\n"
        + json.dumps(report, ensure_ascii=True)
    )


def _extract_firecrawl_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        for key in ("data", "result", "output", "response"):
            value = raw.get(key)
            if isinstance(value, dict):
                return value
            parsed = _coerce_json_dict(value)
            if parsed is not None:
                return parsed
        return raw

    parsed = _coerce_json_dict(raw)
    return parsed or {}


def _extract_firecrawl_message(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""

    for key in ("message", "error", "reason", "details", "warning"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    nested = payload.get("data")
    if isinstance(nested, dict):
        message = _extract_firecrawl_message(nested)
        if message:
            return message

    return ""


def _build_firecrawl_status_url(job_id: str) -> str:
    base = (FIRECRAWL_URL or "https://api.firecrawl.dev/v2/agent").rstrip("/")
    if base.endswith("/v2/agent"):
        return f"{base}/{job_id}"
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "https://api.firecrawl.dev"
    return f"{root}/v2/agent/{job_id}"


def _fetch_firecrawl_agent_status(job_id: str) -> tuple[dict[str, Any] | None, str, str]:
    status_url = _build_firecrawl_status_url(job_id)
    try:
        poll_res = requests.get(
            status_url,
            headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
            timeout=min(12, FIRECRAWL_TIMEOUT_SECONDS),
        )
    except Exception:
        return None, "request_error", status_url

    if poll_res.status_code >= 400:
        return None, f"http_{poll_res.status_code}", status_url

    try:
        payload = poll_res.json()
    except Exception:
        return None, "invalid_json", status_url

    status = str(payload.get("status") or "unknown").lower()
    return payload, status, status_url


def process_safety_request(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if not FIRECRAWL_API_KEY:
        return {"error": "Missing FIRECRAWL_API_KEY/firecrawl_api_key in environment."}, 500

    requested_job_id = str(payload.get("jobId") or "").strip()
    formula = payload.get("formula") if isinstance(payload.get("formula"), dict) else None

    if requested_job_id:
        print(f"[safety] polling firecrawl job: {requested_job_id}")
        started_at = time.perf_counter()
        fetched_payload, firecrawl_status, firecrawl_status_url = _fetch_firecrawl_agent_status(requested_job_id)
        print(f"[safety] polled status: {firecrawl_status} (job={requested_job_id})")

        if fetched_payload is None:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            return {
                "safety_report": {},
                "summary": "",
                "provider": "firecrawl",
                "duration_ms": duration_ms,
                "used_urls": [],
                "firecrawl_status": firecrawl_status,
                "firecrawl_job_id": requested_job_id,
                "firecrawl_status_url": firecrawl_status_url,
                "firecrawl_verbose": {"status": firecrawl_status, "job_id": requested_job_id},
                "firecrawl_message": "Could not fetch Firecrawl status payload.",
                "warning": "Safety status check failed.",
            }, 200

        if firecrawl_status != "completed":
            warning = "Safety job still running."
            if firecrawl_status in {"failed", "cancelled", "canceled"}:
                warning = "Safety job failed or was cancelled."
            elif firecrawl_status in {"request_error", "invalid_json"}:
                warning = "Safety status check returned an invalid response."

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            return {
                "safety_report": {},
                "summary": "",
                "provider": "firecrawl",
                "duration_ms": duration_ms,
                "used_urls": [],
                "firecrawl_status": firecrawl_status,
                "firecrawl_job_id": requested_job_id,
                "firecrawl_status_url": firecrawl_status_url,
                "firecrawl_verbose": fetched_payload,
                "firecrawl_message": _extract_firecrawl_message(fetched_payload),
                "warning": warning,
            }, 200

        extracted = _extract_firecrawl_payload(fetched_payload)
        safety_report = extracted.get("safety_report") if isinstance(extracted.get("safety_report"), dict) else extracted
        if not isinstance(safety_report, dict):
            safety_report = {}
        used_urls = _collect_crawl_reference_urls(safety_report, extracted)

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[safety] firecrawl job completed: {requested_job_id}")
        return {
            "safety_report": safety_report,
            "summary": str(extracted.get("summary") or "").strip(),
            "provider": "firecrawl",
            "duration_ms": duration_ms,
            "used_urls": used_urls,
            "firecrawl_status": firecrawl_status,
            "firecrawl_job_id": requested_job_id,
            "firecrawl_status_url": firecrawl_status_url,
            "firecrawl_verbose": fetched_payload,
            "firecrawl_message": _extract_firecrawl_message(fetched_payload),
        }, 200

    report = payload.get("report")
    if not isinstance(report, dict):
        return {"error": "Field 'report' must be an object when jobId is not provided."}, 400

    urls = payload.get("urls", [])
    if not isinstance(urls, list):
        urls = []
    urls = [str(u).strip() for u in urls if str(u).strip()]
    if not urls:
        urls = _extract_reference_urls(report)

    max_credits = payload.get("maxCredits", 80)
    strict_to_urls = bool(payload.get("strictConstrainToURLs", False))
    model = str(payload.get("model") or FIRECRAWL_MODEL)

    request_body: dict[str, Any] = {
        "prompt": _build_safety_prompt(report, formula),
        "urls": urls,
        "schema": _safety_schema(),
        "maxCredits": max_credits,
        "strictConstrainToURLs": strict_to_urls,
        "model": model,
    }

    started_at = time.perf_counter()
    print(f"[safety] starting firecrawl job with {len(urls)} url(s), strict={strict_to_urls}, model={model}")
    try:
        response = requests.post(
            FIRECRAWL_URL,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=FIRECRAWL_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        return {"error": f"Safety agent request failed: {exc}"}, 502

    if response.status_code >= 400:
        return {
            "error": "Safety agent returned an error.",
            "status_code": response.status_code,
            "details": response.text[:1200],
        }, 502

    try:
        raw_result = response.json()
    except Exception:
        raw_result = {"raw": response.text}

    firecrawl_job_id = str(raw_result.get("id") or "") if isinstance(raw_result, dict) else ""
    firecrawl_status = str(raw_result.get("status") or "processing").lower() if isinstance(raw_result, dict) else "processing"
    firecrawl_status_url = _build_firecrawl_status_url(firecrawl_job_id) if firecrawl_job_id else ""

    if isinstance(raw_result, dict) and isinstance(raw_result.get("data"), dict):
        extracted = _extract_firecrawl_payload(raw_result)
        safety_report = extracted.get("safety_report") if isinstance(extracted.get("safety_report"), dict) else extracted
        if not isinstance(safety_report, dict):
            safety_report = {}
        used_urls = _collect_crawl_reference_urls(safety_report, extracted)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[safety] firecrawl completed inline (job_id={firecrawl_job_id or 'n/a'})")
        return {
            "safety_report": safety_report,
            "summary": str(extracted.get("summary") or "").strip(),
            "provider": "firecrawl",
            "duration_ms": duration_ms,
            "used_urls": used_urls,
            "firecrawl_status": "completed",
            "firecrawl_job_id": firecrawl_job_id,
            "firecrawl_status_url": firecrawl_status_url,
            "firecrawl_verbose": raw_result,
            "firecrawl_message": _extract_firecrawl_message(raw_result),
        }, 200

    duration_ms = int((time.perf_counter() - started_at) * 1000)
    print(f"[safety] firecrawl job created: id={firecrawl_job_id}, status={firecrawl_status}")
    return {
        "safety_report": {},
        "summary": "",
        "provider": "firecrawl",
        "duration_ms": duration_ms,
        "used_urls": urls,
        "firecrawl_status": firecrawl_status,
        "firecrawl_job_id": firecrawl_job_id,
        "firecrawl_status_url": firecrawl_status_url,
        "firecrawl_verbose": raw_result,
        "firecrawl_message": _extract_firecrawl_message(raw_result),
        "warning": "Safety job started. Polling required until completion.",
    }, 200
