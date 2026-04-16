import { useState, useCallback } from "react";
import type { FormulaPayload, AssessmentResponse } from "@/types/api";
import { api } from "@/lib/api";

type Status = "idle" | "loading" | "success" | "error";

export function useAssessment() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<AssessmentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<FormulaPayload | null>(null);

  const submit = useCallback(async (payload: FormulaPayload) => {
    setStatus("loading");
    setError(null);
    setLastPayload(payload);
    try {
      const res = await api.assessFormula(payload);
      setResult(res);
      setStatus("success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("error");
    }
  }, []);

  const retry = useCallback(() => {
    if (lastPayload) submit(lastPayload);
  }, [lastPayload, submit]);

  const reset = useCallback(() => {
    setStatus("idle");
    setError(null);
    setResult(null);
  }, []);

  return { status, result, error, submit, retry, reset, lastPayload };
}
