import { z } from "zod";

export const ingredientSchema = z.object({
  inci_name: z.string().min(1, "INCI name is required"),
  wt_pct: z.number().gt(0, "Must be > 0").max(100, "Must be ≤ 100"),
  phase: z.string().min(1, "Phase is required"),
});

export const storageConditionSchema = z.object({
  label: z.string().min(1, "Label is required"),
  temperature_c: z.number().min(-30, "Min -30°C").max(80, "Max 80°C"),
  duration_weeks: z.number().min(1, "Min 1 week"),
  light_exposure: z.string().min(1, "Required"),
});

export const formulaSchema = z.object({
  product_name: z.string().min(1, "Product name is required").max(200),
  product_type: z.string().min(1, "Product type is required").max(200),
  target_ph: z.number().min(0, "pH must be ≥ 0").max(14, "pH must be ≤ 14"),
  ingredients: z.array(ingredientSchema).min(1, "At least one ingredient is required"),
  process_conditions: z.object({
    mixing_order: z.array(z.string().min(1)).min(1, "At least one step required"),
    mixing_speed_rpm: z.number().gt(0, "Must be > 0 RPM"),
    processing_temperature_c: z.number().min(-10, "Min -10°C").max(150, "Max 150°C"),
    homogenization: z.boolean(),
  }),
  packaging: z.object({
    format: z.string().min(1, "Required"),
    material: z.string().min(1, "Required"),
    headspace_pct: z.number().min(0).max(100),
  }),
  storage_conditions: z.array(storageConditionSchema).min(1, "At least one storage condition"),
  assessment_goal: z.string().min(1, "Assessment goal is required").max(2000),
}).superRefine((data, ctx) => {
  const total = data.ingredients.reduce((sum, ingredient) => sum + ingredient.wt_pct, 0);
  if (total < 99 || total > 101) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["ingredients"],
      message: `Ingredient wt_pct total must be within 99-101. Current total: ${total.toFixed(2)}`,
    });
  }

  const seen = new Set<string>();
  for (let index = 0; index < data.ingredients.length; index += 1) {
    const normalized = data.ingredients[index].inci_name.trim().toLowerCase();
    if (!normalized) {
      continue;
    }
    if (seen.has(normalized)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["ingredients", index, "inci_name"],
        message: "Duplicate INCI name is not allowed",
      });
    }
    seen.add(normalized);
  }
});

export type ValidationErrors = Record<string, string>;

type ParsedAssessmentOutput = {
  isJson: boolean;
  parsed?: unknown;
  text: string;
  reportText: string;
  toolsFromOutput: string[];
};

export function validateFormula(data: unknown): { success: true; data: z.infer<typeof formulaSchema> } | { success: false; errors: ValidationErrors } {
  const result = formulaSchema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  }
  const errors: ValidationErrors = {};
  for (const issue of result.error.issues) {
    const path = issue.path.join(".");
    errors[path] = issue.message;
  }
  return { success: false, errors };
}

export function parseAssessmentOutput(output: string): ParsedAssessmentOutput {
  const trimmed = output.trim();

  const fromParsed = (parsed: unknown): ParsedAssessmentOutput => {
    const asRecord = parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null;
    const responseText = typeof asRecord?.response === "string" ? asRecord.response.trim() : null;
    const summaryText = typeof asRecord?.summary === "string" ? asRecord.summary.trim() : null;
    const reportText = responseText || summaryText || JSON.stringify(parsed, null, 2);
    const tools = Array.isArray(asRecord?.tools_used)
      ? asRecord.tools_used.filter((v): v is string => typeof v === "string")
      : [];

    return {
      isJson: true,
      parsed,
      text: trimmed,
      reportText,
      toolsFromOutput: tools,
    };
  };

  try {
    const parsed = JSON.parse(trimmed);
    return fromParsed(parsed);
  } catch {
    // Try to extract JSON from markdown code blocks
    const jsonMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[1].trim());
        return fromParsed(parsed);
      } catch { /* not json */ }
    }
    return { isJson: false, text: trimmed, reportText: trimmed, toolsFromOutput: [] };
  }
}
