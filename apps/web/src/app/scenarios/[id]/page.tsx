"use client";

import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScenarioForm, type ScenarioData } from "@/components/scenario/scenario-form";
import { SummaryTable } from "@/components/results/summary-table";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

export default function ScenarioDetailPage() {
  const supabase = createClient();
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [scenario, setScenario] = useState<ScenarioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [simStatus, setSimStatus] = useState<string | null>(null);
  const [results, setResults] = useState<any[]>([]);
  const [latestRunId, setLatestRunId] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load scenario
  useEffect(() => {
    async function load() {
      const { data, error } = await supabase
        .from("scenarios")
        .select("*")
        .eq("id", id)
        .single();

      if (error || !data) {
        toast.error("Scenario not found");
        router.push("/scenarios");
        return;
      }
      setScenario(data as ScenarioData);
      setLoading(false);

      // Load latest run results
      const { data: runs } = await supabase
        .from("simulation_runs")
        .select("id, status")
        .eq("scenario_id", id)
        .order("created_at", { ascending: false })
        .limit(1);

      if (runs && runs.length > 0) {
        setLatestRunId(runs[0].id);
        setSimStatus(runs[0].status);
        if (runs[0].status === "completed") {
          loadResults(runs[0].id);
        }
      }
    }
    load();
  }, [id]);

  async function loadResults(runId: string) {
    const { data } = await supabase
      .from("simulation_results")
      .select("*")
      .eq("run_id", runId)
      .order("start_portfolio")
      .order("reserve_years")
      .order("loan_amount");
    setResults(data ?? []);
  }

  // Auto-save with debounce
  const handleChange = useCallback(
    (updated: ScenarioData) => {
      setScenario(updated);
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(async () => {
        setSaving(true);
        const { id: _id, ...rest } = updated;
        await supabase.from("scenarios").update(rest).eq("id", id);
        setSaving(false);
      }, 800);
    },
    [id]
  );

  // Run simulation
  async function runSimulation() {
    if (!scenario) return;
    setSimulating(true);
    setSimStatus("running");
    setResults([]);

    try {
      const resp = await fetch("/api/simulations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenarioId: id }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text);
      }

      const data = await resp.json();
      setLatestRunId(data.runId);
      setSimStatus("completed");
      loadResults(data.runId);
      toast.success("Simulation completed");
    } catch (e: any) {
      setSimStatus("failed");
      toast.error(`Simulation failed: ${e.message}`);
    } finally {
      setSimulating(false);
    }
  }

  // Subscribe to realtime updates for the run
  useEffect(() => {
    if (!latestRunId || simStatus === "completed" || simStatus === "failed")
      return;

    const channel = supabase
      .channel(`run-${latestRunId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "simulation_runs",
          filter: `id=eq.${latestRunId}`,
        },
        (payload) => {
          const newStatus = payload.new.status;
          setSimStatus(newStatus);
          if (newStatus === "completed") {
            loadResults(latestRunId);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [latestRunId, simStatus]);

  if (loading || !scenario) {
    return <p className="text-muted-foreground">Loading scenario...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => router.push("/scenarios")}>
            Back
          </Button>
          {saving && (
            <Badge variant="secondary">Saving...</Badge>
          )}
        </div>
        <Button
          onClick={runSimulation}
          disabled={simulating}
          size="lg"
        >
          {simulating ? "Running..." : "Run Simulation"}
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <ScenarioForm data={scenario} onChange={handleChange} />
        </CardContent>
      </Card>

      <Separator />

      <div>
        <div className="mb-4 flex items-center gap-3">
          <h2 className="text-xl font-semibold">Results</h2>
          {simStatus && (
            <Badge
              variant={
                simStatus === "completed"
                  ? "default"
                  : simStatus === "running"
                  ? "secondary"
                  : "destructive"
              }
            >
              {simStatus}
            </Badge>
          )}
        </div>

        <SummaryTable results={results} mode={scenario.mode} />
      </div>
    </div>
  );
}
