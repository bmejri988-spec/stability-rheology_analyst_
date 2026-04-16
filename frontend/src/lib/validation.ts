import { z } from "zod";

export const ingredientSchema = z.object({
  inci_name: z.string().min(1, "INCI name required"),
  wt_pct: z.number().gt(0, "Must be > 0").lte(100, "Must be ≤ 100"),
  phase: z.string().min(1, "Phase required"),
});

export const processConditionsSchema = z.object({
  mixing_order: z.array(z.string().min(1, "Step cannot be empty")).min(1, "At least 1 step"),
  mixing_speed_rpm: z.number().gt(0, "Must be > 0"),
  processing_temperature_c: z.number().min(-10).max(150),
  homogenization: z.boolean(),
});

export const packagingSchema = z.object({
  format: z.string().min(1, "Format required"),
  material: z.string().min(1, "Material required"),
  headspace_pct: z.number().min(0).max(100),
});

export const storageConditionSchema = z.object({
  label: z.string().min(1, "Label required"),
  temperature_c: z.number().min(-30).max(80),
  duration_weeks: z.number().min(1, "Min 1 week"),
  light_exposure: z.string().min(1, "Light exposure required"),
});

export const formulaPayloadSchema = z.object({
  product_name: z.string().min(1, "Required").max(200),
  product_type: z.string().min(1, "Required").max(200),
  target_ph: z.number().min(0).max(14),
  ingredients: z
    .array(ingredientSchema)
    .min(1, "At least 1 ingredient")
    .refine(
      (items) => {
        const names = items.map((i) => i.inci_name.toLowerCase());
        return new Set(names).size === names.length;
      },
      { message: "Duplicate INCI names not allowed" }
    )
    .refine(
      (items) => {
        const total = items.reduce((s, i) => s + i.wt_pct, 0);
        return total >= 99 && total <= 101;
      },
      { message: "Total wt% must be 99–101" }
    ),
  process_conditions: processConditionsSchema,
  packaging: packagingSchema,
  storage_conditions: z.array(storageConditionSchema).min(1, "At least 1 condition"),
  assessment_goal: z.string().min(1, "Required").max(2000),
});

export type FormulaFormValues = z.infer<typeof formulaPayloadSchema>;
