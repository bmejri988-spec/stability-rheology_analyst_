import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.agent import create_agent
from agent.agent2 import build_agent2_input, create_agent2, run_agent2_fallback
from api.safety_agent import process_safety_request
from config import ASSESSMENT_ENFORCE_TOOL_COVERAGE_RETRY
from models.formula_schema import build_agent_input, parse_formula_input


mcp = FastMCP("stability-rheology-analyst")

_AGENT = None
_AGENT2 = None


def _agent_instance():
    global _AGENT
    if _AGENT is None:
        _AGENT, _ = create_agent()
    return _AGENT


def _agent2_instance():
    global _AGENT2
    if _AGENT2 is None:
        _AGENT2 = create_agent2()
    return _AGENT2


def _coerce_json_dict(raw_output: Any) -> dict[str, Any] | None:
    if isinstance(raw_output, dict):
        return raw_output

    if not isinstance(raw_output, str):
        return None

    text = raw_output.strip()
    if not text:
        return None

    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

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


def _clean_text_artifacts(text: str) -> str:
    cleaned = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    return cleaned.strip()


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
    has_chemistry_or_lit = any(
        t in tools for t in ["pubchem_property_tool", "rdkit_analysis_tool", "semantic_scholar_search"]
    )
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


@mcp.tool()
def health() -> dict[str, str]:
    return {"status": "ok"}


@mcp.tool()
def stability_rheology_check(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        formula = parse_formula_input(json.dumps(payload))
    except Exception as exc:
        return {"error": f"Invalid formula payload: {exc}"}

    started_at = time.perf_counter()
    try:
        result, tools, retried = _run_with_minimum_tool_coverage(_agent_instance(), build_agent_input(formula))
        raw_output = result.get("output", "")
        report_text = _extract_report_text(raw_output)
        structured_report = _extract_structured_report(raw_output)
    except Exception as exc:
        return {"error": f"Formula assessment failed: {exc}"}

    duration_ms = int((time.perf_counter() - started_at) * 1000)
    return {
        "report_text": report_text,
        "structured_report": structured_report,
        "tools": tools,
        "retried": retried,
        "duration_ms": duration_ms,
    }


@mcp.tool()
def safety_environment(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response_payload, status_code = process_safety_request(payload)
    except Exception as exc:
        return {"error": f"Safety assessment failed: {exc}"}

    return {"status_code": status_code, **response_payload}


@mcp.tool()
def rheology_assistant(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    message = str(message).strip()
    if not message:
        return {"error": "Field 'message' is required."}

    if not isinstance(history, list):
        history = []
    history = history[-8:]

    started_at = time.perf_counter()
    fallback_used = False
    tools: list[str] = []

    try:
        agent2 = _agent2_instance()
        result = agent2.invoke({"input": build_agent2_input(message, history)})
        reply = str(result.get("output", "")).strip()
        tools = _tools_from_steps(result)
    except Exception:
        fallback_used = True
        try:
            reply = run_agent2_fallback(message, history)
        except Exception as exc:
            return {"error": f"Rheology Assistant failed: {exc}"}

    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if not reply:
        reply = "I could not generate a response for that. Please try rephrasing your question."

    return {
        "reply": reply,
        "duration_ms": duration_ms,
        "tools": tools,
        "fallback_used": fallback_used,
    }


if __name__ == "__main__":
    print("MCP server starting. Waiting for a client connection...", file=sys.stderr)
    mcp.run()
