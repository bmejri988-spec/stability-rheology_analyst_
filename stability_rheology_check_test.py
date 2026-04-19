import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command="python",
        args=["backend/mcpServer.py"]
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "stability_rheology_check",
                {
                    "payload": {
                        "product_name": "Gentle Purify Foaming Cleanser",
                        "product_type": "Surfactant Gel",
                        "target_ph": 5.5,
                        "ingredients": [
                        {
                            "inci_name": "Aqua",
                            "wt_pct": 60.4,
                            "phase": "A"
                        },
                        {
                            "inci_name": "Disodium EDTA",
                            "wt_pct": 0.1,
                            "phase": "A"
                        },
                        {
                            "inci_name": "Glycerin",
                            "wt_pct": 4.0,
                            "phase": "A"
                        },
                        {
                            "inci_name": "Sodium Laureth Sulfate (70%)",
                            "wt_pct": 15.0,
                            "phase": "B"
                        },
                        {
                            "inci_name": "Cocamidopropyl Betaine (30%)",
                            "wt_pct": 10.0,
                            "phase": "B"
                        },
                        {
                            "inci_name": "Decyl Glucoside",
                            "wt_pct": 5.0,
                            "phase": "B"
                        },
                        {
                            "inci_name": "PEG-150 Distearate",
                            "wt_pct": 2.0,
                            "phase": "C"
                        },
                        {
                            "inci_name": "Sodium Benzoate",
                            "wt_pct": 0.5,
                            "phase": "D"
                        },
                        {
                            "inci_name": "Potassium Sorbate",
                            "wt_pct": 0.3,
                            "phase": "D"
                        },
                        {
                            "inci_name": "Citric Acid (10% sol.)",
                            "wt_pct": 1.5,
                            "phase": "D"
                        },
                        {
                            "inci_name": "Fragrance",
                            "wt_pct": 0.2,
                            "phase": "D"
                        },
                        {
                            "inci_name": "Sodium Chloride",
                            "wt_pct": 1.0,
                            "phase": "E"
                        }
                        ],
                        "process_conditions": {
                        "mixing_order": [
                            "Add Aqua to the main vessel, heat to 65°C. Add Disodium EDTA and Glycerin (Phase A) and mix until dissolved.",
                            "Add Phase B surfactants one by one, mixing slowly to avoid aeration.",
                            "Add PEG-150 Distearate (Phase C) and maintain heat at 65°C until fully melted and incorporated.",
                            "Begin cooling the batch to 40°C.",
                            "Add Phase D ingredients, adjusting pH to 5.5 with Citric Acid.",
                            "Slowly add Sodium Chloride (Phase E) to build final viscosity."
                        ],
                        "mixing_speed_rpm": 250,
                        "processing_temperature_c": 65,
                        "homogenization": False
                        },
                        "packaging": {
                        "format": "pump bottle",
                        "material": "PETG",
                        "headspace_pct": 8
                        },
                        "storage_conditions": [
                        {
                            "label": "Ambient",
                            "temperature_c": 25,
                            "duration_weeks": 12,
                            "light_exposure": "indirect"
                        },
                        {
                            "label": "Accelerated",
                            "temperature_c": 45,
                            "duration_weeks": 12,
                            "light_exposure": "none"
                        },
                        {
                            "label": "Freeze-Thaw Cycling",
                            "temperature_c": -10,
                            "duration_weeks": 4,
                            "light_exposure": "none"
                        }
                        ],
                        "assessment_goal": "Assess viscosity stability across different temperature extremes, monitor for surfactant clouding or phase separation, and ensure the preservative system maintains efficacy without destabilizing the gel network."
                    }
                }
            )

            print(result)

asyncio.run(main())