import { useState, useCallback, useEffect } from "react";
import type { FormulaPayload } from "@/types/api";
import { useFormulaForm } from "@/hooks/useFormulaForm";
import FormulaFormFields from "./FormulaFormFields";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Play, Code, FormInput } from "lucide-react";

interface Props {
  onSubmit: (payload: FormulaPayload) => void;
  isLoading: boolean;
}

export default function FormulaEditor({ onSubmit, isLoading }: Props) {
  const {
    payload,
    errors,
    update,
    validate,
    setFromJson,
    ingredientTotal,
    setPayload,
  } = useFormulaForm();
  const [mode, setMode] = useState<"form" | "json">("form");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");
  const [samples, setSamples] = useState<FormulaPayload[]>([]);
  const [selectedSample, setSelectedSample] = useState("0");

  useEffect(() => {
    const loadSamples = async () => {
      try {
        const res = await fetch("/queryExemple.jsonl");
        const raw = await res.text();

        let parsed: unknown = [];
        try {
          parsed = JSON.parse(raw);
        } catch {
          parsed = raw
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => JSON.parse(line));
        }

        if (Array.isArray(parsed)) {
          setSamples(parsed as FormulaPayload[]);
        }
      } catch {
        setSamples([]);
      }
    };

    loadSamples();
  }, []);

  const loadSelectedSample = useCallback(() => {
    const index = Number(selectedSample);
    const sample = samples[index];
    if (!sample) return;

    setPayload(sample);
    setJsonText(JSON.stringify(sample, null, 2));
    setJsonError("");
  }, [samples, selectedSample, setPayload]);

  const handleSubmit = useCallback(() => {
    if (mode === "json") {
      const ok = setFromJson(jsonText);
      if (!ok) return;
      // Re-validate after setting
      try {
        const parsed = JSON.parse(jsonText);
        onSubmit(parsed);
      } catch {
        setJsonError("Invalid JSON");
      }
      return;
    }
    const valid = validate();
    if (valid) onSubmit(valid);
  }, [mode, jsonText, setFromJson, validate, onSubmit]);

  const switchToJson = useCallback(() => {
    setJsonText(JSON.stringify(payload, null, 2));
    setMode("json");
  }, [payload]);

  const switchToForm = useCallback(() => {
    if (jsonText.trim()) {
      setFromJson(jsonText);
    }
    setMode("form");
  }, [jsonText, setFromJson]);

  return (
    <div className="bg-card rounded-lg border border-border">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">
          Formula Input
        </h2>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <select
              value={selectedSample}
              onChange={(e) => setSelectedSample(e.target.value)}
              className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
              disabled={samples.length === 0}
            >
              {samples.map((sample, idx) => (
                <option
                  key={`${sample.product_name}-${idx}`}
                  value={String(idx)}
                >
                  {sample.product_name || `Sample ${idx + 1}`}
                </option>
              ))}
              {samples.length === 0 && (
                <option value="0">No samples found</option>
              )}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={loadSelectedSample}
              disabled={samples.length === 0}
            >
              Load Sample
            </Button>
          </div>
          <Button
            variant={mode === "form" ? "secondary" : "ghost"}
            size="sm"
            onClick={switchToForm}
          >
            <FormInput className="h-3.5 w-3.5 mr-1" /> Form
          </Button>
          <Button
            variant={mode === "json" ? "secondary" : "ghost"}
            size="sm"
            onClick={switchToJson}
          >
            <Code className="h-3.5 w-3.5 mr-1" /> JSON
          </Button>
        </div>
      </div>

      <div className="p-4">
        {mode === "form" ? (
          <FormulaFormFields
            payload={payload}
            errors={errors}
            ingredientTotal={ingredientTotal}
            onUpdate={update}
            setPayload={setPayload}
          />
        ) : (
          <div className="space-y-2">
            <Textarea
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                setJsonError("");
              }}
              rows={20}
              className="font-mono text-xs"
              placeholder="Paste or edit formula JSON..."
            />
            {(jsonError || errors._json) && (
              <p className="text-xs text-destructive">
                {jsonError || errors._json}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="border-t border-border px-4 py-3 flex justify-end">
        <Button onClick={handleSubmit} disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-2" />
          )}
          {isLoading ? "Assessing…" : "Run Assessment"}
        </Button>
      </div>
    </div>
  );
}
