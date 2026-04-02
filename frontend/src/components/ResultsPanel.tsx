import { useEffect, useMemo, useState } from "react";
import {
  Copy,
  Download,
  ChevronDown,
  ChevronRight,
  Shield,
  AlertTriangle,
  Lightbulb,
  HelpCircle,
  Clock,
  Wrench,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { AssessmentResponse } from "@/types/formula";
import { parseAssessmentOutput } from "@/lib/validation";
import { motion, AnimatePresence } from "framer-motion";

interface Props {
  result: AssessmentResponse | null;
  error: string | null;
  loading: boolean;
  onRetry: () => void;
  requestTimestamp: string | null;
  rawPayload: unknown | null;
}

export function ResultsPanel({
  result,
  error,
  loading,
  onRetry,
  requestTimestamp,
  rawPayload,
}: Props) {
  const [traceOpen, setTraceOpen] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!loading) {
      setElapsedSeconds(0);
      return;
    }
    const id = setInterval(() => setElapsedSeconds((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, [loading]);

  const loadingMessages = useMemo(() => {
    const sequence = [
      "Validating formula structure and totals",
      "Retrieving internal formulation evidence",
      "Cross-checking ingredient-level chemistry",
      "Running risk synthesis and confidence estimation",
      "Formatting final assessment report",
    ];

    const count = Math.min(sequence.length, 1 + Math.floor(elapsedSeconds / 3));
    return sequence.slice(0, count);
  }, [elapsedSeconds]);

  if (loading) {
    return (
      <div className="flex flex-col h-full p-6 gap-5 text-muted-foreground">
        <div className="flex items-center gap-4">
          <div className="relative h-12 w-12 shrink-0">
            <div className="absolute inset-0 rounded-full border-2 border-primary/20" />
            <div className="absolute inset-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">
              Running Stability & Rheology Assessment
            </p>
            <p className="text-xs mt-1">
              Verbose mode enabled · elapsed {elapsedSeconds}s
            </p>
          </div>
        </div>

        <div className="rounded-md border bg-card p-4">
          <p className="section-title mb-3">Live Execution Notes</p>
          <div className="space-y-2">
            {loadingMessages.map((msg, idx) => (
              <div key={msg} className="flex items-start gap-2 text-xs">
                <span
                  className={`mt-1 h-2 w-2 rounded-full ${idx === loadingMessages.length - 1 ? "bg-primary animate-pulse" : "bg-success"}`}
                />
                <span>{msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 px-6 text-center">
        <AlertTriangle className="h-10 w-10 text-destructive" />
        <div>
          <p className="text-sm font-semibold text-destructive">
            Assessment Failed
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm">{error}</p>
        </div>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCcw className="h-3 w-3 mr-1" /> Retry
        </Button>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground px-6 text-center">
        <Shield className="h-10 w-10 opacity-30" />
        <p className="text-sm">
          Enter a formula and run an assessment to see results here.
        </p>
      </div>
    );
  }

  const { isJson, parsed, reportText, toolsFromOutput } = parseAssessmentOutput(
    result.output,
  );
  const sections = extractSections(reportText);
  const mergedTools = Array.from(
    new Set([...(result.tools || []), ...toolsFromOutput]),
  );

  const copyReport = () => navigator.clipboard.writeText(result.output);
  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "assessment-result.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col h-full"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Assessment Report
          </h2>
          <div className="flex gap-1.5">
            {result.coverage_retry && (
              <Badge
                variant="outline"
                className="text-xs border-warning/40 text-warning"
              >
                Cross-check enforced
              </Badge>
            )}
            {typeof result.duration_ms === "number" && (
              <Badge variant="outline" className="text-xs">
                {(result.duration_ms / 1000).toFixed(1)}s
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={copyReport}
              className="text-xs h-7"
            >
              <Copy className="h-3 w-3 mr-1" /> Copy
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={downloadJson}
              className="text-xs h-7"
            >
              <Download className="h-3 w-3 mr-1" /> JSON
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Tools */}
          {mergedTools.length > 0 && (
            <div className="space-y-1.5">
              <p className="section-title flex items-center gap-1">
                <Wrench className="h-3 w-3" /> Tools Used
              </p>
              <div className="flex flex-wrap gap-1.5">
                {mergedTools.map((t) => (
                  <Badge
                    key={t}
                    variant="secondary"
                    className="text-xs font-mono"
                  >
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Parsed sections or raw */}
          {sections.length > 0 ? (
            sections.map((sec, i) => (
              <ReportSection
                key={i}
                title={sec.title}
                content={sec.content}
                icon={sec.icon}
              />
            ))
          ) : (
            <div className="rounded-md border bg-muted/50 p-4">
              <p className="text-sm whitespace-pre-wrap leading-relaxed">
                {reportText}
              </p>
            </div>
          )}

          {/* Execution Trace */}
          <Collapsible
            open={traceOpen}
            onOpenChange={setTraceOpen}
            className="border rounded-md"
          >
            <CollapsibleTrigger className="flex items-center justify-between w-full px-4 py-2.5 text-xs font-medium text-muted-foreground hover:bg-muted/50 transition-colors">
              <span className="flex items-center gap-1.5">
                <Clock className="h-3 w-3" /> Execution Trace
              </span>
              {traceOpen ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </CollapsibleTrigger>
            <CollapsibleContent className="px-4 pb-3 space-y-2">
              <TraceRow label="Timestamp" value={requestTimestamp || "—"} />
              <TraceRow
                label="Tools"
                value={mergedTools.join(", ") || "None"}
              />
              <TraceRow
                label="Coverage Retry"
                value={result.coverage_retry ? "Yes" : "No"}
              />
              <TraceRow
                label="Output Format"
                value={isJson ? "JSON" : "Text"}
              />
              {typeof result.duration_ms === "number" && (
                <TraceRow
                  label="Duration"
                  value={`${(result.duration_ms / 1000).toFixed(2)}s`}
                />
              )}

              {result.trace && result.trace.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">
                    Tool Call Trace
                  </p>
                  <div className="space-y-2">
                    {result.trace.map((item) => (
                      <div
                        key={`${item.step}-${item.tool}`}
                        className="rounded border bg-muted/50 p-2"
                      >
                        <p className="text-xs font-semibold">
                          Step {item.step}: {item.tool}
                        </p>
                        <p className="text-xs mt-1">
                          <span className="font-medium">input:</span>{" "}
                          {item.input}
                        </p>
                        <p className="text-xs mt-1 whitespace-pre-wrap">
                          <span className="font-medium">output:</span>{" "}
                          {item.output_preview}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  Raw Response
                </p>
                <div className="relative">
                  <pre className="text-xs font-mono bg-muted rounded-md p-3 overflow-x-auto max-h-60 whitespace-pre-wrap">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-1 right-1 h-6 text-xs"
                    onClick={() =>
                      navigator.clipboard.writeText(
                        JSON.stringify(result, null, 2),
                      )
                    }
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              {rawPayload && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">
                    Request Payload
                  </p>
                  <div className="relative">
                    <pre className="text-xs font-mono bg-muted rounded-md p-3 overflow-x-auto max-h-60 whitespace-pre-wrap">
                      {JSON.stringify(rawPayload, null, 2)}
                    </pre>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-1 right-1 h-6 text-xs"
                      onClick={() =>
                        navigator.clipboard.writeText(
                          JSON.stringify(rawPayload, null, 2),
                        )
                      }
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              )}

              {isJson && parsed && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">
                    Parsed Output JSON
                  </p>
                  <pre className="text-xs font-mono bg-muted rounded-md p-3 overflow-x-auto max-h-60 whitespace-pre-wrap">
                    {JSON.stringify(parsed, null, 2)}
                  </pre>
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function TraceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3 text-xs">
      <span className="font-medium text-muted-foreground w-28 shrink-0">
        {label}
      </span>
      <span className="font-mono">{value}</span>
    </div>
  );
}

interface Section {
  title: string;
  content: string;
  icon: React.ReactNode;
}

function extractSections(text: string): Section[] {
  const sections: Section[] = [];
  const patterns: { re: RegExp; title: string; icon: React.ReactNode }[] = [
    {
      re: /(?:overall\s*risk\s*summary|risk\s*summary)[:\s]*([\s\S]*?)(?=(?:key\s*risk|recommended|confidence|data\s*gap|$))/i,
      title: "Overall Risk Summary",
      icon: <Shield className="h-4 w-4 text-warning" />,
    },
    {
      re: /(?:key\s*risk\s*drivers?)[:\s]*([\s\S]*?)(?=(?:recommended|confidence|data\s*gap|$))/i,
      title: "Key Risk Drivers",
      icon: <AlertTriangle className="h-4 w-4 text-destructive" />,
    },
    {
      re: /(?:recommended\s*actions?)[:\s]*([\s\S]*?)(?=(?:confidence|data\s*gap|$))/i,
      title: "Recommended Actions",
      icon: <Lightbulb className="h-4 w-4 text-accent" />,
    },
    {
      re: /(?:confidence|data\s*gaps?)[:\s]*([\s\S]*?)$/i,
      title: "Confidence & Data Gaps",
      icon: <HelpCircle className="h-4 w-4 text-muted-foreground" />,
    },
  ];
  for (const p of patterns) {
    const m = text.match(p.re);
    if (m?.[1]?.trim()) {
      sections.push({ title: p.title, content: m[1].trim(), icon: p.icon });
    }
  }
  if (sections.length === 0 && text.length > 0) {
    sections.push({
      title: "Assessment Output",
      content: text,
      icon: <Shield className="h-4 w-4 text-primary" />,
    });
  }
  return sections;
}

function ReportSection({ title, content, icon }: Section) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-md border p-4 space-y-2"
    >
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      <p className="text-sm leading-relaxed text-card-foreground whitespace-pre-wrap">
        {content}
      </p>
    </motion.div>
  );
}
