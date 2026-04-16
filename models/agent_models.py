from typing import List

from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    brief_stability_conclusion: str = Field(..., description="Short overall stability conclusion")
    key_risks_overview: List[str] = Field(default_factory=list, description="Top risk bullets")
    expected_shelf_life_behavior: str = Field(..., description="Expected behavior over shelf-life")
    risk_level: str = Field(..., description="Low, Medium, or High")
    confidence_level: str = Field(..., description="Low, Medium, or High")
    launch_decision: str = Field(..., description="Proceed, Proceed with Mitigations, or Hold")


class FormulationArchitecture(BaseModel):
    emulsion_type: str = Field(..., description="O/W, W/O, gel cream, serum gel, etc.")
    stabilization_mechanisms: List[str] = Field(default_factory=list, description="Mechanistic stabilization bullets")
    key_structuring_agents: List[str] = Field(default_factory=list, description="Primary structuring ingredients")


class IngredientFunctionalRow(BaseModel):
    ingredient: str = Field(..., description="Ingredient name")
    function: str = Field(..., description="Primary formulation function")
    stability_role: str = Field(..., description="How it contributes to or risks stability")


class RheologicalPrediction(BaseModel):
    flow_type: str = Field(..., description="Newtonian, shear-thinning, viscoelastic, etc.")
    yield_stress_presence: str = Field(..., description="Expected presence and qualitative magnitude")
    thixotropy_behavior: str = Field(..., description="Expected rebuild and hysteresis behavior")
    viscosity_profile_under_shear: str = Field(..., description="Viscosity trend across shear rates")


class StabilityRiskAssessment(BaseModel):
    polymer_instability_risks: List[str] = Field(default_factory=list)
    emulsion_breakdown_risks: List[str] = Field(default_factory=list)
    thermal_sensitivity: List[str] = Field(default_factory=list)
    ph_sensitivity: List[str] = Field(default_factory=list)
    electrolyte_sensitivity: List[str] = Field(default_factory=list)


class ProcessSensitivityAnalysis(BaseModel):
    mixing_order_impact: List[str] = Field(default_factory=list)
    temperature_sensitivity: List[str] = Field(default_factory=list)
    homogenization_effects: List[str] = Field(default_factory=list)
    neutralization_risks: List[str] = Field(default_factory=list)


class PackagingCompatibility(BaseModel):
    material_compatibility: List[str] = Field(default_factory=list)
    oxygen_water_barrier: List[str] = Field(default_factory=list)
    headspace_effects: List[str] = Field(default_factory=list)


class SustainabilityAssessment(BaseModel):
    ingredient_origin_and_renewability: List[str] = Field(default_factory=list)
    biodegradability_and_ecotoxicity: List[str] = Field(default_factory=list)
    packaging_and_waste_impact: List[str] = Field(default_factory=list)
    process_and_energy_footprint: List[str] = Field(default_factory=list)
    safer_or_lower_impact_alternatives: List[str] = Field(default_factory=list)


class StabilityPredictionRow(BaseModel):
    condition: str = Field(..., description="Storage condition")
    prediction: str = Field(..., description="Predicted response under this condition")
    risk_level: str = Field(..., description="Low, Medium, or High")


class OptimizationRecommendations(BaseModel):
    ingredient_adjustments: List[str] = Field(default_factory=list)
    process_improvements: List[str] = Field(default_factory=list)
    stability_enhancers: List[str] = Field(default_factory=list)


class ReferenceItem(BaseModel):
    title: str = Field(..., description="Paper title or document name")
    year: str = Field(default="", description="Publication year if known")
    source_type: str = Field(..., description="paper, pdf, internal_doc, experimental_data, tool_output")
    relevance: str = Field(..., description="One-line relevance to the conclusion")
    source_file: str = Field(default="", description="File path or document identifier if applicable")
    pages: str = Field(default="", description="Page number or page range if applicable")
    url: str = Field(default="", description="External URL if available")


class StructuredReport(BaseModel):
    executive_summary: ExecutiveSummary
    formulation_architecture: FormulationArchitecture
    ingredient_functional_analysis: List[IngredientFunctionalRow] = Field(default_factory=list)
    rheological_prediction: RheologicalPrediction
    stability_risk_assessment: StabilityRiskAssessment
    process_sensitivity_analysis: ProcessSensitivityAnalysis
    packaging_compatibility: PackagingCompatibility
    sustainability_assessment: SustainabilityAssessment = Field(default_factory=SustainabilityAssessment)
    accelerated_real_time_stability_prediction: List[StabilityPredictionRow] = Field(default_factory=list)
    weak_points_summary: List[str] = Field(default_factory=list)
    optimization_recommendations: OptimizationRecommendations
    final_conclusion: str = Field(..., description="Single final formulation verdict")
    references: List[ReferenceItem] = Field(default_factory=list)


class AgentResponse(BaseModel):
    response: str = Field(
        default="",
        description="Optional short plain-text summary. Structured report content must be in report.",
    )
    report: StructuredReport = Field(..., description="Primary structured report object aligned with the 12-section template")
    tools_used: List[str] = Field(default_factory=list, description="List of tool names actually called")