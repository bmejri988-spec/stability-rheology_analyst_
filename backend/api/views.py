import json
import re
import time
from typing import Any

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from agent.agent import create_agent
from agent.agent2 import build_agent2_input, create_agent2, run_agent2_fallback
from config import ASSESSMENT_ENFORCE_TOOL_COVERAGE_RETRY
from models.formula_schema import build_agent_input, parse_formula_input
from .safety_agent import process_safety_request

_AGENT = None
_AGENT2 = None
_AGENT_PARSER = None


def _agent_instance():
    global _AGENT, _AGENT_PARSER
    if _AGENT is None:
        _AGENT, _AGENT_PARSER = create_agent()
    return _AGENT


def _coerce_json_dict(raw_output: Any) -> dict[str, Any] | None:
    if isinstance(raw_output, dict):
        return raw_output

    if not isinstance(raw_output, str):
        return None

    text = raw_output.strip()
    if not text:
        return None

    # Remove optional markdown code fences.
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    # First try direct JSON decode.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Fallback: extract the largest JSON object span.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None

    return None


def _clean_text_artifacts(text: str) -> str:
    cleaned = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    return cleaned.strip()


def _agent2_instance():
    global _AGENT2
    if _AGENT2 is None:
        _AGENT2 = create_agent2()
    return _AGENT2


def _tools_from_agent2_steps(result: dict[str, Any]) -> list[str]:
    tools: list[str] = []
    for step in result.get("intermediate_steps", []):
        action = step[0]
        name = getattr(action, "tool", None)
        if name and name not in tools:
            tools.append(name)
    return tools


def _tools_from_steps(response):
    tools = []
    for step in response.get("intermediate_steps", []):
        action = step[0]
        name = getattr(action, "tool", None)
        if name and name not in tools:
            tools.append(name)
    return tools


def _run_with_minimum_tool_coverage(agent, agent_input: str):
    first = agent.invoke({"input": agent_input})
    tools = _tools_from_steps(first)

    if not ASSESSMENT_ENFORCE_TOOL_COVERAGE_RETRY:
        return first, tools, False

    has_ingredient_tool = "ingredient_lookup_tool" in tools
    has_chemistry_or_lit = any(t in tools for t in ["pubchem_property_tool", "rdkit_analysis_tool", "semantic_scholar_search"])
    has_rag = "search_formulation_docs" in tools

    if has_rag and has_ingredient_tool and has_chemistry_or_lit:
        return first, tools, False

    retry_input = (
        agent_input
        + "\n\nMANDATORY TOOL COVERAGE OVERRIDE:\n"
        + "Re-run the assessment with cross-check coverage. You must call search_formulation_docs, ingredient_lookup_tool, "
        + "and at least one of pubchem_property_tool / rdkit_analysis_tool / semantic_scholar_search before finalizing."
    )
    second = agent.invoke({"input": retry_input})
    return second, _tools_from_steps(second), True


def _trace_from_steps(response):
    trace = []
    for idx, step in enumerate(response.get("intermediate_steps", []), start=1):
        action, observation = step
        tool_name = getattr(action, "tool", "unknown")
        tool_input = getattr(action, "tool_input", "")

        if isinstance(tool_input, (dict, list)):
            input_text = json.dumps(tool_input, ensure_ascii=True)
        else:
            input_text = str(tool_input)

        output_text = str(observation)
        if len(output_text) > 600:
            output_text = output_text[:600] + " ..."

        trace.append(
            {
                "step": idx,
                "tool": tool_name,
                "input": input_text,
                "output_preview": output_text,
            }
        )

    return trace


def _extract_report_text(raw_output: Any) -> str:
    parsed = _coerce_json_dict(raw_output)
    if parsed is not None:
        response_text = parsed.get("response")
        if isinstance(response_text, str) and response_text.strip():
            return _clean_text_artifacts(response_text)
        return json.dumps(parsed, ensure_ascii=True, indent=2)

    return _clean_text_artifacts(str(raw_output))


def _extract_structured_report(raw_output: Any) -> dict[str, Any] | None:
    parsed = _coerce_json_dict(raw_output)
    if parsed is None:
        return None

    report_obj = parsed.get("report")
    if isinstance(report_obj, dict):
        return report_obj
    return None


