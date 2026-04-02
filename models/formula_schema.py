import json
from typing import List

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class FormulaIngredient(BaseModel):
    inci_name: str = Field(..., min_length=1, description="INCI ingredient name")
    wt_pct: float = Field(..., gt=0.0, le=100.0, description="Weight percentage")
    phase: str = Field(..., min_length=1, description="Formulation phase (for example: A, B, C, cool_down)")

    @field_validator("inci_name", "phase")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class ProcessConditions(BaseModel):
    mixing_order: List[str] = Field(..., min_length=1, description="Ordered process steps")
    mixing_speed_rpm: int = Field(..., gt=0, description="Primary mixing speed in RPM")
    processing_temperature_c: float = Field(..., ge=-10.0, le=150.0, description="Primary processing temperature")
    homogenization: bool = Field(..., description="Whether homogenization is used")

    @field_validator("mixing_order")
    @classmethod
    def _validate_mixing_order(cls, value: List[str]) -> List[str]:
        cleaned = [step.strip() for step in value if step and step.strip()]
        if not cleaned:
            raise ValueError("must include at least one non-empty process step")
        return cleaned


class Packaging(BaseModel):
    format: str = Field(..., min_length=1, description="Packaging format (for example: airless_pump, jar, tube)")
    material: str = Field(..., min_length=1, description="Packaging material")
    headspace_pct: float = Field(..., ge=0.0, le=100.0, description="Headspace percentage")

    @field_validator("format", "material")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class StorageCondition(BaseModel):
    label: str = Field(..., min_length=1, description="Storage label")
    temperature_c: float = Field(..., ge=-30.0, le=80.0, description="Storage temperature")
    duration_weeks: int = Field(..., gt=0, description="Storage duration in weeks")
    light_exposure: str = Field(..., min_length=1, description="Light exposure condition")

    @field_validator("label", "light_exposure")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class FormulaInput(BaseModel):
    product_name: str = Field(..., min_length=1, description="Product name")
    product_type: str = Field(..., min_length=1, description="Product type (for example: lotion, cream, gel)")
    target_ph: float = Field(..., ge=0.0, le=14.0, description="Target pH")
    ingredients: List[FormulaIngredient] = Field(..., min_length=1)
    process_conditions: ProcessConditions
    packaging: Packaging
    storage_conditions: List[StorageCondition] = Field(..., min_length=1)
    assessment_goal: str = Field(
        default="Perform rheology and physical stability assessment with risks, evidence, confidence, and actions.",
        min_length=1,
    )

    @field_validator("product_name", "product_type", "assessment_goal")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _validate_formula_totals(self):
        total = sum(item.wt_pct for item in self.ingredients)
        if not (99.0 <= total <= 101.0):
            raise ValueError(f"Ingredient wt_pct sum must be within 99-101. Current total: {total:.2f}")

        unique_names = {item.inci_name.lower() for item in self.ingredients}
        if len(unique_names) != len(self.ingredients):
            raise ValueError("Ingredient list contains duplicate INCI names")

        return self


def parse_formula_input(raw_text: str) -> FormulaInput:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Input is empty. Provide a JSON formula object.")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Input must be valid JSON. Parse error: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object, not a list/string/number.")

    try:
        return FormulaInput.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(exc) from exc


def build_agent_input(formula: FormulaInput) -> str:
    return (
        "You must perform a cosmetic formulation rheology and physical stability assessment "
        "using this validated structured input only.\n\n"
        f"FORMULA_JSON:\n{formula.model_dump_json(indent=2)}"
    )


FORMULA_TEMPLATE = """{
  "product_name": "Example Leave-On Emulsion",
  "product_type": "lotion",
  "target_ph": 5.5,
  "ingredients": [
        {"inci_name": "Aqua", "wt_pct": 81.0, "phase": "A"},
    {"inci_name": "Glycerin", "wt_pct": 4.0, "phase": "A"},
    {"inci_name": "Carbomer", "wt_pct": 0.25, "phase": "A"},
    {"inci_name": "Caprylic/Capric Triglyceride", "wt_pct": 8.0, "phase": "B"},
    {"inci_name": "Cetearyl Alcohol", "wt_pct": 3.0, "phase": "B"},
    {"inci_name": "Glyceryl Stearate Citrate", "wt_pct": 2.5, "phase": "B"},
    {"inci_name": "Phenoxyethanol", "wt_pct": 0.9, "phase": "C"},
    {"inci_name": "Parfum", "wt_pct": 0.2, "phase": "C"},
        {"inci_name": "Sodium Hydroxide", "wt_pct": 0.15, "phase": "C"}
  ],
  "process_conditions": {
    "mixing_order": ["Disperse polymer in water", "Heat A/B to 75C", "Emulsify", "Cool to 40C", "Add phase C"],
    "mixing_speed_rpm": 1500,
    "processing_temperature_c": 75.0,
    "homogenization": true
  },
  "packaging": {
    "format": "airless_pump",
    "material": "PP",
    "headspace_pct": 5.0
  },
  "storage_conditions": [
    {"label": "ambient", "temperature_c": 25.0, "duration_weeks": 12, "light_exposure": "indirect"},
    {"label": "accelerated", "temperature_c": 40.0, "duration_weeks": 12, "light_exposure": "dark"}
  ],
  "assessment_goal": "Evaluate rheology and physical stability risks for launch readiness."
}"""