import json
from typing import Any
from urllib.parse import quote

import requests
from langchain.tools import tool
from config import PUBCHEM_TIMEOUT_SECONDS


def get_pubchem_properties(ingredient: str) -> dict[str, Any]:
    """Fetch molecular properties for an ingredient from PubChem PUG REST."""
    query = ingredient.strip()
    if not query:
        return {"error": "ingredient is required"}

    endpoint = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{quote(query)}/property/MolecularWeight,XLogP,CanonicalSMILES,IsomericSMILES/JSON"
    )

    try:
        response = requests.get(endpoint, timeout=PUBCHEM_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "ingredient": query,
            "error": f"PubChem request failed: {exc}",
        }

    try:
        payload = response.json()
        record = payload["PropertyTable"]["Properties"][0]
    except Exception as exc:
        return {
            "ingredient": query,
            "error": f"Unexpected PubChem response format: {exc}",
        }

    return {
        "ingredient": query,
        "molecular_weight": record.get("MolecularWeight"),
        "logP": record.get("XLogP"),
        "SMILES": (
            record.get("CanonicalSMILES")
            or record.get("IsomericSMILES")
            or record.get("SMILES")
            or record.get("ConnectivitySMILES")
        ),
        "source": "PubChem PUG REST",
    }


@tool
def pubchem_property_tool(ingredient: str) -> str:
    """Get PubChem molecular properties (molecular_weight, logP, SMILES) for an ingredient."""
    return json.dumps(get_pubchem_properties(ingredient), ensure_ascii=True)
