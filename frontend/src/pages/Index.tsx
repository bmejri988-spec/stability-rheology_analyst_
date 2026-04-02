import { useState, useCallback } from "react";
import { TopBar } from "@/components/TopBar";
import { FormulaBuilder } from "@/components/FormulaBuilder";
import { ResultsPanel } from "@/components/ResultsPanel";
import { assessFormula } from "@/lib/api";
import type { FormulaPayload, AssessmentResponse } from "@/types/formula";

export default function Index() {
  const [result, setResult] = useState<AssessmentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [timestamp, setTimestamp] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<FormulaPayload | null>(null);

  const handleSubmit = useCallback(async (payload: FormulaPayload) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setLastPayload(payload);
    setTimestamp(new Date().toISOString());
    try {
      const res = await assessFormula(payload);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRetry = () => {
    if (lastPayload) handleSubmit(lastPayload);
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <TopBar />
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        <div className="lg:w-1/2 xl:w-[45%] border-r overflow-hidden flex flex-col">
          <FormulaBuilder onSubmit={handleSubmit} loading={loading} />
        </div>
        <div className="lg:w-1/2 xl:w-[55%] overflow-hidden flex flex-col">
          <ResultsPanel
            result={result}
            error={error}
            loading={loading}
            onRetry={handleRetry}
            requestTimestamp={timestamp}
            rawPayload={lastPayload}
          />
        </div>
      </div>
    </div>
  );
}
