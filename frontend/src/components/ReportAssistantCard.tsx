import { useCallback, useMemo, useState, KeyboardEvent } from "react";
import { Loader2, MessageSquare, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { AssessmentResponse, FormulaPayload } from "@/types/api";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

type ChatMessage = {
  role: "assistant" | "user";
  text: string;
};

interface Props {
  result: AssessmentResponse;
  formula?: FormulaPayload | null;
}

const QUICK_PROMPTS = [
  "What is the main stability risk in this formula?",
  "Which ingredient is most responsible for the rheology behavior?",
  "What should I change first to improve shelf life?",
];

export default function ReportAssistantCard({ result, formula }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const reportContext = useMemo(
    () => buildReportContext(result, formula),
    [result, formula],
  );

  const send = useCallback(
    async (overrideText?: string) => {
      const text = (overrideText ?? input).trim();
      if (!text || loading) return;

      setInput("");
      const userMsg: ChatMessage = { role: "user", text };
      const conversation = [...messages, userMsg];
      setMessages(conversation);
      setLoading(true);

      try {
        const res = await api.chat({
          message: text,
          history: conversation,
          context: reportContext,
        });
        setMessages((current) => [...current, { role: "assistant", text: res.reply }]);
      } catch (error) {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            text: `Error: ${error instanceof Error ? error.message : "Failed to generate a reply"}`,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, messages, reportContext],
  );

  const handleKey = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        void send();
      }
    },
    [send],
  );

  return (
    <section className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-card to-sky-500/5 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Report Assistant
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground">
              Ask follow-up questions about this formula and report
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              This assistant keeps the formula, rheology report, weak points,
              and recommendations in context.
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-background/80 px-3 py-2 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">
            {formula?.product_name || "Current formula"}
          </p>
          <p className="mt-1">
            {formula?.product_type || "Formula analysis"} • {result.tools.length} tools
          </p>
        </div>
      </div>

      {!messages.length && (
        <div className="mt-4 space-y-3 rounded-xl border border-border bg-background/80 p-4">
          <p className="text-sm font-medium text-foreground">
            Try one of these questions:
          </p>
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => void send(prompt)}
                className="rounded-full border border-border bg-muted/40 px-3 py-1.5 text-left text-xs text-foreground transition-colors hover:border-primary/40 hover:bg-primary/5"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {!!messages.length && (
        <div className="mt-4 space-y-3 rounded-xl border border-border bg-background/80 p-4">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm ${message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}>
                {message.role === "assistant" ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{message.text}</ReactMarkdown>
                  </div>
                ) : (
                  <span className="whitespace-pre-wrap">{message.text}</span>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-muted px-3 py-2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex items-end gap-2 rounded-xl border border-border bg-background/90 p-3 shadow-sm">
        <MessageSquare className="mb-2 h-4 w-4 shrink-0 text-muted-foreground" />
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about the report, ingredients, risks, or next changes..."
          rows={2}
          className="min-h-[48px] flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <Button size="icon" onClick={() => void send()} disabled={!input.trim() || loading} className="shrink-0">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </section>
  );
}

function buildReportContext(result: AssessmentResponse, formula?: FormulaPayload | null): string {
  const context = {
    task: "Answer follow-up questions about this specific rheology and stability assessment.",
    formula,
    report: result.report
      ? {
          executive_summary: result.report.executive_summary,
          formulation_architecture: result.report.formulation_architecture,
          ingredient_functional_analysis: result.report.ingredient_functional_analysis,
          rheological_prediction: result.report.rheological_prediction,
          stability_risk_assessment: result.report.stability_risk_assessment,
          process_sensitivity_analysis: result.report.process_sensitivity_analysis,
          packaging_compatibility: result.report.packaging_compatibility,
          sustainability_assessment: result.report.sustainability_assessment,
          accelerated_real_time_stability_prediction: result.report.accelerated_real_time_stability_prediction,
          weak_points_summary: result.report.weak_points_summary,
          optimization_recommendations: result.report.optimization_recommendations,
          final_conclusion: result.report.final_conclusion,
          references: result.report.references,
        }
      : null,
  };

  return JSON.stringify(context, null, 2);
}