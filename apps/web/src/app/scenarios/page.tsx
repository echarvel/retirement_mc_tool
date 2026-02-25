"use client";

import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Scenario {
  id: string;
  name: string;
  mode: string;
  start_age: number;
  start_portfolios: number[];
  updated_at: string;
}

export default function ScenariosPage() {
  const supabase = createClient();
  const router = useRouter();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadScenarios();
  }, []);

  async function loadScenarios() {
    const { data } = await supabase
      .from("scenarios")
      .select("id, name, mode, start_age, start_portfolios, updated_at")
      .order("updated_at", { ascending: false });
    setScenarios(data ?? []);
    setLoading(false);
  }

  async function createScenario() {
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    const { data, error } = await supabase
      .from("scenarios")
      .insert({ user_id: user.id, name: "New Scenario" })
      .select("id")
      .single();

    if (data && !error) {
      router.push(`/scenarios/${data.id}`);
    }
  }

  async function deleteScenario(id: string) {
    await supabase.from("scenarios").delete().eq("id", id);
    setScenarios((prev) => prev.filter((s) => s.id !== id));
  }

  function formatCurrency(n: number) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(n);
  }

  if (loading) {
    return <p className="text-muted-foreground">Loading scenarios...</p>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Scenarios</h1>
        <Button onClick={createScenario}>New Scenario</Button>
      </div>

      {scenarios.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">
              No scenarios yet. Create one to get started.
            </p>
            <Button onClick={createScenario}>Create Scenario</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {scenarios.map((s) => (
            <Card
              key={s.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/scenarios/${s.id}`)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">{s.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-1 text-sm text-muted-foreground">
                  <span>
                    Mode: {s.mode} | Age: {s.start_age}
                  </span>
                  <span>
                    Portfolio:{" "}
                    {(s.start_portfolios as number[])
                      .map(formatCurrency)
                      .join(", ")}
                  </span>
                  <span>
                    Updated: {new Date(s.updated_at).toLocaleDateString()}
                  </span>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  className="mt-3"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteScenario(s.id);
                  }}
                >
                  Delete
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
