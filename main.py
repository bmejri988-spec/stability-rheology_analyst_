from agent.agent import create_agent
from models.formula_schema import FORMULA_TEMPLATE, build_agent_input, parse_formula_input


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


def _read_formula_json_input():
    print("Paste formula JSON. Submit an empty line to run. Type 'q' to quit.\n")
    lines = []
    while True:
        line = input()
        if not lines and line.strip().lower() in {"q", "quit", "exit"}:
            return None
        if line.strip() == "":
            if lines:
                return "\n".join(lines)
            continue
        lines.append(line)


def main():
    agent, _ = create_agent()

    while True:
        raw_formula = _read_formula_json_input()
        if raw_formula is None:
            print("Exiting.")
            break

        try:
            formula = parse_formula_input(raw_formula)
        except Exception as exc:
            print("\nInvalid formula payload.")
            print(f"Validation error: {exc}\n")
            print("Template:")
            print(FORMULA_TEMPLATE)
            print()
            continue

        result, tools, retried = _run_with_minimum_tool_coverage(agent, build_agent_input(formula))
        print("\n=== Agent Response ===\n")
        print(result.get("output", ""))
        if retried:
            print("\n[info] Initial run did not meet tool-coverage policy; assessment was retried with enforced coverage.")
        print(f"\n[tools] {', '.join(tools) if tools else 'none'}")
        print()


if __name__ == "__main__":
    main()
 