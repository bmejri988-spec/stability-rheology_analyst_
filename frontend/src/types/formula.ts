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

export interface AssessmentResponse {
  output: string;
  tools: string[];
  coverage_retry: boolean;
  duration_ms?: number;
  trace?: AssessmentTraceItem[];
}

export interface AssessmentTraceItem {
  step: number;
  tool: string;
  input: string;
  output_preview: string;
}

export interface HealthResponse {
  status: string;
}
