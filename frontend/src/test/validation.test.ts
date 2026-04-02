import { describe, it, expect } from "vitest";
import { validateFormula, parseAssessmentOutput } from "@/lib/validation";
import { exampleFormula } from "@/lib/exampleFormula";

describe("validateFormula", () => {
  it("accepts a valid formula", () => {
    const result = validateFormula(exampleFormula);
    expect(result.success).toBe(true);
  });

  it("rejects empty product_name", () => {
    const result = validateFormula({ ...exampleFormula, product_name: "" });
    expect(result.success).toBe(false);
    if (result.success === false) {
      expect(result.errors).toHaveProperty("product_name");
    }
  });

  it("rejects pH out of range", () => {
    const result = validateFormula({ ...exampleFormula, target_ph: 15 });
    expect(result.success).toBe(false);
  });

  it("rejects empty ingredients", () => {
    const result = validateFormula({ ...exampleFormula, ingredients: [] });
    expect(result.success).toBe(false);
  });

  it("rejects ingredient with wt_pct > 100", () => {
    const result = validateFormula({
      ...exampleFormula,
      ingredients: [{ inci_name: "Aqua", wt_pct: 101, phase: "A" }],
    });
    expect(result.success).toBe(false);
  });
});

describe("parseAssessmentOutput", () => {
  it("detects plain text", () => {
    const r = parseAssessmentOutput("This is a plain report.");
    expect(r.isJson).toBe(false);
    expect(r.text).toBe("This is a plain report.");
  });

  it("detects JSON output", () => {
    const r = parseAssessmentOutput('{"risk": "low"}');
    expect(r.isJson).toBe(true);
    expect(r.parsed).toEqual({ risk: "low" });
  });

  it("extracts JSON from markdown code block", () => {
    const r = parseAssessmentOutput('Some text\n```json\n{"risk": "high"}\n```');
    expect(r.isJson).toBe(true);
    expect(r.parsed).toEqual({ risk: "high" });
  });
});
