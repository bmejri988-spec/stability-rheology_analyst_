import json
from typing import Any
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski
from langchain.tools import tool


def analyze_molecule(smiles: str) -> dict[str, Any]:
    """Analyze molecular descriptors from a SMILES string using RDKit."""
    query = smiles.strip()
    if not query:
        return {"error": "smiles is required"}

    mol = Chem.MolFromSmiles(query)
    if mol is None:
        return {"error": "Invalid SMILES", "smiles": query}

    return {
        "smiles": query,
        "molecular_weight": round(float(Descriptors.MolWt(mol)), 4),
        "logP": round(float(Crippen.MolLogP(mol)), 4),
        "hbond_donors": int(Lipinski.NumHDonors(mol)),
        "hbond_acceptors": int(Lipinski.NumHAcceptors(mol)),
        "source": "RDKit",
    }


@tool
def rdkit_analysis_tool(smiles: str) -> str:
    """Compute RDKit descriptors from SMILES (molecular_weight, logP, hbond_donors, hbond_acceptors)."""
    return json.dumps(analyze_molecule(smiles), ensure_ascii=True)
