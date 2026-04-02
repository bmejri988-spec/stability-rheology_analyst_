import json
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from agent.agent import create_agent
from models.formula_schema import build_agent_input, parse_formula_input

_AGENT = None


def _agent_instance():
    global _AGENT
    if _AGENT is None:
        _AGENT, _ = create_agent()
    return _AGENT


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


def health(request):
    return JsonResponse({"status": "ok"})


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
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return JsonResponse(
            {
                "output": result.get("output", ""),
                "tools": tools,
                "coverage_retry": retried,
                "duration_ms": duration_ms,
                "trace": _trace_from_steps(result),
            }
        )
    except Exception as exc:
        return JsonResponse({"error": f"Assessment failed: {exc}"}, status=500)
