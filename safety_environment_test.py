import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# -----------------------------
# MOCK STABILITY OUTPUT
# -----------------------------
with open("stability_sample.json", "r") as f:
    STABILITY_FIXTURE = json.load(f)


FORMULA_PAYLOAD: dict[str, Any] = {
    "product_name": "Gentle Purify Foaming Cleanser",
    "product_type": "Surfactant Gel",
    "target_ph": 5.5,
    "ingredients": [
        {"inci_name": "Aqua", "wt_pct": 60.4, "phase": "A"},
        {"inci_name": "Sodium Laureth Sulfate (70%)", "wt_pct": 15.0, "phase": "B"},
        {"inci_name": "Cocamidopropyl Betaine (30%)", "wt_pct": 10.0, "phase": "B"},
        {"inci_name": "Decyl Glucoside", "wt_pct": 5.0, "phase": "B"},
        {"inci_name": "PEG-150 Distearate", "wt_pct": 2.0, "phase": "C"},
        {"inci_name": "Sodium Chloride", "wt_pct": 1.0, "phase": "E"},
    ],
}


def _extract_result_payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "structuredContent") and isinstance(result.structuredContent, dict):
        return result.structuredContent

    content = getattr(result, "content", None)
    if isinstance(content, list):
        for chunk in content:
            text = getattr(chunk, "text", None)
            if isinstance(text, str) and text.strip().startswith("{"):
                try:
                    return json.loads(text)
                except Exception:
                    pass

    return {}


async def _call_tool_payload(session: ClientSession, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    raw = await session.call_tool(tool_name, args)
    payload = _extract_result_payload(raw)

    if not payload:
        raise RuntimeError(f"Tool '{tool_name}' returned empty payload")

    return payload


async def main() -> int:
    server = StdioServerParameters(
        command="python",
        args=["backend/mcpServer.py"]
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # -----------------------------
            # FIXTURE (NO STABILITY TOOL)
            # -----------------------------
            print("1) Using cached stability fixture...")

            structured_report = STABILITY_FIXTURE.get("structured_report")

            if not isinstance(structured_report, dict):
                print("Invalid fixture format", file=sys.stderr)
                return 1

            # -----------------------------
            # SINGLE CALL ONLY
            # -----------------------------
            print("2) Running safety_environment...")

            safety_payload = await _call_tool_payload(
                session,
                "safety_environment",
                {
                    "payload": {
                        "report": structured_report,
                        "formula": FORMULA_PAYLOAD,
                    }
                },
            )

            # -----------------------------
            # FINAL OUTPUT
            # -----------------------------
            print("Final safety_environment response:")
            print(json.dumps(safety_payload, indent=2))

            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))