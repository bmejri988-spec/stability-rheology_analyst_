import type { FormulaPayload } from "@/types/formula";

export const exampleFormula: FormulaPayload = {
  product_name: "HydraSmooth Moisturizing Cream",
  product_type: "O/W Emulsion Cream",
  target_ph: 5.8,
  ingredients: [
    { inci_name: "Aqua", wt_pct: 70.3, phase: "A" },
    { inci_name: "Glycerin", wt_pct: 5.0, phase: "A" },
    { inci_name: "Butylene Glycol", wt_pct: 3.0, phase: "A" },
    { inci_name: "Carbomer 940", wt_pct: 0.3, phase: "A" },
    { inci_name: "Cetearyl Alcohol", wt_pct: 4.0, phase: "B" },
    { inci_name: "Ceteareth-20", wt_pct: 2.0, phase: "B" },
    { inci_name: "Caprylic/Capric Triglyceride", wt_pct: 8.0, phase: "B" },
    { inci_name: "Dimethicone", wt_pct: 2.0, phase: "B" },
    { inci_name: "Shea Butter", wt_pct: 3.0, phase: "B" },
    { inci_name: "Phenoxyethanol", wt_pct: 0.8, phase: "C" },
    { inci_name: "Ethylhexylglycerin", wt_pct: 0.2, phase: "C" },
    { inci_name: "Sodium Hydroxide (10% sol.)", wt_pct: 0.5, phase: "C" },
    { inci_name: "Tocopheryl Acetate", wt_pct: 0.5, phase: "C" },
    { inci_name: "Fragrance", wt_pct: 0.2, phase: "C" },
    { inci_name: "Xanthan Gum", wt_pct: 0.2, phase: "A" },
  ],
  process_conditions: {
    mixing_order: [
      "Heat Phase A to 75°C, disperse Carbomer & Xanthan Gum",
      "Heat Phase B to 75°C, melt fatty components",
      "Add Phase B to Phase A under homogenization",
      "Cool to 40°C, add Phase C ingredients",
      "Neutralize Carbomer with NaOH, adjust pH to 5.8",
      "Homogenize final batch, deaerate",
    ],
    mixing_speed_rpm: 3000,
    processing_temperature_c: 75.0,
    homogenization: true,
  },
  packaging: {
    format: "tube",
    material: "PE/EVOH",
    headspace_pct: 10.0,
  },
  storage_conditions: [
    { label: "Ambient", temperature_c: 25.0, duration_weeks: 12, light_exposure: "indirect" },
    { label: "Accelerated", temperature_c: 40.0, duration_weeks: 8, light_exposure: "none" },
    { label: "Freeze-Thaw Cycling", temperature_c: -10.0, duration_weeks: 4, light_exposure: "none" },
  ],
  assessment_goal:
    "Evaluate emulsion stability risk, predict rheological behavior over shelf-life, identify weak points in the formulation that may lead to phase separation or viscosity drift under accelerated and ambient conditions.",
};
