import FormulaEditor from "@/components/FormulaEditor";
import AssessmentResults from "@/components/AssessmentResults";
import ChatLauncher from "@/components/ChatLauncher";
import TopBar from "@/components/TopBar";
import { useAssessment } from "@/hooks/useAssessment";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Pencil, RefreshCw } from "lucide-react";

const Index = () => {
  const { status, result, error, submit, retry, reset, lastPayload } =
    useAssessment();

  return (
    <div className="min-h-screen bg-background">
      <TopBar />

      <main className="container max-w-5xl px-4 py-6 space-y-6">
        {(status === "idle" || status === "error") && (
          <FormulaEditor onSubmit={submit} isLoading={status === "loading"} />
        )}

        {/* Error state */}
        {status === "error" && (
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 flex items-start gap-3 animate-fade-in">
            <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">
                Assessment failed
              </p>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={retry}>
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Retry
            </Button>
          </div>
        )}

        {/* Loading state */}
        {status === "loading" && (
          <div className="bg-card rounded-lg border border-border animate-fade-in">
            <div className="flex min-h-[420px] flex-col items-center justify-center px-6 py-12 text-center">
              <div className="h-9 w-9 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <p className="mt-4 text-sm text-muted-foreground">
                Running assessment...
              </p>
            </div>
          </div>
        )}

        {/* Results */}
        {status === "success" && result && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={reset}>
                <Pencil className="h-3.5 w-3.5 mr-1" /> Back to edit formula
              </Button>
            </div>
            <AssessmentResults result={result} formula={lastPayload} />
          </div>
        )}
      </main>

      <ChatLauncher />
    </div>
  );
};

export default Index;
