export interface Ingredient {
  inci_name: string;
  wt_pct: number;
  phase: string;
}

export interface ProcessConditions {
  mixing_order: string[];
  mixing_speed_rpm: number;
  processing_temperature_c: number;
  homogenization: boolean;
}

export interface Packaging {
  format: string;
  material: string;
  headspace_pct: number;
}

export interface StorageCondition {
  label: string;
  temperature_c: number;
  duration_weeks: number;
  light_exposure: string;
}

export interface FormulaPayload {
  product_name: string;
  product_type: string;
  target_ph: number;
  ingredients: Ingredient[];
  process_conditions: ProcessConditions;
  packaging: Packaging;
  storage_conditions: StorageCondition[];
  assessment_goal: string;
}

export interface TraceStep {
  step: number;
  tool: string;
  input: string;
  output_preview: string;
}

export interface ExecutiveSummaryReport {
  brief_stability_conclusion?: string;
  key_risks_overview?: string[];
  expected_shelf_life_behavior?: string;
  risk_level?: string;
  confidence_level?: string;
  launch_decision?: string;
}

export interface FormulationArchitectureReport {
  emulsion_type?: string;
  stabilization_mechanisms?: string[];
  key_structuring_agents?: string[];
}

export interface IngredientFunctionalRowReport {
  ingredient?: string;
  function?: string;
  stability_role?: string;
}

export interface RheologicalPredictionReport {
  flow_type?: string;
  yield_stress_presence?: string;
  thixotropy_behavior?: string;
  viscosity_profile_under_shear?: string;
}

export interface StabilityRiskAssessmentReport {
  polymer_instability_risks?: string[];
  emulsion_breakdown_risks?: string[];
  thermal_sensitivity?: string[];
  ph_sensitivity?: string[];
  electrolyte_sensitivity?: string[];
}

export interface ProcessSensitivityReport {
  mixing_order_impact?: string[];
  temperature_sensitivity?: string[];
  homogenization_effects?: string[];
  neutralization_risks?: string[];
}

export interface PackagingCompatibilityReport {
  material_compatibility?: string[];
  oxygen_water_barrier?: string[];
  headspace_effects?: string[];
}

export interface SustainabilityAssessmentReport {
  ingredient_origin_and_renewability?: string[];
  biodegradability_and_ecotoxicity?: string[];
  packaging_and_waste_impact?: string[];
  process_and_energy_footprint?: string[];
  safer_or_lower_impact_alternatives?: string[];
}

export interface StabilityPredictionRowReport {
  condition?: string;
  prediction?: string;
  risk_level?: string;
}

export interface OptimizationRecommendationsReport {
  ingredient_adjustments?: string[];
  process_improvements?: string[];
  stability_enhancers?: string[];
}

export interface ReferenceItemReport {
  title?: string;
  year?: string;
  source_type?: string;
  relevance?: string;
  source_file?: string;
  pages?: string;
  url?: string;
}

export interface StructuredAssessmentReport {
  executive_summary?: ExecutiveSummaryReport;
  formulation_architecture?: FormulationArchitectureReport;
  ingredient_functional_analysis?: IngredientFunctionalRowReport[];
  rheological_prediction?: RheologicalPredictionReport;
  stability_risk_assessment?: StabilityRiskAssessmentReport;
  process_sensitivity_analysis?: ProcessSensitivityReport;
  packaging_compatibility?: PackagingCompatibilityReport;
  sustainability_assessment?: SustainabilityAssessmentReport;
  accelerated_real_time_stability_prediction?: StabilityPredictionRowReport[];
  weak_points_summary?: string[];
  optimization_recommendations?: OptimizationRecommendationsReport;
  final_conclusion?: string;
  references?: ReferenceItemReport[];
}

export interface AssessmentResponse {
  output: string;
  report?: StructuredAssessmentReport | null;
  tools: string[];
  coverage_retry: boolean;
  duration_ms: number;
  trace: TraceStep[];
}

export interface SafetyReferenceReport {
  title?: string;
  url?: string;
  relevance?: string;
}

export interface SafetyReport {
  ingredient_origin_and_renewability?: string[];
  biodegradability_and_ecotoxicity?: string[];
  packaging_and_waste_impact?: string[];
  process_and_energy_footprint?: string[];
  safer_or_lower_impact_alternatives?: string[];
  confidence_level?: string;
  references?: SafetyReferenceReport[];
}

export interface SafetyAssessmentRequest {
  report?: StructuredAssessmentReport;
  formula?: FormulaPayload;
  jobId?: string;
  urls?: string[];
  maxCredits?: number;
  strictConstrainToURLs?: boolean;
  model?: string;
}

export interface SafetyAssessmentResponse {
  safety_report: SafetyReport;
  summary: string;
  provider: string;
  duration_ms: number;
  used_urls: string[];
  firecrawl_status?: string;
  firecrawl_job_id?: string;
  firecrawl_status_url?: string;
  firecrawl_verbose?: unknown;
  firecrawl_message?: string;
  warning?: string;
}

export interface HealthResponse {
  status: string;
}

export interface ChatMessage {
  role: "assistant" | "user";
  text: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  duration_ms: number;
}
