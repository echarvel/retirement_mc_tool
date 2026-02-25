# Retirement MC Tool — Web Application Plan

## Context

Converting the existing single-file Python Monte Carlo retirement simulator (`simulate.py`) into a full-stack web application. The current tool runs from the command line with `.env` config and outputs CSV files. The new app will allow users to configure scenarios via a web UI, run simulations, and explore results — with flexible asset types, income streams, and optimization targets.

## Architecture

```
Browser  →  Next.js (Vercel)  →  FastAPI (Railway)  →  NumPy engine
                ↕
         Supabase (Postgres + Auth + Realtime)
```

- **Next.js** (App Router) on **Vercel**: UI + server actions/API routes for simulation orchestration
- **Supabase**: PostgreSQL database + Google OAuth + auto-generated REST API (PostgREST) + Row-Level Security + Realtime subscriptions
- **FastAPI** on **Railway**: Stateless compute service — receives scenario JSON, returns simulation results
- **CRUD is handled by Supabase client directly** — no hand-written API routes for scenario/asset/income management

### Local Development

- `supabase start` — runs full Supabase stack locally (Postgres, Auth, PostgREST, Realtime) in Docker
- `npm run dev` — Next.js with hot reload (port 3000)
- `uvicorn src.main:app --reload` — Python engine (port 8000)

### Production

| Service | Host | Notes |
|---------|------|-------|
| Next.js frontend + server | Vercel (free tier) | Optimized for Next.js, edge functions |
| Python simulation engine | Railway (Docker) | Internal only, not publicly exposed |
| PostgreSQL + Auth + Realtime | Supabase (free tier) | Managed Postgres, Google OAuth, RLS, Realtime |

## Project Structure

```
retirement-mc/
├── supabase/
│   ├── config.toml                 # Supabase local config
│   └── migrations/                 # SQL migrations (schema + RLS policies)
├── apps/
│   ├── web/                        # Next.js + shadcn UI
│   │   ├── src/
│   │   │   ├── app/                # App Router pages
│   │   │   │   ├── auth/           # Auth callback handling
│   │   │   │   ├── scenarios/      # Scenario CRUD pages
│   │   │   │   └── api/
│   │   │   │       └── simulations/ # Only API routes needed: simulation orchestration
│   │   │   ├── lib/
│   │   │   │   ├── supabase/       # Supabase client (browser + server)
│   │   │   │   └── simulation-client.ts  # HTTP client for Python engine
│   │   │   └── components/         # ui/, scenario/, results/, layout/
│   │   └── ...
│   └── engine/                     # Python FastAPI
│       ├── Dockerfile
│       ├── requirements.txt
│       └── src/
│           ├── main.py             # FastAPI app + routes
│           ├── models/             # Pydantic request/response models
│           ├── simulation/         # Modular engine (from simulate.py)
│           │   ├── engine.py       # Core year-by-year loop
│           │   ├── optimizer.py    # Binary search for max E
│           │   ├── returns.py      # Return generators (normal, lognormal, fat-tailed)
│           │   ├── mortality.py    # SSA table + death-weighted success
│           │   ├── income.py       # Flexible income streams
│           │   ├── accounts.py     # take_from helper, account init
│           │   ├── guardrails.py   # Spending cuts logic
│           │   ├── reverse_mortgage.py
│           │   ├── loan.py
│           │   └── rebalancing.py  # Asset group rebalancing
│           └── workers/runner.py   # Background task execution
└── legacy/                         # Backup of current simulate.py + configs
```

**Key difference from previous plan**: No `prisma/` directory, no hand-written CRUD API routes. Supabase handles schema via SQL migrations and CRUD via PostgREST. Only simulation-related API routes remain in Next.js.

## Database Schema (Supabase / PostgreSQL)

All tables live in Supabase-managed Postgres. Schema defined via SQL migrations in `supabase/migrations/`.

| Table | Purpose |
|-------|---------|
| **auth.users** | Managed by Supabase Auth (Google OAuth) — no custom user table needed |
| **scenarios** | Per-user scenario with ~30 core params (guardrails, RM, loan, optimization) |
| **assets** | Per-scenario assets: name, category (risky/non_risky), return params, distribution type, target weight, group assignment |
| **asset_groups** | Named groups with rebalancing flag (e.g., "Aggressive": 80% stocks, 20% gold) |
| **incomes** | Per-scenario income streams: type (SS/annuity/salary/freelancing), amount, start/end age, COLA |
| **sweep_values** | Parameter sweep definitions: which param + JSON array of values |
| **simulation_runs** | Job tracking: status (pending/running/completed/failed), progress, config snapshot |
| **simulation_results** | One row per grid point: success metrics, drawdown medians, terminal balances, optional path data (JSONB) |

### Row-Level Security (RLS)

Every table has RLS policies ensuring users can only access their own data:
```sql
-- Example: scenarios table
ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own scenarios" ON scenarios
  FOR ALL USING (user_id = auth.uid());
```

This eliminates the need for `where: { userId }` in application code — the database enforces it.

## API Design

### Supabase Client (CRUD — no API routes needed)

Scenario, asset, income, group, and sweep CRUD is done directly via the Supabase JS client:
```typescript
// Example: fetch scenarios with related data
const { data } = await supabase
  .from('scenarios')
  .select('*, assets(*), incomes(*), asset_groups(*, assets(*)), sweep_values(*)')
  .order('updated_at', { ascending: false });

// Example: create scenario
const { data } = await supabase
  .from('scenarios')
  .insert({ name: 'My Plan', start_age: 53, ... })
  .select()
  .single();
```

### Next.js API Routes (simulation orchestration only)

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /api/simulations | Start simulation run (creates run, calls Python engine, writes results) |

