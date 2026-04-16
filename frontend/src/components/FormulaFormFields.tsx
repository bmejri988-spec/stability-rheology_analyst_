import { useCallback, useMemo } from "react";
import type { FormulaPayload, Ingredient, StorageCondition } from "@/types/api";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";

interface Props {
  payload: FormulaPayload;
  errors: Record<string, string>;
  ingredientTotal: number;
  onUpdate: <K extends keyof FormulaPayload>(key: K, value: FormulaPayload[K]) => void;
  setPayload: React.Dispatch<React.SetStateAction<FormulaPayload>>;
}

function FieldError({ error }: { error?: string }) {
  if (!error) return null;
  return <p className="text-xs text-destructive mt-1">{error}</p>;
}

export default function FormulaFormFields({ payload, errors, ingredientTotal, onUpdate, setPayload }: Props) {
  const addIngredient = useCallback(() => {
    onUpdate("ingredients", [...payload.ingredients, { inci_name: "", wt_pct: 0, phase: "A" }]);
  }, [payload.ingredients, onUpdate]);

  const removeIngredient = useCallback(
    (idx: number) => {
      onUpdate("ingredients", payload.ingredients.filter((_, i) => i !== idx));
    },
    [payload.ingredients, onUpdate]
  );

  const updateIngredient = useCallback(
    (idx: number, field: keyof Ingredient, value: string | number) => {
      const next = payload.ingredients.map((ing, i) => (i === idx ? { ...ing, [field]: value } : ing));
      onUpdate("ingredients", next);
    },
    [payload.ingredients, onUpdate]
  );

  const addStorage = useCallback(() => {
    onUpdate("storage_conditions", [
      ...payload.storage_conditions,
      { label: "", temperature_c: 25, duration_weeks: 4, light_exposure: "none" },
    ]);
  }, [payload.storage_conditions, onUpdate]);

  const removeStorage = useCallback(
    (idx: number) => {
      onUpdate("storage_conditions", payload.storage_conditions.filter((_, i) => i !== idx));
    },
    [payload.storage_conditions, onUpdate]
  );

  const updateStorage = useCallback(
    (idx: number, field: keyof StorageCondition, value: string | number) => {
      const next = payload.storage_conditions.map((sc, i) => (i === idx ? { ...sc, [field]: value } : sc));
      onUpdate("storage_conditions", next);
    },
    [payload.storage_conditions, onUpdate]
  );

  const addMixingStep = useCallback(() => {
    setPayload((p) => ({
      ...p,
      process_conditions: { ...p.process_conditions, mixing_order: [...p.process_conditions.mixing_order, ""] },
    }));
  }, [setPayload]);

  const removeMixingStep = useCallback(
    (idx: number) => {
      setPayload((p) => ({
        ...p,
        process_conditions: {
          ...p.process_conditions,
          mixing_order: p.process_conditions.mixing_order.filter((_, i) => i !== idx),
        },
      }));
    },
    [setPayload]
  );

  const totalColor = useMemo(() => {
    if (ingredientTotal >= 99 && ingredientTotal <= 101) return "bg-success text-success-foreground";
    if (ingredientTotal > 90) return "bg-warning text-warning-foreground";
    return "bg-destructive text-destructive-foreground";
  }, [ingredientTotal]);

  return (
    <div className="space-y-6">
      {/* Basic Info */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground tracking-wide uppercase">Basic Information</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label htmlFor="product_name">Product Name</Label>
            <Input id="product_name" value={payload.product_name} onChange={(e) => onUpdate("product_name", e.target.value)} maxLength={200} />
            <FieldError error={errors["product_name"]} />
          </div>
          <div>
            <Label htmlFor="product_type">Product Type</Label>
            <Input id="product_type" value={payload.product_type} onChange={(e) => onUpdate("product_type", e.target.value)} maxLength={200} />
            <FieldError error={errors["product_type"]} />
          </div>
          <div>
            <Label htmlFor="target_ph">Target pH</Label>
            <Input id="target_ph" type="number" step="0.1" min={0} max={14} value={payload.target_ph} onChange={(e) => onUpdate("target_ph", parseFloat(e.target.value) || 0)} />
            <FieldError error={errors["target_ph"]} />
          </div>
        </div>
      </section>

      {/* Ingredients */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground tracking-wide uppercase">Ingredients</h3>
          <div className="flex items-center gap-2">
            <Badge className={totalColor}>{ingredientTotal.toFixed(1)}%</Badge>
            <Button type="button" variant="outline" size="sm" onClick={addIngredient}>
              <Plus className="h-3.5 w-3.5 mr-1" /> Add
            </Button>
          </div>
        </div>
        <FieldError error={errors["ingredients"]} />
        <div className="space-y-2">
          <div className="grid grid-cols-[1fr_80px_80px_32px] gap-2 text-xs text-muted-foreground font-medium px-1">
            <span>INCI Name</span><span>wt%</span><span>Phase</span><span />
          </div>
          {payload.ingredients.map((ing, idx) => (
            <div key={idx} className="grid grid-cols-[1fr_80px_80px_32px] gap-2 items-start">
              <div>
                <Input value={ing.inci_name} placeholder="e.g. Aqua" onChange={(e) => updateIngredient(idx, "inci_name", e.target.value)} className="text-sm" />
                <FieldError error={errors[`ingredients.${idx}.inci_name`]} />
              </div>
              <div>
                <Input type="number" step="0.1" value={ing.wt_pct} onChange={(e) => updateIngredient(idx, "wt_pct", parseFloat(e.target.value) || 0)} className="text-sm" />
                <FieldError error={errors[`ingredients.${idx}.wt_pct`]} />
              </div>
              <div>
                <Input value={ing.phase} placeholder="A" onChange={(e) => updateIngredient(idx, "phase", e.target.value)} className="text-sm" />
              </div>
              <Button type="button" variant="ghost" size="icon" onClick={() => removeIngredient(idx)} disabled={payload.ingredients.length <= 1} className="h-9 w-8 text-muted-foreground hover:text-destructive">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      </section>

      {/* Process Conditions */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground tracking-wide uppercase">Process Conditions</h3>
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <Label>Mixing Order</Label>
              <Button type="button" variant="outline" size="sm" onClick={addMixingStep}><Plus className="h-3.5 w-3.5 mr-1" /> Step</Button>
            </div>
            <FieldError error={errors["process_conditions.mixing_order"]} />
            {payload.process_conditions.mixing_order.map((step, idx) => (
              <div key={idx} className="flex gap-2 mt-1">
                <span className="text-xs text-muted-foreground pt-2.5 w-5">{idx + 1}.</span>
                <Input value={step} placeholder="Step description" onChange={(e) => {
                  const next = [...payload.process_conditions.mixing_order];
                  next[idx] = e.target.value;
                  setPayload((p) => ({ ...p, process_conditions: { ...p.process_conditions, mixing_order: next } }));
                }} className="text-sm" />
                <Button type="button" variant="ghost" size="icon" onClick={() => removeMixingStep(idx)} disabled={payload.process_conditions.mixing_order.length <= 1} className="h-9 w-8 text-muted-foreground hover:text-destructive shrink-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <Label>Speed (RPM)</Label>
              <Input type="number" value={payload.process_conditions.mixing_speed_rpm} onChange={(e) => setPayload((p) => ({ ...p, process_conditions: { ...p.process_conditions, mixing_speed_rpm: parseInt(e.target.value) || 0 } }))} />
              <FieldError error={errors["process_conditions.mixing_speed_rpm"]} />
            </div>
            <div>
              <Label>Temperature (°C)</Label>
              <Input type="number" value={payload.process_conditions.processing_temperature_c} onChange={(e) => setPayload((p) => ({ ...p, process_conditions: { ...p.process_conditions, processing_temperature_c: parseFloat(e.target.value) || 0 } }))} />
              <FieldError error={errors["process_conditions.processing_temperature_c"]} />
            </div>
            <div className="flex items-center gap-2 pt-5">
              <Switch checked={payload.process_conditions.homogenization} onCheckedChange={(v) => setPayload((p) => ({ ...p, process_conditions: { ...p.process_conditions, homogenization: v } }))} />
              <Label>Homogenization</Label>
            </div>
          </div>
        </div>
      </section>

      {/* Packaging */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground tracking-wide uppercase">Packaging</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <Label>Format</Label>
            <Input value={payload.packaging.format} placeholder="e.g. Tube" onChange={(e) => onUpdate("packaging", { ...payload.packaging, format: e.target.value })} />
            <FieldError error={errors["packaging.format"]} />
          </div>
          <div>
            <Label>Material</Label>
            <Input value={payload.packaging.material} placeholder="e.g. HDPE" onChange={(e) => onUpdate("packaging", { ...payload.packaging, material: e.target.value })} />
            <FieldError error={errors["packaging.material"]} />
          </div>
          <div>
            <Label>Headspace %</Label>
            <Input type="number" min={0} max={100} value={payload.packaging.headspace_pct} onChange={(e) => onUpdate("packaging", { ...payload.packaging, headspace_pct: parseFloat(e.target.value) || 0 })} />
            <FieldError error={errors["packaging.headspace_pct"]} />
          </div>
        </div>
      </section>

      {/* Storage Conditions */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground tracking-wide uppercase">Storage Conditions</h3>
          <Button type="button" variant="outline" size="sm" onClick={addStorage}><Plus className="h-3.5 w-3.5 mr-1" /> Add</Button>
        </div>
        <FieldError error={errors["storage_conditions"]} />
        {payload.storage_conditions.map((sc, idx) => (
          <div key={idx} className="grid grid-cols-[1fr_80px_80px_100px_32px] gap-2 items-start">
            <div>
              <Input value={sc.label} placeholder="Label" onChange={(e) => updateStorage(idx, "label", e.target.value)} className="text-sm" />
              <FieldError error={errors[`storage_conditions.${idx}.label`]} />
            </div>
            <div>
              <Input type="number" value={sc.temperature_c} onChange={(e) => updateStorage(idx, "temperature_c", parseFloat(e.target.value) || 0)} className="text-sm" />
            </div>
            <div>
              <Input type="number" min={1} value={sc.duration_weeks} onChange={(e) => updateStorage(idx, "duration_weeks", parseInt(e.target.value) || 1)} className="text-sm" />
            </div>
            <div>
              <Input value={sc.light_exposure} placeholder="none" onChange={(e) => updateStorage(idx, "light_exposure", e.target.value)} className="text-sm" />
            </div>
            <Button type="button" variant="ghost" size="icon" onClick={() => removeStorage(idx)} disabled={payload.storage_conditions.length <= 1} className="h-9 w-8 text-muted-foreground hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
        <div className="grid grid-cols-[1fr_80px_80px_100px_32px] gap-2 text-[10px] text-muted-foreground px-1 -mt-1">
          <span>Label</span><span>°C</span><span>Weeks</span><span>Light</span><span />
        </div>
      </section>

      {/* Assessment Goal */}
      <section className="space-y-2">
        <Label htmlFor="assessment_goal">Assessment Goal</Label>
        <Textarea id="assessment_goal" value={payload.assessment_goal} onChange={(e) => onUpdate("assessment_goal", e.target.value)} maxLength={2000} rows={3} placeholder="Describe what you want to assess..." />
        <div className="flex justify-between">
          <FieldError error={errors["assessment_goal"]} />
          <span className="text-xs text-muted-foreground">{payload.assessment_goal.length}/2000</span>
        </div>
      </section>
    </div>
  );
}
