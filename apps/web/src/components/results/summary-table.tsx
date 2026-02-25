"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface GridPointResult {
  start_portfolio: number;
  reserve_years: number;
  loan_amount: number;
  max_e_real_per_year?: number | null;
  e_real_per_year?: number | null;
  p_success_death_weighted: number;
  p_success_to_age_99: number;
  median_max_dd_risky: number;
  median_max_dd_total: number;
  home_equity_remaining_median: number;
  p_any_rm_draw: number;
  rm_balance_end_median: number;
  risky_end_median: number;
  total_net_end_median: number;
  net_worth_end_median: number;
}

interface SummaryTableProps {
  results: GridPointResult[];
  mode: string;
}

function fmt$(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtPct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export function SummaryTable({ results, mode }: SummaryTableProps) {
  if (results.length === 0) {
    return <p className="text-muted-foreground">No results yet.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Portfolio</TableHead>
            <TableHead>Reserve Yrs</TableHead>
            <TableHead>Loan</TableHead>
            <TableHead>
              {mode === "single" ? "E (fixed)" : "Max E"}
            </TableHead>
            <TableHead>Success (DW)</TableHead>
            <TableHead>Success (99)</TableHead>
            <TableHead>DD Risky</TableHead>
            <TableHead>DD Total</TableHead>
            <TableHead>RM Draw %</TableHead>
            <TableHead>Home Equity</TableHead>
            <TableHead>Net Worth</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((r, i) => (
            <TableRow key={i}>
              <TableCell>{fmt$(r.start_portfolio)}</TableCell>
              <TableCell>{r.reserve_years}</TableCell>
              <TableCell>{fmt$(r.loan_amount)}</TableCell>
              <TableCell className="font-medium">
                {fmt$(
                  (mode === "single"
                    ? r.e_real_per_year
                    : r.max_e_real_per_year) ?? 0
                )}
              </TableCell>
              <TableCell>{fmtPct(r.p_success_death_weighted)}</TableCell>
              <TableCell>{fmtPct(r.p_success_to_age_99)}</TableCell>
              <TableCell>{fmtPct(r.median_max_dd_risky)}</TableCell>
              <TableCell>{fmtPct(r.median_max_dd_total)}</TableCell>
              <TableCell>{fmtPct(r.p_any_rm_draw)}</TableCell>
              <TableCell>{fmt$(r.home_equity_remaining_median)}</TableCell>
              <TableCell>{fmt$(r.net_worth_end_median)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
