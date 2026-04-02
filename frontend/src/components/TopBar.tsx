import { useState, useEffect, useCallback } from "react";
import { Moon, Sun, Activity, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { checkHealth } from "@/lib/api";

type HealthStatus = "checking" | "healthy" | "unhealthy";

export function TopBar() {
  const [dark, setDark] = useState(false);
  const [health, setHealth] = useState<HealthStatus>("checking");

  const toggleTheme = () => {
    setDark((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
  };

  const ping = useCallback(async () => {
    setHealth("checking");
    try {
      await checkHealth();
      setHealth("healthy");
    } catch {
      setHealth("unhealthy");
    }
  }, []);

  useEffect(() => {
    ping();
    const id = setInterval(ping, 30_000);
    return () => clearInterval(id);
  }, [ping]);

  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-4 md:px-6 shrink-0">
      <div className="flex items-center gap-3">
        <Activity className="h-5 w-5 text-primary" />
        <h1 className="text-base font-semibold tracking-tight">
          Cosmetic Rheology & Stability Agent
        </h1>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={ping}
          className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md border bg-muted hover:bg-muted/80 transition-colors"
          title="Backend status"
        >
          {health === "checking" && (
            <span className="h-2 w-2 rounded-full bg-warning animate-pulse-slow" />
          )}
          {health === "healthy" && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
          {health === "unhealthy" && <AlertCircle className="h-3.5 w-3.5 text-destructive" />}
          <span className="hidden sm:inline text-muted-foreground">
            {health === "checking" ? "Checking…" : health === "healthy" ? "Connected" : "Offline"}
          </span>
        </button>
        <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8">
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
