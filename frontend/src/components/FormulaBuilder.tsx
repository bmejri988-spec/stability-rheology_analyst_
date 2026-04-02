import { useState, useMemo } from "react";
import { Plus, Trash2, FlaskConical, FileJson, Play, CheckCircle, Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import CodeEditor from "@uiw/react-textarea-code-editor";
import type { FormulaPayload, Ingredient, StorageCondition } from "@/types/formula";
import { validateFormula, type ValidationErrors } from "@/lib/validation";
import { exampleFormula } from "@/lib/exampleFormula";

interface Props {
  onSubmit: (payload: FormulaPayload) => void;
  loading: boolean;
}

const emptyIngredient = (): Ingredient => ({ inci_name: "", wt_pct: 0, phase: "A" });
const emptyStorage = (): StorageCondition => ({ label: "", temperature_c: 25, duration_weeks: 12, light_exposure: "indirect" });

const defaultFormula: FormulaPayload = {
  product_name: "",
  product_type: "",
  target_ph: 5.5,
  ingredients: [emptyIngredient()],
  process_conditions: {
    mixing_order: [""],
    mixing_speed_rpm: 3000,
    processing_temperature_c: 75,
    homogenization: true,
  },
  packaging: { format: "tube", material: "PE", headspace_pct: 10 },
  storage_conditions: [emptyStorage()],
  assessment_goal: "",
};

export function FormulaBuilder({ onSubmit, loading }: Props) {
  const [mode, setMode] = useState<"form" | "json">("form");
  const [formula, setFormula] = useState<FormulaPayload>(defaultFormula);
  const [rawJson, setRawJson] = useState("");
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [validated, setValidated] = useState(false);

  const totalWt = useMemo(() => formula.ingredients.reduce((s, i) => s + (i.wt_pct || 0), 0), [formula.ingredients]);

  const updateField = <K extends keyof FormulaPayload>(key: K, val: FormulaPayload[K]) => {
    setFormula((f) => ({ ...f, [key]: val }));
    setValidated(false);
  };

  const updateIngredient = (idx: number, field: keyof Ingredient, val: string | number) => {
    const next = [...formula.ingredients];
    next[idx] = { ...next[idx], [field]: val };
    updateField("ingredients", next);
  };

  const updateStorage = (idx: number, field: keyof StorageCondition, val: string | number) => {
    const next = [...formula.storage_conditions];
    next[idx] = { ...next[idx], [field]: val };
    updateField("storage_conditions", next);
  };

  const updateMixingStep = (idx: number, val: string) => {
    const next = [...formula.process_conditions.mixing_order];
    next[idx] = val;
    updateField("process_conditions", { ...formula.process_conditions, mixing_order: next });
  };

  const loadExample = () => {
    setFormula(exampleFormula);
    setRawJson(JSON.stringify(exampleFormula, null, 2));
    setErrors({});
    setValidated(false);
  };

  const doValidate = (): boolean => {
    const source = mode === "json" ? (() => { try { return JSON.parse(rawJson); } catch { return null; } })() : formula;
    if (source === null) {
      setErrors({ _json: "Invalid JSON" });
      setValidated(true);
      return false;
    }
    const vResult = validateFormula(source);
    if (vResult.success === true) {
      setErrors({});
      setValidated(true);
      if (mode === "json") setFormula(vResult.data);
      return true;
    }
    const failResult = vResult as { success: false; errors: ValidationErrors };
    setErrors(failResult.errors);
    setValidated(true);
    return false;
  };

  const handleSubmit = () => {
    if (doValidate()) {
      const source = mode === "json" ? JSON.parse(rawJson) : formula;
      onSubmit(source);
    }
  };

  const errorList = Object.entries(errors);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-primary" />
          Formula Builder
        </h2>
        <Button variant="outline" size="sm" onClick={loadExample} className="text-xs">
          <Upload className="h-3 w-3 mr-1" /> Load Example
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        <Tabs value={mode} onValueChange={(v) => { setMode(v as "form" | "json"); if (v === "json") setRawJson(JSON.stringify(formula, null, 2)); }}>
          <TabsList className="w-full">
            <TabsTrigger value="form" className="flex-1 text-xs">Form Mode</TabsTrigger>
            <TabsTrigger value="json" className="flex-1 text-xs">
              <FileJson className="h-3 w-3 mr-1" /> Raw JSON
            </TabsTrigger>
          </TabsList>

          <TabsContent value="json" className="mt-3">
            <CodeEditor
              value={rawJson}
              language="json"
              onChange={(e) => { setRawJson(e.target.value); setValidated(false); }}
              padding={16}
              className="rounded-md border text-sm font-mono min-h-[400px]"
              style={{ backgroundColor: "hsl(var(--muted))", color: "hsl(var(--foreground))" }}
            />
          </TabsContent>

          <TabsContent value="form" className="mt-3 space-y-5">
            {/* Basic Info */}
            <section className="space-y-3">
              <p className="section-title">Product Information</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Product Name</Label>
                  <Input value={formula.product_name} onChange={(e) => updateField("product_name", e.target.value)} placeholder="e.g. HydraSmooth Cream" className="text-sm" />
                  {errors.product_name && <p className="text-xs text-destructive mt-1">{errors.product_name}</p>}
                </div>
                <div>
                  <Label className="text-xs">Product Type</Label>
                  <Input value={formula.product_type} onChange={(e) => updateField("product_type", e.target.value)} placeholder="e.g. O/W Emulsion" className="text-sm" />
                </div>
                <div>
                  <Label className="text-xs">Target pH</Label>
                  <Input type="number" step={0.1} min={0} max={14} value={formula.target_ph} onChange={(e) => updateField("target_ph", parseFloat(e.target.value) || 0)} className="text-sm" />
                </div>
              </div>
            </section>

            {/* Ingredients */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="section-title">Ingredients</p>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs font-mono">
                    Σ {totalWt.toFixed(1)}%
                  </Badge>
                  <Button variant="outline" size="sm" onClick={() => updateField("ingredients", [...formula.ingredients, emptyIngredient()])} className="text-xs h-7">
                    <Plus className="h-3 w-3 mr-1" /> Add
                  </Button>
                </div>
              </div>
              <div className="border rounded-md overflow-hidden">
                <div className="grid grid-cols-[1fr_80px_60px_32px] gap-2 px-3 py-2 bg-muted text-xs font-medium text-muted-foreground">
                  <span>INCI Name</span><span>wt%</span><span>Phase</span><span />
                </div>
                {formula.ingredients.map((ing, i) => (
                  <div key={i} className="grid grid-cols-[1fr_80px_60px_32px] gap-2 px-3 py-1.5 border-t items-center">
                    <Input value={ing.inci_name} onChange={(e) => updateIngredient(i, "inci_name", e.target.value)} className="h-8 text-xs" placeholder="Aqua" />
                    <Input type="number" step={0.1} value={ing.wt_pct} onChange={(e) => updateIngredient(i, "wt_pct", parseFloat(e.target.value) || 0)} className="h-8 text-xs font-mono" />
                    <Input value={ing.phase} onChange={(e) => updateIngredient(i, "phase", e.target.value)} className="h-8 text-xs" placeholder="A" />
                    <button onClick={() => { if (formula.ingredients.length > 1) updateField("ingredients", formula.ingredients.filter((_, j) => j !== i)); }} className="text-muted-foreground hover:text-destructive transition-colors">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {/* Process Conditions */}
            <section className="space-y-3">
              <p className="section-title">Process Conditions</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <Label className="text-xs">Mixing Speed (RPM)</Label>
                  <Input type="number" value={formula.process_conditions.mixing_speed_rpm} onChange={(e) => updateField("process_conditions", { ...formula.process_conditions, mixing_speed_rpm: parseInt(e.target.value) || 0 })} className="text-sm" />
                </div>
                <div>
                  <Label className="text-xs">Temperature (°C)</Label>
                  <Input type="number" value={formula.process_conditions.processing_temperature_c} onChange={(e) => updateField("process_conditions", { ...formula.process_conditions, processing_temperature_c: parseFloat(e.target.value) || 0 })} className="text-sm" />
                </div>
                <div className="flex items-end gap-2 pb-1">
                  <Switch checked={formula.process_conditions.homogenization} onCheckedChange={(c) => updateField("process_conditions", { ...formula.process_conditions, homogenization: c })} />
                  <Label className="text-xs">Homogenization</Label>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Mixing Order Steps</Label>
                  <Button variant="ghost" size="sm" onClick={() => updateField("process_conditions", { ...formula.process_conditions, mixing_order: [...formula.process_conditions.mixing_order, ""] })} className="text-xs h-6">
                    <Plus className="h-3 w-3 mr-1" /> Step
                  </Button>
                </div>
                {formula.process_conditions.mixing_order.map((step, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-xs text-muted-foreground mt-2 w-5 shrink-0">{i + 1}.</span>
                    <Input value={step} onChange={(e) => updateMixingStep(i, e.target.value)} className="text-xs" placeholder="Describe step..." />
                    {formula.process_conditions.mixing_order.length > 1 && (
                      <button onClick={() => updateField("process_conditions", { ...formula.process_conditions, mixing_order: formula.process_conditions.mixing_order.filter((_, j) => j !== i) })} className="text-muted-foreground hover:text-destructive">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* Packaging */}
            <section className="space-y-3">
              <p className="section-title">Packaging</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <Label className="text-xs">Format</Label>
                  <Input value={formula.packaging.format} onChange={(e) => updateField("packaging", { ...formula.packaging, format: e.target.value })} className="text-sm" placeholder="tube, jar, pump..." />
                </div>
                <div>
                  <Label className="text-xs">Material</Label>
                  <Input value={formula.packaging.material} onChange={(e) => updateField("packaging", { ...formula.packaging, material: e.target.value })} className="text-sm" />
                </div>
                <div>
                  <Label className="text-xs">Headspace %</Label>
                  <Input type="number" step={0.5} value={formula.packaging.headspace_pct} onChange={(e) => updateField("packaging", { ...formula.packaging, headspace_pct: parseFloat(e.target.value) || 0 })} className="text-sm" />
                </div>
              </div>
            </section>

            {/* Storage */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="section-title">Storage Conditions</p>
                <Button variant="outline" size="sm" onClick={() => updateField("storage_conditions", [...formula.storage_conditions, emptyStorage()])} className="text-xs h-7">
                  <Plus className="h-3 w-3 mr-1" /> Add
                </Button>
              </div>
              <div className="border rounded-md overflow-hidden">
                <div className="grid grid-cols-[1fr_70px_70px_90px_32px] gap-2 px-3 py-2 bg-muted text-xs font-medium text-muted-foreground">
                  <span>Label</span><span>°C</span><span>Weeks</span><span>Light</span><span />
                </div>
                {formula.storage_conditions.map((sc, i) => (
                  <div key={i} className="grid grid-cols-[1fr_70px_70px_90px_32px] gap-2 px-3 py-1.5 border-t items-center">
                    <Input value={sc.label} onChange={(e) => updateStorage(i, "label", e.target.value)} className="h-8 text-xs" placeholder="Ambient" />
                    <Input type="number" value={sc.temperature_c} onChange={(e) => updateStorage(i, "temperature_c", parseFloat(e.target.value) || 0)} className="h-8 text-xs font-mono" />
                    <Input type="number" value={sc.duration_weeks} onChange={(e) => updateStorage(i, "duration_weeks", parseInt(e.target.value) || 0)} className="h-8 text-xs font-mono" />
                    <Input value={sc.light_exposure} onChange={(e) => updateStorage(i, "light_exposure", e.target.value)} className="h-8 text-xs" placeholder="none" />
                    <button onClick={() => { if (formula.storage_conditions.length > 1) updateField("storage_conditions", formula.storage_conditions.filter((_, j) => j !== i)); }} className="text-muted-foreground hover:text-destructive">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {/* Assessment Goal */}
            <section className="space-y-2">
              <p className="section-title">Assessment Goal</p>
              <Textarea value={formula.assessment_goal} onChange={(e) => updateField("assessment_goal", e.target.value)} placeholder="Describe what you want the agent to evaluate..." rows={3} className="text-sm" />
            </section>
          </TabsContent>
        </Tabs>

        {/* Validation Errors */}
        {validated && errorList.length > 0 && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 space-y-1">
            <p className="text-xs font-semibold text-destructive">Validation Errors</p>
            {errorList.map(([path, msg]) => (
              <p key={path} className="text-xs text-destructive/80">
                <span className="font-mono">{path}</span>: {msg}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="border-t p-4 flex gap-2">
        <Button variant="outline" size="sm" onClick={doValidate} className="text-xs">
          <CheckCircle className="h-3 w-3 mr-1" /> Validate
        </Button>
        <Button size="sm" onClick={handleSubmit} disabled={loading} className="flex-1 text-xs">
          {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Play className="h-3 w-3 mr-1" />}
          Run Stability & Rheology Check
        </Button>
      </div>
    </div>
  );
}
