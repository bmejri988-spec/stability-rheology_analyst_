import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  FlaskConical,
  Moon,
  Sun,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type HealthStatus = "checking" | "healthy" | "unhealthy";

export default function TopBar() {
  const [dark, setDark] = useState(false);
  const [health, setHealth] = useState<HealthStatus>("checking");

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("theme");
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)",
    ).matches;
    const shouldUseDark = savedTheme ? savedTheme === "dark" : prefersDark;
    document.documentElement.classList.toggle("dark", shouldUseDark);
    setDark(shouldUseDark);
  }, []);

  const toggleTheme = () => {
    setDark((current) => {
      const next = !current;
      document.documentElement.classList.toggle("dark", next);
      window.localStorage.setItem("theme", next ? "dark" : "light");
      return next;
    });
  };

  const pingHealth = useCallback(async () => {
    setHealth("checking");
    try {
      await api.health();
      setHealth("healthy");
    } catch {
      setHealth("unhealthy");
    }
  }, []);

  useEffect(() => {
    pingHealth();
    const id = window.setInterval(pingHealth, 30000);
    return () => window.clearInterval(id);
  }, [pingHealth]);

  return (
    <header className="border-b border-border bg-card sticky top-0 z-40">
      <div className="container max-w-5xl flex items-center gap-3 py-3 px-4">
        <FlaskConical className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-bold text-foreground tracking-tight">
          FormulaSense
        </h1>
        <span className="text-xs text-muted-foreground hidden sm:inline">
          Rheology and Stability Assessment
        </span>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={pingHealth}
            className="hidden sm:flex items-center gap-2 rounded-full border border-border/80 bg-card px-3 py-1.5 text-xs"
            title="Backend status"
            type="button"
          >
            {health === "checking" && (
              <span className="h-2 w-2 rounded-full bg-warning animate-pulse" />
            )}
            {health === "healthy" && (
              <CheckCircle2 className="h-3.5 w-3.5 text-success" />
            )}
            {health === "unhealthy" && (
              <AlertCircle className="h-3.5 w-3.5 text-destructive" />
            )}
            <span className="text-muted-foreground">
              {health === "checking"
                ? "Checking"
                : health === "healthy"
                  ? "Connected"
                  : "Offline"}
            </span>
            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
          </button>

          <button
            onClick={pingHealth}
            className="sm:hidden inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/80 bg-card"
            title="Backend status"
            type="button"
          >
            {health === "checking" && (
              <span className="h-2.5 w-2.5 rounded-full bg-warning animate-pulse" />
            )}
            {health === "healthy" && (
              <CheckCircle2 className="h-4 w-4 text-success" />
            )}
            {health === "unhealthy" && (
              <AlertCircle className="h-4 w-4 text-destructive" />
            )}
          </button>

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="h-9 w-9 rounded-full border border-border/70"
            title="Toggle theme"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </header>
  );
}
