import type {
  FormulaPayload,
  AssessmentResponse,
  HealthResponse,
  ChatRequest,
  ChatResponse,
  SafetyAssessmentRequest,
  SafetyAssessmentResponse,
} from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  assessFormula: (payload: FormulaPayload) =>
    request<AssessmentResponse>("/api/assess-formula", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  assessSafety: (payload: SafetyAssessmentRequest) =>
    request<SafetyAssessmentResponse>("/api/assess-safety", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  chat: (data: ChatRequest) =>
    request<ChatResponse>("/api/agent2-chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
