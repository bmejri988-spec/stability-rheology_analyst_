import { useState, useCallback } from "react";
import type { FormulaPayload } from "@/types/api";
import { formulaPayloadSchema } from "@/lib/validation";

const defaultPayload: FormulaPayload = {
  product_name: "",
  product_type: "",
  target_ph: 5.5,
  ingredients: [{ inci_name: "", wt_pct: 0, phase: "A" }],
  process_conditions: {
    mixing_order: [""],
    mixing_speed_rpm: 3000,
    processing_temperature_c: 25,
    homogenization: false,
  },
  packaging: { format: "", material: "", headspace_pct: 5 },
  storage_conditions: [{ label: "", temperature_c: 25, duration_weeks: 4, light_exposure: "none" }],
  assessment_goal: "",
};

export function useFormulaForm() {
  const [payload, setPayload] = useState<FormulaPayload>(defaultPayload);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const update = useCallback(<K extends keyof FormulaPayload>(key: K, value: FormulaPayload[K]) => {
    setPayload((p) => ({ ...p, [key]: value }));
  }, []);

  const validate = useCallback((): FormulaPayload | null => {
    const result = formulaPayloadSchema.safeParse(payload);
    if (result.success) {
      setErrors({});
      return result.data as FormulaPayload;
    }
    const errs: Record<string, string> = {};
    for (const issue of result.error.issues) {
      errs[issue.path.join(".")] = issue.message;
    }
    setErrors(errs);
    return null;
  }, [payload]);

  const setFromJson = useCallback((json: string): boolean => {
    try {
      const parsed = JSON.parse(json);
      const result = formulaPayloadSchema.safeParse(parsed);
      if (result.success) {
        setPayload(result.data as FormulaPayload);
        setErrors({});
        return true;
      }
      const errs: Record<string, string> = {};
      for (const issue of result.error.issues) {
        errs[issue.path.join(".")] = issue.message;
      }
      setErrors(errs);
      return false;
    } catch {
      setErrors({ _json: "Invalid JSON" });
      return false;
    }
  }, []);

  const ingredientTotal = payload.ingredients.reduce((s, i) => s + (i.wt_pct || 0), 0);

  return { payload, errors, update, validate, setFromJson, ingredientTotal, setPayload };
}
