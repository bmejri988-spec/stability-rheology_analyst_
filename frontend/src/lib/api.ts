import type { FormulaPayload, AssessmentResponse, HealthResponse } from "@/types/formula";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export async function assessFormula(payload: FormulaPayload): Promise<AssessmentResponse> {
  return request<AssessmentResponse>("/api/assess-formula", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