def _structured_report_to_text(report: dict[str, Any]) -> str:
    def _s(v: Any, default: str = "") -> str:
        return str(v).strip() if v is not None else default

    def _list(v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    def _bullets(items: list[str], fallback: str) -> str:
        if not items:
            return f"- {fallback}"
        return "\n".join(f"- {item}" for item in items)

    exec_sum = report.get("executive_summary", {}) if isinstance(report.get("executive_summary"), dict) else {}
    architecture = report.get("formulation_architecture", {}) if isinstance(report.get("formulation_architecture"), dict) else {}
    rheology = report.get("rheological_prediction", {}) if isinstance(report.get("rheological_prediction"), dict) else {}
    risk = report.get("stability_risk_assessment", {}) if isinstance(report.get("stability_risk_assessment"), dict) else {}
    process = report.get("process_sensitivity_analysis", {}) if isinstance(report.get("process_sensitivity_analysis"), dict) else {}
    packaging = report.get("packaging_compatibility", {}) if isinstance(report.get("packaging_compatibility"), dict) else {}
    sustainability = report.get("sustainability_assessment", {}) if isinstance(report.get("sustainability_assessment"), dict) else {}
    optim = report.get("optimization_recommendations", {}) if isinstance(report.get("optimization_recommendations"), dict) else {}

    ingredient_rows = report.get("ingredient_functional_analysis", []) if isinstance(report.get("ingredient_functional_analysis"), list) else []
    stability_rows = report.get("accelerated_real_time_stability_prediction", []) if isinstance(report.get("accelerated_real_time_stability_prediction"), list) else []
    weak_points = _list(report.get("weak_points_summary"))
    references = report.get("references", []) if isinstance(report.get("references"), list) else []

    ingredient_table_lines = ["| Ingredient | Function | Stability Role |", "|---|---|---|"]
    for row in ingredient_rows:
        if isinstance(row, dict):
            ingredient_table_lines.append(
                f"| {_s(row.get('ingredient'), 'n/a')} | {_s(row.get('function'), 'n/a')} | {_s(row.get('stability_role'), 'n/a')} |"
            )
    if len(ingredient_table_lines) == 2:
        ingredient_table_lines.append("| n/a | n/a | n/a |")

    stability_table_lines = ["| Condition | Prediction | Risk Level |", "|---|---|---|"]
    for row in stability_rows:
        if isinstance(row, dict):
            stability_table_lines.append(
                f"| {_s(row.get('condition'), 'n/a')} | {_s(row.get('prediction'), 'n/a')} | {_s(row.get('risk_level'), 'Medium')} |"
            )
    if len(stability_table_lines) == 2:
        stability_table_lines.append("| n/a | n/a | Medium |")

    reference_lines: list[str] = []
    for ref in references:
        if not isinstance(ref, dict):
            continue
        title = _s(ref.get("title"), "Untitled reference")
        year = _s(ref.get("year"), "n/a")
        source_type = _s(ref.get("source_type"), "paper")
        relevance = _s(ref.get("relevance"), "Relevant evidence source")
        source_file = _s(ref.get("source_file"))
        pages = _s(ref.get("pages"))
        url = _s(ref.get("url"))

        line = f"- {title} ({year}) [{source_type}]"
        if url:
            line += f" - {url}"
        reference_lines.append(line)
        reference_lines.append(f"  Relevance: {relevance}")
        if source_file:
            reference_lines.append(f"  Source File: {source_file}")
        if pages:
            reference_lines.append(f"  Pages: {pages}")

    if not reference_lines:
        reference_lines.append("- No references available in this run.")

    return (
        "1. Executive Summary\n"
        f"- Brief stability conclusion: {_s(exec_sum.get('brief_stability_conclusion'), 'Assessment indicates moderate formulation risk requiring controls.')}\n"
        f"- Key risks overview:\n{_bullets(_list(exec_sum.get('key_risks_overview')), 'Viscosity drift and phase stability under stress conditions.')}\n"
        f"- Expected shelf-life behavior: {_s(exec_sum.get('expected_shelf_life_behavior'), 'Potential viscosity drift over storage without optimization.')}\n"
        f"- Risk Level: {_s(exec_sum.get('risk_level'), 'Medium')}\n"
        f"- Confidence Level: {_s(exec_sum.get('confidence_level'), 'Medium')}\n"
        f"- Launch Decision: {_s(exec_sum.get('launch_decision'), 'Proceed with Mitigations')}\n\n"
        "2. Formulation Architecture\n"
        f"- Emulsion type: {_s(architecture.get('emulsion_type'), 'Not explicitly specified')}\n"
        f"- Stabilization mechanisms:\n{_bullets(_list(architecture.get('stabilization_mechanisms')), 'Polymer structuring, emulsifier film formation, and process control.')}\n"
        f"- Key structuring agents:\n{_bullets(_list(architecture.get('key_structuring_agents')), 'Primary thickener/emulsifier system identified from formula composition.')}\n\n"
        "3. Ingredient Functional Analysis\n"
        + "\n".join(ingredient_table_lines)
        + "\n\n"
        "4. Rheological Prediction\n"
        f"- Flow type: {_s(rheology.get('flow_type'), 'Shear-thinning / viscoelastic tendency expected')}\n"
        f"- Yield stress presence: {_s(rheology.get('yield_stress_presence'), 'Low-to-moderate yield stress likely')}\n"
        f"- Thixotropy behavior: {_s(rheology.get('thixotropy_behavior'), 'Partial structure rebuild after shear likely')}\n"
        f"- Viscosity profile under shear: {_s(rheology.get('viscosity_profile_under_shear'), 'Viscosity decreases with increasing shear rate')}\n\n"
        "5. Stability Risk Assessment\n"
        f"- Polymer instability risks:\n{_bullets(_list(risk.get('polymer_instability_risks')), 'Polymer-electrolyte interactions may reduce viscosity stability.')}\n"
        f"- Emulsion breakdown risks:\n{_bullets(_list(risk.get('emulsion_breakdown_risks')), 'Droplet coalescence risk under thermal and shear stress.')}\n"
        f"- Thermal sensitivity:\n{_bullets(_list(risk.get('thermal_sensitivity')), 'Elevated temperature may accelerate viscosity and phase drift.')}\n"
        f"- pH sensitivity:\n{_bullets(_list(risk.get('ph_sensitivity')), 'pH shifts may alter thickener efficiency and interfacial stability.')}\n"
        f"- Electrolyte sensitivity:\n{_bullets(_list(risk.get('electrolyte_sensitivity')), 'Salt content may compress polymer coils and reduce viscosity.')}\n\n"
        "6. Process Sensitivity Analysis\n"
        f"- Mixing order impact:\n{_bullets(_list(process.get('mixing_order_impact')), 'Order of addition can affect hydration and emulsion robustness.')}\n"
        f"- Temperature sensitivity:\n{_bullets(_list(process.get('temperature_sensitivity')), 'Temperature during processing affects dispersion and final microstructure.')}\n"
        f"- Homogenization effects:\n{_bullets(_list(process.get('homogenization_effects')), 'Over/under-homogenization can destabilize rheology and droplet size.')}\n"
        f"- Neutralization risks:\n{_bullets(_list(process.get('neutralization_risks')), 'Neutralization timing and target pH strongly impact viscosity build.')}\n\n"
        "7. Packaging Compatibility\n"
        f"- Material compatibility:\n{_bullets(_list(packaging.get('material_compatibility')), 'Verify compatibility with selected polymer/preservative system.')}\n"
        f"- Oxygen / water barrier:\n{_bullets(_list(packaging.get('oxygen_water_barrier')), 'Barrier properties influence oxidation and moisture loss/gain.')}\n"
        f"- Headspace effects:\n{_bullets(_list(packaging.get('headspace_effects')), 'Headspace may influence oxidation and volatile loss.')}\n\n"
        "8. Sustainability & Environmental Safety\n"
        f"- Ingredient origin and renewability:\n{_bullets(_list(sustainability.get('ingredient_origin_and_renewability')), 'Screen for renewable feedstocks, restricted substances, and renewable content where data exists.')}\n"
        f"- Biodegradability and ecotoxicity:\n{_bullets(_list(sustainability.get('biodegradability_and_ecotoxicity')), 'Use conservative screening when direct biodegradation or ecotoxicity data is unavailable.')}\n"
        f"- Packaging and waste impact:\n{_bullets(_list(sustainability.get('packaging_and_waste_impact')), 'Prefer recyclable, refillable, or lower-material packaging where feasible.')}\n"
        f"- Process and energy footprint:\n{_bullets(_list(sustainability.get('process_and_energy_footprint')), 'Lower heating, rework, and hold times when process design allows.')}\n"
        f"- Safer or lower-impact alternatives:\n{_bullets(_list(sustainability.get('safer_or_lower_impact_alternatives')), 'Consider lower-impact substitutes only when they preserve performance and safety.')}\n\n"
        "9. Accelerated & Real-Time Stability Prediction\n"
        + "\n".join(stability_table_lines)
        + "\n\n"
        "10. Weak Points Summary\n"
        f"{_bullets(weak_points, 'Key vulnerability is viscosity/structure drift under combined process and storage stress.')}\n\n"
        "11. Optimization Recommendations\n"
        f"- Ingredient adjustments:\n{_bullets(_list(optim.get('ingredient_adjustments')), 'Tune structurant/emulsifier ratio and electrolyte tolerance.')}\n"
        f"- Process improvements:\n{_bullets(_list(optim.get('process_improvements')), 'Tighten mixing, temperature, and neutralization control windows.')}\n"
        f"- Stability enhancers:\n{_bullets(_list(optim.get('stability_enhancers')), 'Add robustness tests and consider co-structurant support.')}\n\n"
        "12. Final Conclusion\n"
        f"- {_s(report.get('final_conclusion'), 'Formulation appears feasible with targeted mitigations and validation testing.')}\n\n"
        "References\n"
        + "\n".join(reference_lines)
    )


def _extract_used_papers(response: dict[str, Any]) -> list[dict[str, str]]:
    papers: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for step in response.get("intermediate_steps", []):
        action, observation = step
        tool_name = getattr(action, "tool", "")
        query = getattr(action, "tool_input", "")
        query_text = query if isinstance(query, str) else json.dumps(query, ensure_ascii=True)

        payload = None
        try:
            payload = json.loads(str(observation))
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        raw_papers = payload.get("papers", [])
        if not isinstance(raw_papers, list):
            continue

        for item in raw_papers:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            title_key = title.lower()
            if title_key in seen_titles:
                continue

            seen_titles.add(title_key)
            year = str(item.get("year") or "n/a")
            url = str(item.get("url") or "")
            venue = str(item.get("venue") or "")
            relevance = f"Retrieved in this run via {tool_name or 'tool'}"
            if query_text:
                relevance += f" for query: {query_text[:120]}"
            if venue:
                relevance += f" ({venue})"

            papers.append(
                {
                    "title": title,
                    "year": year,
                    "url": url,
                    "relevance": relevance,
                }
            )

    return papers[:5]


def _format_related_papers(papers: list[dict[str, str]]) -> str:
    if not papers:
        return (
            "Related Papers\n"
            "- No literature papers were used in this run."
        )

    lines = ["Related Papers"]
    for paper in papers:
        line = f"- {paper['title']} ({paper['year']})"
        if paper.get("url"):
            line += f" - {paper['url']}"
        lines.append(line)
        lines.append(f"  Relevance: {paper['relevance']}")
    return "\n".join(lines)


def _to_bullets(text: str, fallback: str) -> str:
    raw = (text or "").strip()
    if not raw:
        raw = fallback

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return f"- {fallback}"

    normalized = []
    for line in lines:
        cleaned = re.sub(r"^[-*\d\.)\s]+", "", line).strip()
        if not cleaned:
            continue
        normalized.append(f"- {cleaned}")

    if not normalized:
        return f"- {fallback}"

    return "\n".join(normalized)


def _extract_risk_level(overall_text: str) -> str:
    text = (overall_text or "").lower()
    if "high" in text:
        return "High"
    if "medium" in text or "moderate" in text:
        return "Medium"
    if "low" in text:
        return "Low"
    return "Medium"


def _extract_confidence_level(text: str) -> str:
    sample = (text or "").lower()
    if "confidence level: high" in sample or "high confidence" in sample:
        return "High"
    if "confidence level: low" in sample or "low confidence" in sample:
        return "Low"
    return "Medium"


def _capture_section(text: str, patterns: list[str], stop_tokens: str) -> str:
    for pattern in patterns:
        match = re.search(
            pattern + r"[:\s]*([\s\S]*?)(?=(?:" + stop_tokens + r"|$))",
            text,
            re.IGNORECASE,
        )
        if match and match.group(1):
            captured = match.group(1).strip()
            if captured:
                return captured
    return ""


def _first_bullet_line(text: str, fallback: str) -> str:
    lines = _to_bullets(text, fallback).splitlines()
    if not lines:
        return fallback
    return re.sub(r"^[-*\s]+", "", lines[0]).strip() or fallback


def _normalize_report_structure(report_text: str, papers_section: str) -> str:
    text = report_text.strip()
    papers_body = re.sub(r"^\s*related\s*papers\s*", "", papers_section.strip(), flags=re.IGNORECASE).strip()

    stop_tokens = (
        r"\d+\.\s*executive\s*summary|\d+\.\s*formulation\s*architecture|\d+\.\s*ingredient\s*functional\s*analysis"
        r"|\d+\.\s*rheological\s*prediction|\d+\.\s*stability\s*risk\s*assessment|\d+\.\s*process\s*sensitivity\s*analysis"
        r"|\d+\.\s*packaging\s*compatibility|\d+\.\s*sustainability|\d+\.\s*accelerated|\d+\.\s*weak\s*points|\d+\.\s*optimization|\d+\.\s*final\s*conclusion"
        r"|A\)\s*executive\s*snapshot|B\)\s*failure\s*mode|C\)\s*action\s*plan|D\)\s*required\s*test\s*plan|E\)\s*evidence\s*ledger|F\)\s*references"
        r"|references|related\s*papers"
    )

    executive = _capture_section(
        text,
        [
            r"(?:1\.\s*executive\s*summary)",
            r"(?:A\)\s*executive\s*snapshot)",
            r"(?:overall\s*risk\s*summary|risk\s*summary)",
        ],
        stop_tokens,
    )
    architecture = _capture_section(text, [r"(?:2\.\s*formulation\s*architecture)"], stop_tokens)
    ingredient = _capture_section(text, [r"(?:3\.\s*ingredient\s*functional\s*analysis)"], stop_tokens)
    rheology = _capture_section(text, [r"(?:4\.\s*rheological\s*prediction)"], stop_tokens)
    matrix = _capture_section(
        text,
        [
            r"(?:5\.\s*stability\s*risk\s*assessment)",
            r"(?:B\)\s*failure\s*mode\s*matrix)",
            r"(?:key\s*risk\s*drivers?)",
        ],
        stop_tokens,
    )
    process = _capture_section(text, [r"(?:6\.\s*process\s*sensitivity\s*analysis)"], stop_tokens)
    packaging = _capture_section(text, [r"(?:7\.\s*packaging\s*compatibility)"], stop_tokens)
    sustainability = _capture_section(text, [r"(?:8\.\s*sustainability.*?|8\.\s*environmental.*?|8\.\s*eco.*?)"], stop_tokens)
    stability_pred = _capture_section(text, [r"(?:9\.\s*accelerated.*?)"], stop_tokens)
    weak_points = _capture_section(text, [r"(?:10\.\s*weak\s*points\s*summary)"], stop_tokens)
    action_plan = _capture_section(
        text,
        [
            r"(?:11\.\s*optimization\s*recommendations)",
            r"(?:C\)\s*action\s*plan)",
            r"(?:recommended\s*actions?)",
        ],
        stop_tokens,
    )
    final_conclusion = _capture_section(text, [r"(?:12\.\s*final\s*conclusion)"], stop_tokens)
    test_plan = _capture_section(text, [r"(?:D\)\s*required\s*test\s*plan)"], stop_tokens)
    evidence = _capture_section(text, [r"(?:E\)\s*evidence\s*ledger)"], stop_tokens)
    confidence = _capture_section(text, [r"(?:confidence|data\s*gaps?)"], stop_tokens)

    if not executive:
        executive = text

    risk_level = _extract_risk_level(executive)
    confidence_level = _extract_confidence_level(confidence)
    top_failure_mode = _first_bullet_line(matrix, "Viscosity drift under process/storage stress")

    executive_block = (
        f"- Risk Level: {risk_level}\n"
        f"- Confidence Level: {confidence_level}\n"
        f"- Launch Decision: {'Proceed with Mitigations' if risk_level in {'Medium', 'High'} else 'Proceed'}\n"
        f"- Top Failure Mode: {top_failure_mode}\n"
        + _to_bullets(
            executive,
            "Assessment synthesized from available composition, process, and evidence context.",
        )
    )

    matrix_block = _to_bullets(
        matrix,
        "Phase separation | Likelihood=Medium | Impact=High | Evidence Basis=Formulation and rheology heuristics.",
    )

    actions_block = _to_bullets(
        action_plan,
        "Confirm with accelerated and real-time stability, viscosity profiling, and process window verification.",
    )
    if "now" not in actions_block.lower() and "0-2" not in actions_block.lower():
        actions_block = (
            "- Now (0-2 weeks): Stabilize process controls and confirm pH/viscosity window.\n"
            "- Next (2-6 weeks): Run accelerated storage and packaging compatibility checks.\n"
            "- Scale-up Controls: Lock mixing order, shear window, and hold-time limits before pilot scale.\n"
            + actions_block
        )

    test_plan_block = _to_bullets(
        test_plan,
        "Rheology: flow curve + amplitude/frequency sweeps under initial and aged conditions with predefined pass windows.\n"
        "Physical Stability: centrifuge, thermal cycling, and freeze-thaw with visual and viscosity pass/fail criteria.\n"
        "Packaging Compatibility: monitor pH, viscosity drift, and organoleptic changes in final pack.",
    )

    evidence_block = _to_bullets(
        evidence,
        "Experimental Evidence: empirical dataset matching was limited or indirect for this formula profile.\n"
        "Formulation/Chemistry Evidence: ingredient function and polarity/solubility behavior were considered.\n"
        "Literature Evidence: domain papers and internal RAG references were used where available.",
    )
    if "confidence" in confidence.lower() or "data gap" in confidence.lower():
        evidence_block += "\n" + _to_bullets(confidence, "Confidence and data-gap notes included.")

    if not architecture:
        architecture = "Emulsion and structuring architecture inferred from composition and process data."
    if not ingredient:
        ingredient = "| Ingredient | Function | Stability Role |\n|---|---|---|\n| n/a | n/a | n/a |"
    if not rheology:
        rheology = "Flow likely shear-thinning with possible viscoelastic structure and process-dependent recovery."
    if not process:
        process = "Mixing order, neutralization timing, and shear history can materially impact final stability."
    if not packaging:
        packaging = "Verify material compatibility and barrier/headspace effects under accelerated storage."
    if not sustainability:
        sustainability = (
            "Ingredient origin and renewability should be screened for bio-based content, recyclability, and restricted substances.\n"
            "Packaging and waste impact should favor lower-material, recyclable, or refillable options where feasible.\n"
            "Process and energy footprint should minimize heating, hold time, and rework."
        )
    if not stability_pred:
        stability_pred = "| Condition | Prediction | Risk Level |\n|---|---|---|\n| 40C / 75% RH | Viscosity drift risk | Medium |"
    if not weak_points:
        weak_points = "Viscosity drift and phase robustness under storage/process stress are primary concerns."
    if not final_conclusion:
        final_conclusion = "Formulation is viable with mitigations and targeted validation testing."

    references_block = papers_body if papers_body else "- No references available in this run."

    return (
        "1. Executive Summary\n"
        f"{executive_block}\n\n"
        "2. Formulation Architecture\n"
        f"{_to_bullets(architecture, 'Architecture inferred from formula composition and process setup.')}\n\n"
        "3. Ingredient Functional Analysis\n"
        f"{ingredient}\n\n"
        "4. Rheological Prediction\n"
        f"{_to_bullets(rheology, 'Shear-thinning behavior with process-sensitive rebuild is expected.')}\n\n"
        "5. Stability Risk Assessment\n"
        f"{matrix_block}\n\n"
        "6. Process Sensitivity Analysis\n"
        f"{_to_bullets(process, 'Process sequence and shear-temperature windows should be tightly controlled.')}\n\n"
        "7. Packaging Compatibility\n"
        f"{_to_bullets(packaging, 'Confirm packaging compatibility under accelerated and real-time conditions.')}\n\n"
        "8. Sustainability & Environmental Safety\n"
        f"{_to_bullets(sustainability, 'Screen ingredient origin, packaging waste, and process footprint for lower-impact choices.')}\n\n"
        "9. Accelerated & Real-Time Stability Prediction\n"
        f"{stability_pred}\n\n"
        "10. Weak Points Summary\n"
        f"{_to_bullets(weak_points, 'Primary weakness is structure/viscosity robustness under stress.')}\n\n"
        "11. Optimization Recommendations\n"
        f"{actions_block}\n\n"
        "12. Final Conclusion\n"
        f"- {final_conclusion.strip()}\n\n"
        "References\n"
        f"{references_block}\n\n"
        "Appendix - Required Test Plan\n"
        f"{test_plan_block}\n\n"
        "Appendix - Evidence Ledger\n"
        f"{evidence_block}"
    )


def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
def assess_safety(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    response_payload, status_code = process_safety_request(payload)
    return JsonResponse(response_payload, status=status_code)


@csrf_exempt
def agent2_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    message = str(payload.get("message", "")).strip()
    if not message:
        return JsonResponse({"error": "Field 'message' is required."}, status=400)

    history = payload.get("history", [])
    if not isinstance(history, list):
        history = []

    # Keep prompt size bounded for consistent latency.
    history = history[-8:]

    started_at = time.perf_counter()
    fallback_used = False
    tools: list[str] = []

    try:
        agent2 = _agent2_instance()
        result = agent2.invoke({"input": build_agent2_input(message, history)})
        reply = str(result.get("output", "")).strip()
        tools = _tools_from_agent2_steps(result)
    except Exception:
        # If any tool path fails, gracefully degrade to a direct concise model reply.
        fallback_used = True
        try:
            reply = run_agent2_fallback(message, history)
        except Exception as exc:
            return JsonResponse({"error": f"Agent2 chat failed: {exc}"}, status=500)

    duration_ms = int((time.perf_counter() - started_at) * 1000)

    if not reply:
        reply = "I could not generate a response for that. Please try rephrasing your question."

    return JsonResponse(
        {
            "reply": reply,
            "duration_ms": duration_ms,
            "tools": tools,
            "fallback_used": fallback_used,
        }
    )


@csrf_exempt
def assess_formula(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    try:
        formula = parse_formula_input(json.dumps(payload))
    except Exception as exc:
        return JsonResponse({"error": f"Invalid formula payload: {exc}"}, status=400)

    try:
        started_at = time.perf_counter()
        result, tools, retried = _run_with_minimum_tool_coverage(_agent_instance(), build_agent_input(formula))
        raw_output = result.get("output", "")
        report_text = _extract_report_text(raw_output)
        structured_report = _extract_structured_report(raw_output)
        related_papers = _extract_used_papers(result)
        papers_section = _format_related_papers(related_papers)
        if structured_report:
            enhanced_output = _structured_report_to_text(structured_report)
            if papers_section.strip() and "no literature papers were used" not in papers_section.lower():
                enhanced_output += "\n\nReferences (Tool Retrieved)\n" + re.sub(
                    r"^\s*related\s*papers\s*", "", papers_section.strip(), flags=re.IGNORECASE
                ).strip()
        else:
            enhanced_output = _normalize_report_structure(report_text, papers_section)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return JsonResponse(
            {
                "output": enhanced_output,
                "report": structured_report,
                "tools": tools,
                "coverage_retry": retried,
                "duration_ms": duration_ms,
                "trace": _trace_from_steps(result),
            }
        )
    except Exception as exc:
        return JsonResponse({"error": f"Assessment failed: {exc}"}, status=500)