import { useMemo, useState, useCallback, useEffect } from "react";
import type {
  AssessmentResponse,
  StructuredAssessmentReport,
  SafetyAssessmentResponse,
  SafetyReport,
  ReferenceItemReport,
  IngredientFunctionalRowReport,
  StabilityPredictionRowReport,
  FormulaPayload,
} from "@/types/api";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import ReportAssistantCard from "@/components/ReportAssistantCard";
import {
  Copy,
  Download,
  ChevronDown,
  ChevronRight,
  Check,
  FileText,
} from "lucide-react";

interface Props {
  result: AssessmentResponse;
  formula?: FormulaPayload | null;
}

type ReportViewMode = "main" | "safety";
type SafetyLoadStatus = "idle" | "starting" | "polling" | "success" | "error";

export default function AssessmentResults({ result, formula }: Props) {
  const [showRaw, setShowRaw] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [viewMode, setViewMode] = useState<ReportViewMode>("main");
  const [copied, setCopied] = useState(false);
  const [safetyStatus, setSafetyStatus] = useState<SafetyLoadStatus>("idle");
  const [safetyResult, setSafetyResult] =
    useState<SafetyAssessmentResponse | null>(null);
  const [safetyError, setSafetyError] = useState<string>("");
  const [safetyJobId, setSafetyJobId] = useState<string>("");

  const report = result.report ?? parseReportFromOutput(result.output);

  useEffect(() => {
    if (viewMode !== "safety") return;
    if (!report) return;
    if (safetyStatus !== "idle") return;

    const urls = collectReferenceUrls(report);
    setSafetyStatus("starting");
    setSafetyError("");

    api
      .assessSafety({
        report,
        formula: formula ?? undefined,
        urls,
        strictConstrainToURLs: false,
      })
      .then((res) => {
        const status = (res.firecrawl_status || "").toLowerCase();
        const jobId = res.firecrawl_job_id || "";
        setSafetyResult(res);
        if (status === "completed") {
          setSafetyStatus("success");
          return;
        }
        if (jobId) {
          setSafetyJobId(jobId);
          setSafetyStatus("polling");
          return;
        }
        setSafetyStatus("error");
        setSafetyError("Safety job did not provide a pollable job id.");
      })
      .catch((err) => {
        setSafetyError(
          err instanceof Error ? err.message : "Failed to load safety report",
        );
        setSafetyStatus("error");
      });
  }, [viewMode, report, safetyStatus, formula]);

  useEffect(() => {
    if (viewMode !== "safety") return;
    if (safetyStatus !== "polling") return;
    if (!safetyJobId) return;

    let cancelled = false;
    const startedAt = Date.now();
    const MAX_POLL_MS = 120000;
    const tick = async () => {
      if (Date.now() - startedAt > MAX_POLL_MS) {
        setSafetyStatus("error");
        setSafetyError("Safety polling timed out after 120 seconds.");
        return;
      }

      try {
        const res = await api.assessSafety({ jobId: safetyJobId });
        if (cancelled) return;
        setSafetyResult((prev) => {
          const merged = {
            ...(prev || {}),
            ...res,
            warning: res.warning || "",
          } as SafetyAssessmentResponse;
          return merged;
        });

        const status = (res.firecrawl_status || "").toLowerCase();
        if (status === "completed") {
          setSafetyStatus("success");
          return;
        }
        if (
          [
            "failed",
            "cancelled",
            "canceled",
            "request_error",
            "invalid_json",
          ].includes(status)
        ) {
          setSafetyStatus("error");
          setSafetyError(
            res.firecrawl_message
              ? `Safety job ended with status: ${status}. ${res.firecrawl_message}`
              : `Safety job ended with status: ${status}`,
          );
          return;
        }

        // Keep polling while processing/pending/queued.
        window.setTimeout(() => {
          if (!cancelled) {
            void tick();
          }
        }, 2000);
      } catch (err) {
        if (cancelled) return;
        setSafetyStatus("error");
        setSafetyError(
          err instanceof Error ? err.message : "Safety polling failed",
        );
      }
    };

    void tick();
    return () => {
      cancelled = true;
    };
  }, [viewMode, safetyStatus, safetyJobId]);

  const copyOutput = useCallback(() => {
    navigator.clipboard.writeText(result.output);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }, [result.output]);

  const downloadJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rheology-assessment.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  const fallbackText = useMemo(
    () => cleanEscapedText(result.output),
    [result.output],
  );

  return (
    <div className="bg-card rounded-lg border border-border animate-slide-up">
      <div className="px-4 py-4 border-b border-border bg-gradient-to-r from-primary/5 to-transparent">
        <h2 className="text-lg font-bold text-foreground">
          {viewMode === "main"
            ? "Rheology & Stability Assessment Report"
            : "Safety & Sustainability Report"}
        </h2>
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          <Badge variant="outline">Duration: {result.duration_ms}ms</Badge>
          <Badge variant="outline">Tools: {result.tools.length}</Badge>
          {result.coverage_retry && (
            <Badge className="bg-warning text-warning-foreground">Retry</Badge>
          )}
        </div>
        <div className="mt-3 inline-flex rounded-md border border-border bg-background p-1 text-xs">
          <Button
            variant={viewMode === "main" ? "default" : "ghost"}
            size="sm"
            className="h-8 px-3"
            onClick={() => setViewMode("main")}
          >
            Main report
          </Button>
          <Button
            variant={viewMode === "safety" ? "default" : "ghost"}
            size="sm"
            className="h-8 px-3"
            onClick={() => setViewMode("safety")}
          >
            Safety report
          </Button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        <div className="bg-primary/5 border border-primary/20 rounded-md p-3 text-sm">
          <span className="font-medium">Tools used:</span>{" "}
          {result.tools.join(", ") || "None"}
        </div>

        {report ? (
          viewMode === "main" ? (
            <div className="space-y-4">
              <MainReportView report={report} />
              <ReportAssistantCard result={result} formula={formula} />
            </div>
          ) : (
            <SafetyReportView
              report={report}
              formula={formula}
              safetyReport={safetyResult?.safety_report}
              safetySummary={safetyResult?.summary}
              safetyUsedUrls={safetyResult?.used_urls || []}
              status={safetyStatus}
              error={safetyError}
              warning={safetyResult?.warning || ""}
              firecrawlStatus={safetyResult?.firecrawl_status || ""}
              firecrawlVerbose={safetyResult?.firecrawl_verbose}
              firecrawlStatusUrl={safetyResult?.firecrawl_status_url || ""}
              firecrawlMessage={safetyResult?.firecrawl_message || ""}
            />
          )
        ) : (
          <FallbackTextView text={fallbackText} />
        )}

        <ExpandablePanel
          title={`Execution Trace (${result.trace?.length || 0} steps)`}
          open={showTrace}
          onToggle={() => setShowTrace((v) => !v)}
        >
          <div className="space-y-2">
            {(result.trace || []).map((step) => (
              <div
                key={step.step}
                className="border border-border rounded p-2 text-xs bg-muted/30"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-muted-foreground">
                    #{step.step}
                  </span>
                  <Badge variant="outline" className="text-[10px]">
                    {step.tool}
                  </Badge>
                </div>
                <div className="text-muted-foreground">
                  <span className="font-medium">Input:</span> {step.input}
                </div>
                <div className="text-foreground mt-1">
                  <span className="font-medium">Output:</span>{" "}
                  {step.output_preview}
                </div>
              </div>
            ))}
          </div>
        </ExpandablePanel>

        <ExpandablePanel
          title="Raw Response"
          open={showRaw}
          onToggle={() => setShowRaw((v) => !v)}
        >
          <pre className="bg-muted rounded p-3 text-xs font-mono overflow-x-auto max-h-64">
            {JSON.stringify(result, null, 2)}
          </pre>
        </ExpandablePanel>
      </div>

      <div className="border-t border-border px-4 py-3 flex gap-2">
        <Button variant="outline" size="sm" onClick={copyOutput}>
          {copied ? (
            <Check className="h-3.5 w-3.5 mr-1" />
          ) : (
            <Copy className="h-3.5 w-3.5 mr-1" />
          )}
          {copied ? "Copied" : "Copy Report"}
        </Button>
        <Button variant="outline" size="sm" onClick={downloadJson}>
          <Download className="h-3.5 w-3.5 mr-1" /> Download JSON
        </Button>
      </div>
    </div>
  );
}