This is the only API route needed. It:
1. Reads the scenario from Supabase (server-side, using service role key)
2. Creates a `simulation_runs` row (status: pending)
3. Calls the Python engine with the full scenario JSON
4. Writes results back to `simulation_results`
5. Updates `simulation_runs` status

All other reads (simulation status, results, paths) are done directly via Supabase client from the frontend.

### Python FastAPI (internal only — Railway)

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /simulate | Run simulation, return results |
| POST | /simulate/progress | SSE stream with progress per grid point |
| GET | /health | Health check |

Stateless — no database access. Receives JSON, returns JSON.

## Job Execution Flow (with Supabase Realtime)

1. User clicks "Run" → frontend calls `POST /api/simulations` with scenario ID
2. Next.js API route reads full scenario from Supabase, creates `simulation_runs` row (pending)
3. Next.js calls Python engine with scenario JSON
4. Python computes, streams progress via SSE back to Next.js
5. Next.js updates `simulation_runs.progress` in Supabase as results arrive
6. **Frontend subscribes to Realtime** — gets instant push when progress/status changes:
   ```typescript
   supabase.channel('run-progress')
     .on('postgres_changes', {
       event: 'UPDATE',
       table: 'simulation_runs',
       filter: `id=eq.${runId}`,
     }, (payload) => {
       setProgress(payload.new.progress);
       if (payload.new.status === 'completed') fetchResults();
     })
     .subscribe();
   ```
7. On completion, Next.js inserts `simulation_results` rows, sets status = completed
8. Frontend Realtime subscription fires → UI updates instantly (no polling)

## Frontend Pages

| Route | Content |
|-------|---------|
| `/` | Dashboard or sign-in |
| `/scenarios` | Card grid of user's scenarios |
| `/scenarios/new` | Tabbed create form |
| `/scenarios/[id]` | Edit: General, Assets, Income, Guardrails, RM/Loans, Sweep Grid tabs |
| `/scenarios/[id]/results` | Summary table + charts + path explorer |

### Key Components
- **ScenarioForm**: Tabbed editor with dynamic lists for assets/incomes
- **SummaryTable**: Sortable grid of results across sweep dimensions
- **SuccessChart / DrawdownChart / BalanceChart**: Visualization suite
- **PathExplorer**: Select individual MC paths, view year-by-year breakdown
- **SimulationStatus**: Realtime-powered progress bar (no polling)

## Authentication

- **Supabase Auth** with Google OAuth provider
- Configured in Supabase dashboard (or `config.toml` locally)
- Supabase JS client handles sign-in/sign-out/session refresh
- Next.js middleware checks Supabase session for protected routes
- RLS policies use `auth.uid()` to scope all data access
- Python engine has no auth — called only by Next.js server-side

## Implementation Phases

### Phase 1: Foundation
- Monorepo scaffolding (Next.js + shadcn + FastAPI)
- `supabase init` + SQL migrations for core tables (scenarios, simulation_runs, simulation_results)
- RLS policies for all tables
- Supabase Auth with Google OAuth
- Scenario CRUD using Supabase client (no API routes)
- Port `simulate.py` as-is into FastAPI POST endpoint
- Single Next.js API route for simulation orchestration
- Realtime subscription for simulation progress
- End-to-end: sign in → create scenario → run sim → view summary table

### Phase 2: Flexible Assets & Incomes
- Add assets, asset_groups, incomes, sweep_values tables + RLS
- Build editor components (AssetEditor, IncomeEditor, AssetGroupEditor)
- Refactor Python engine into modular `simulation/` package
- Multi-asset return generation (normal, lognormal, fat-tailed)
- Flexible income stream processing
- Asset group rebalancing in simulation loop

### Phase 3: Results Visualization & Path Explorer
- Per-path data capture (opt-in `include_path_data` flag)
- Fan charts (percentile bands over time), histograms, bar charts
- Path explorer with year-by-year account breakdown
- Scenario duplication (Supabase RPC function for deep copy)

### Phase 4: Advanced Optimization & Deployment
- "Minimum starting assets" optimization target
- SSE progress streaming (Python → Next.js)
- Vercel deployment (Next.js)
- Railway deployment (Python engine Docker image)
- Supabase project setup (production)
- CI pipeline (GitHub Actions)
- Error handling, timeouts, retries

## Key Design Rationale

- **Supabase for CRUD + Auth + Realtime**: Eliminates ~15 API route files, provides RLS for data isolation, Realtime for instant progress updates. Significant development time savings.
- **Python stays for compute**: NumPy vectorized 25k-path simulation is the core value; no reason to rewrite in TS.
- **No task queue (Celery/Redis)**: Over-engineering for expected user count. FastAPI + `asyncio.to_thread()` handles concurrency.
- **Realtime over polling**: Instant progress updates, zero wasted HTTP requests. Supabase provides this for free.
- **Path data as JSONB column**: 25k paths × 47 years × N accounts = too many rows. Compressed JSONB loaded on demand.
- **Config snapshot on simulation_runs**: Results stay reproducible even if scenario is edited later.
- **AWS migration path**: Supabase features (Auth, PostgREST, Realtime) would need replacement (Cognito, API Gateway, AppSync), but the Postgres schema + RLS policies transfer directly to RDS. Python engine Docker image deploys to ECS unchanged.

## Verification

After each phase:
1. Run `supabase start` + Next.js + Python natively
2. Sign in with Google, create scenario, run simulation
3. Compare simulation results against original `simulate.py` output for the same parameters (Phase 1 validation)
4. Verify RLS: ensure one user cannot see another's data
5. Verify Realtime: simulation progress updates appear instantly without polling
6. Verify asset/income flexibility produces expected results (Phase 2)
7. Verify charts render correctly and path explorer loads data (Phase 3)