function MainReportView({ report }: { report: StructuredAssessmentReport }) {
  const refs = report.references || [];
  return (
    <div className="space-y-4">
      <Section title="1. Executive Summary">
        <Bullet
          label="Brief stability conclusion"
          value={report.executive_summary?.brief_stability_conclusion}
        />
        <BulletList
          label="Key risks overview"
          items={report.executive_summary?.key_risks_overview}
        />
        <Bullet
          label="Expected shelf-life behavior"
          value={report.executive_summary?.expected_shelf_life_behavior}
        />
        <Bullet
          label="Risk Level"
          value={report.executive_summary?.risk_level}
        />
        <Bullet
          label="Confidence Level"
          value={report.executive_summary?.confidence_level}
        />
        <Bullet
          label="Launch Decision"
          value={report.executive_summary?.launch_decision}
        />
      </Section>

      <Section title="2. Formulation Architecture">
        <Bullet
          label="Emulsion type"
          value={report.formulation_architecture?.emulsion_type}
        />
        <BulletList
          label="Stabilization mechanisms"
          items={report.formulation_architecture?.stabilization_mechanisms}
        />
        <BulletList
          label="Key structuring agents"
          items={report.formulation_architecture?.key_structuring_agents}
        />
      </Section>

      <Section title="3. Ingredient Functional Analysis">
        <SimpleTable
          headers={["Ingredient", "Function", "Stability Role"]}
          rows={(report.ingredient_functional_analysis || []).map(
            (r: IngredientFunctionalRowReport) => [
              r.ingredient || "n/a",
              r.function || "n/a",
              r.stability_role || "n/a",
            ],
          )}
        />
      </Section>

      <Section title="4. Rheological Prediction">
        <Bullet
          label="Flow type"
          value={report.rheological_prediction?.flow_type}
        />
        <Bullet
          label="Yield stress presence"
          value={report.rheological_prediction?.yield_stress_presence}
        />
        <Bullet
          label="Thixotropy behavior"
          value={report.rheological_prediction?.thixotropy_behavior}
        />
        <Bullet
          label="Viscosity profile under shear"
          value={report.rheological_prediction?.viscosity_profile_under_shear}
        />
      </Section>

      <Section title="5. Stability Risk Assessment">
        <BulletList
          label="Polymer instability risks"
          items={report.stability_risk_assessment?.polymer_instability_risks}
        />
        <BulletList
          label="Emulsion breakdown risks"
          items={report.stability_risk_assessment?.emulsion_breakdown_risks}
        />
        <BulletList
          label="Thermal sensitivity"
          items={report.stability_risk_assessment?.thermal_sensitivity}
        />
        <BulletList
          label="pH sensitivity"
          items={report.stability_risk_assessment?.ph_sensitivity}
        />
        <BulletList
          label="Electrolyte sensitivity"
          items={report.stability_risk_assessment?.electrolyte_sensitivity}
        />
      </Section>

      <Section title="6. Process Sensitivity Analysis">
        <BulletList
          label="Mixing order impact"
          items={report.process_sensitivity_analysis?.mixing_order_impact}
        />
        <BulletList
          label="Temperature sensitivity"
          items={report.process_sensitivity_analysis?.temperature_sensitivity}
        />
        <BulletList
          label="Homogenization effects"
          items={report.process_sensitivity_analysis?.homogenization_effects}
        />
        <BulletList
          label="Neutralization risks"
          items={report.process_sensitivity_analysis?.neutralization_risks}
        />
      </Section>

      <Section title="7. Packaging Compatibility">
        <BulletList
          label="Material compatibility"
          items={report.packaging_compatibility?.material_compatibility}
        />
        <BulletList
          label="Oxygen / water barrier"
          items={report.packaging_compatibility?.oxygen_water_barrier}
        />
        <BulletList
          label="Headspace effects"
          items={report.packaging_compatibility?.headspace_effects}
        />
      </Section>

      <Section title="8. Relevant Risk Context">
        <BulletList
          label="Stability risks tied to safety decisions"
          items={report.stability_risk_assessment?.emulsion_breakdown_risks}
        />
        <BulletList
          label="Process factors that can increase waste"
          items={report.process_sensitivity_analysis?.homogenization_effects}
        />
        <BulletList
          label="Packaging compatibility notes"
          items={report.packaging_compatibility?.material_compatibility}
        />
      </Section>

      <Section title="9. Accelerated & Real-Time Stability Prediction">
        <SimpleTable
          headers={["Condition", "Prediction", "Risk Level"]}
          rows={(report.accelerated_real_time_stability_prediction || []).map(
            (r: StabilityPredictionRowReport) => [
              r.condition || "n/a",
              r.prediction || "n/a",
              r.risk_level || "Medium",
            ],
          )}
        />
      </Section>

      <Section title="10. Weak Points Summary">
        <BulletList items={report.weak_points_summary} />
      </Section>

      <Section title="11. Optimization Recommendations">
        <BulletList
          label="Ingredient adjustments"
          items={report.optimization_recommendations?.ingredient_adjustments}
        />
        <BulletList
          label="Process improvements"
          items={report.optimization_recommendations?.process_improvements}
        />
        <BulletList
          label="Stability enhancers"
          items={report.optimization_recommendations?.stability_enhancers}
        />
      </Section>

      <Section title="12. Final Conclusion">
        <p className="text-sm">
          {report.final_conclusion || "No conclusion available."}
        </p>
      </Section>

      <Section title="References">
        <div className="space-y-2">
          {refs.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No references provided.
            </p>
          )}
          {refs.map((ref: ReferenceItemReport, idx: number) => (
            <div
              key={`${ref.title || "ref"}-${idx}`}
              className="border border-border rounded p-2 bg-muted/30"
            >
              <div className="flex items-start gap-2">
                <FileText className="h-4 w-4 mt-0.5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">
                    {ref.title || "Untitled reference"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(ref.year || "n/a") + " • " + (ref.source_type || "paper")}
                  </p>
                  {ref.relevance && (
                    <p className="text-xs mt-1">Relevance: {ref.relevance}</p>
                  )}
                  {ref.source_file && (
                    <p className="text-xs">Source File: {ref.source_file}</p>
                  )}
                  {ref.pages && <p className="text-xs">Pages: {ref.pages}</p>}
                  {ref.url && (
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary underline"
                    >
                      {ref.url}
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function SafetyReportView({
  report,
  formula,
  safetyReport,
  safetySummary,
  safetyUsedUrls,
  status,
  error,
  warning,
  firecrawlStatus,
  firecrawlVerbose,
  firecrawlStatusUrl,
  firecrawlMessage,
}: {
  report: StructuredAssessmentReport;
  formula?: FormulaPayload | null;
  safetyReport?: SafetyReport;
  safetySummary?: string;
  safetyUsedUrls: string[];
  status: SafetyLoadStatus;
  error: string;
  warning: string;
  firecrawlStatus: string;
  firecrawlVerbose?: unknown;
  firecrawlStatusUrl: string;
  firecrawlMessage: string;
}) {
  const safety = normalizeSafetyReport(
    safetyReport || report.sustainability_assessment,
  );
  const showWarning =
    !!warning &&
    status !== "error" &&
    firecrawlStatus !== "failed" &&
    firecrawlStatus !== "cancelled" &&
    firecrawlStatus !== "canceled";
  const verboseText = useMemo(() => {
    if (firecrawlVerbose == null) return "";
    try {
      return JSON.stringify(firecrawlVerbose, null, 2);
    } catch {
      return String(firecrawlVerbose);
    }
  }, [firecrawlVerbose]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-500/20 bg-gradient-to-br from-emerald-500/10 via-card to-sky-500/10 p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-background/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-700">
              Safety Intelligence
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Environmental safety and sustainability review
              </h3>
              <p className="text-sm text-muted-foreground">
                Generated from the submitted formula and the latest rheology /
                stability report.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            <StatChip label="Provider" value="Firecrawl" />
            <StatChip label="Status" value={firecrawlStatus || status} />
            <StatChip label="Sources" value={String(safetyUsedUrls.length)} />
            <StatChip
              label="Confidence"
              value={safety?.confidence_level || "n/a"}
            />
          </div>
        </div>
        {!!firecrawlStatusUrl && (
          <a
            href={firecrawlStatusUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex text-xs font-medium text-primary hover:underline"
          >
            Open crawl status endpoint
          </a>
        )}
      </div>

      {(status === "starting" || status === "polling") && (
        <div className="bg-muted/40 border border-border rounded-md p-3 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            <span>
              {status === "starting"
                ? "Starting external safety assessment..."
                : "External safety assessment in progress..."}
              {!!firecrawlStatus && ` (status: ${firecrawlStatus})`}
            </span>
          </div>
        </div>
      )}
      {status === "error" && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-md p-3 text-sm">
          External safety assessment failed: {error}. Showing local safety
          summary.
          {!!firecrawlMessage && (
            <div className="mt-2 rounded-md border border-destructive/20 bg-background/70 p-2 text-xs text-foreground">
              Firecrawl message: {firecrawlMessage}
            </div>
          )}
        </div>
      )}
      {showWarning && (
        <div className="bg-warning/10 border border-warning/30 rounded-md p-3 text-sm">
          {warning}
          {!!firecrawlStatus && <span> (status: {firecrawlStatus})</span>}
        </div>
      )}

      <Section title="Safety Summary">
        {!!safetySummary && (
          <div className="rounded-lg border border-border bg-muted/20 p-3 text-sm leading-relaxed text-foreground">
            {safetySummary}
          </div>
        )}
        {!!safety?.confidence_level && (
          <p className="text-sm text-muted-foreground">
            Confidence level:{" "}
            <span className="text-foreground">{safety.confidence_level}</span>
          </p>
        )}
        <div className="grid gap-3 md:grid-cols-2">
          <InsightCard
            title="Ingredient origin and renewability"
            items={safety?.ingredient_origin_and_renewability}
          />
          <InsightCard
            title="Biodegradability and ecotoxicity"
            items={safety?.biodegradability_and_ecotoxicity}
          />
          <InsightCard
            title="Packaging and waste impact"
            items={safety?.packaging_and_waste_impact}
          />
          <InsightCard
            title="Process and energy footprint"
            items={safety?.process_and_energy_footprint}
          />
          <div className="md:col-span-2">
            <InsightCard
              title="Safer or lower-impact alternatives"
              items={safety?.safer_or_lower_impact_alternatives}
            />
          </div>
        </div>
      </Section>

      {!!(safety?.references || []).length && (
        <Section title="Safety References">
          <div className="space-y-2">
            {(safety.references || []).map((ref, idx) => (
              <div
                key={`${ref.url || ref.title || idx}`}
                className="rounded-lg border border-border bg-muted/20 p-3"
              >
                <p className="text-sm font-medium text-foreground">
                  {ref.title || `Reference ${idx + 1}`}
                </p>
                {!!ref.relevance && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {ref.relevance}
                  </p>
                )}
                {!!ref.url && (
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex text-xs font-medium text-primary hover:underline"
                  >
                    Open source
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {!!safetyUsedUrls.length && (
        <Section title="External Sources Used">
          <div className="flex flex-wrap gap-2">
            {safetyUsedUrls.map((url) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-border bg-background px-3 py-1 text-xs text-foreground transition-colors hover:border-primary/40 hover:bg-primary/5"
              >
                {url}
              </a>
            ))}
          </div>
        </Section>
      )}

      <VerbosePanel text={verboseText} />

      {!hasSafetyContent(safety, safetySummary) && status === "success" && (
        <Section title="Safety Output">
          <p className="text-sm text-muted-foreground">
            Safety agent completed but returned sparse fields. Check the raw
            payload for the full crawl response.
          </p>
        </Section>
      )}
    </div>
  );
}

function VerbosePanel({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;

  return (
    <Section title="Crawl Verbose / Raw Payload">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="text-sm font-medium text-primary hover:underline"
      >
        {open ? "Hide raw payload" : "Show raw payload"}
      </button>
      {open && (
        <pre className="max-h-[420px] overflow-auto rounded-lg border border-border bg-slate-950 p-3 text-xs leading-relaxed text-slate-100">
          {text}
        </pre>
      )}
    </Section>
  );
}

function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-background/80 px-3 py-2 shadow-sm backdrop-blur">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

function InsightCard({ title, items }: { title: string; items?: string[] }) {
  const list = (items || []).filter(Boolean);
  return (
    <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <div className="mt-2 space-y-1">
        {list.length ? (
          list.map((item, idx) => (
            <p
              key={`${title}-${idx}`}
              className="text-sm text-muted-foreground"
            >
              <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-primary align-middle" />
              {item}
            </p>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">n/a</p>
        )}
      </div>
    </div>
  );
}

function normalizeSafetyReport(raw?: SafetyReport): SafetyReport {
  if (!raw || typeof raw !== "object") return {};

  const asAny = raw as Record<string, unknown>;
  const asStringList = (value: unknown): string[] => {
    if (Array.isArray(value))
      return value.map((v) => String(v)).filter(Boolean);
    if (typeof value === "string" && value.trim()) return [value.trim()];
    return [];
  };
  const pick = (primary: unknown, fallback: unknown): string[] => {
    const p = asStringList(primary);
    return p.length ? p : asStringList(fallback);
  };

  return {
    ingredient_origin_and_renewability: pick(
      asAny.ingredient_origin_and_renewability,
      asAny.risk_signals,
    ),
    biodegradability_and_ecotoxicity: pick(
      asAny.biodegradability_and_ecotoxicity,
      asAny.uncertainties,
    ),
    packaging_and_waste_impact: asStringList(asAny.packaging_and_waste_impact),
    process_and_energy_footprint: asStringList(
      asAny.process_and_energy_footprint,
    ),
    safer_or_lower_impact_alternatives: pick(
      asAny.safer_or_lower_impact_alternatives,
      asAny.alternatives,
    ),
    confidence_level:
      typeof asAny.confidence_level === "string"
        ? asAny.confidence_level
        : undefined,
    references: Array.isArray(asAny.references)
      ? (asAny.references as Array<Record<string, unknown>>).map((r) => ({
          title: typeof r.title === "string" ? r.title : undefined,
          url: typeof r.url === "string" ? r.url : undefined,
          relevance: typeof r.relevance === "string" ? r.relevance : undefined,
        }))
      : undefined,
  };
}

function hasSafetyContent(safety: SafetyReport, summary?: string): boolean {
  const fields = [
    safety.ingredient_origin_and_renewability,
    safety.biodegradability_and_ecotoxicity,
    safety.packaging_and_waste_impact,
    safety.process_and_energy_footprint,
    safety.safer_or_lower_impact_alternatives,
  ];
  return (
    fields.some((arr) => (arr || []).length > 0) ||
    !!(summary && summary.trim())
  );
}

function collectReferenceUrls(report: StructuredAssessmentReport): string[] {
  const urls: string[] = [];
  for (const ref of report.references || []) {
    const url = (ref.url || "").trim();
    if (!url) continue;
    if (!url.startsWith("http://") && !url.startsWith("https://")) continue;
    if (!urls.includes(url)) urls.push(url);
  }
  return urls;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-border rounded-md p-4 bg-card">
      <h3 className="text-sm font-semibold mb-3 pb-2 border-b border-border">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Bullet({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <p className="text-sm">
      - {label}: {value}
    </p>
  );
}

function BulletList({ label, items }: { label?: string; items?: string[] }) {
  const list = (items || []).filter(Boolean);
  if (list.length === 0)
    return label ? (
      <p className="text-sm">- {label}: n/a</p>
    ) : (
      <p className="text-sm">- n/a</p>
    );
  return (
    <div>
      {label && <p className="text-sm">- {label}:</p>}
      {list.map((item, idx) => (
        <p key={`${item}-${idx}`} className="text-sm ml-4">
          - {item}
        </p>
      ))}
    </div>
  );
}

function SimpleTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: string[][];
}) {
  const safeRows = rows.length ? rows : [["n/a", "n/a", "n/a"]];
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {headers.map((header) => (
              <th
                key={header}
                className="px-3 py-2 text-left font-semibold text-xs uppercase tracking-wider"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {safeRows.map((row, ridx) => (
            <tr key={ridx} className="border-b border-border/50">
              {row.map((cell, cidx) => (
                <td key={cidx} className="px-3 py-2 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExpandablePanel({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        {open ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        {title}
      </button>
      {open && <div className="mt-2 ml-4">{children}</div>}
    </div>
  );
}

function FallbackTextView({ text }: { text: string }) {
  return (
    <div className="border border-border rounded-md p-4 bg-card">
      <h3 className="text-sm font-semibold mb-2">Report</h3>
      <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">
        {text}
      </pre>
    </div>
  );
}

function parseReportFromOutput(
  output: string,
): StructuredAssessmentReport | null {
  const trimmed = output.trim();
  if (!trimmed) return null;

  const candidates: string[] = [trimmed];
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  if (fenced?.[1]) candidates.push(fenced[1].trim());

  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate) as Record<string, unknown>;
      const report = parsed.report;
      if (report && typeof report === "object")
        return report as StructuredAssessmentReport;
    } catch {
      const start = candidate.indexOf("{");
      const end = candidate.lastIndexOf("}");
      if (start >= 0 && end > start) {
        try {
          const parsed = JSON.parse(candidate.slice(start, end + 1)) as Record<
            string,
            unknown
          >;
          const report = parsed.report;
          if (report && typeof report === "object")
            return report as StructuredAssessmentReport;
        } catch {
          // no-op
        }
      }
    }
  }

  return null;
}

function cleanEscapedText(text: string): string {
  return text
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
