# Retirement MC Tool — Project Specifications

## 1. Overview

A web application for running Monte Carlo retirement simulations. Users configure scenarios with flexible assets, income streams, and spending rules, then run simulations to find optimal withdrawal strategies. Built on top of an existing Python simulation engine (`simulate.py`).

## 2. Architecture

```
Browser  →  Next.js (TypeScript)  →  FastAPI (Python)  →  NumPy engine
                  ↕
            PostgreSQL (Docker)
```

| Layer | Technology | Role |
|-------|-----------|------|
| Frontend + API | Next.js (App Router) + shadcn UI | UI, CRUD, auth, job orchestration |
| Simulation Engine | Python FastAPI | Stateless compute — receives scenario JSON, returns results |
| Database | PostgreSQL (Prisma ORM) | Users, scenarios, simulation runs, results |
| Auth | Auth.js (NextAuth v5) + Google OAuth | User authentication, JWT sessions |
| Deployment | Railway (Docker images) | All services hosted; Python engine on internal network |

### Local Development

- **PostgreSQL**: Docker container
- **Next.js + Python**: Run natively for fast iteration and hot reload

### Production (Railway)

- Three services: `web` (Next.js), `engine` (FastAPI), `db` (Railway Postgres plugin)
- Python engine is internal-only (not publicly exposed)
- All services deployed as Docker images

## 3. Feature Requirements

### 3.1 Flexible Income Types

Multiple income sources per scenario, each with:
- **Type**: social security, annuity, salary, freelancing, other
- **Amount**: annual amount in real (inflation-adjusted) dollars
- **Start/end age**: when income begins and ends (end is optional for lifetime income)
- **COLA rate**: real growth rate (0 = inflation-matched)

### 3.2 Risky Assets

Multiple risky asset types (e.g., US stocks, international stocks, gold, bonds), each with:
- **Expected return**: real annual expected return
- **Volatility**: annual standard deviation
- **Distribution type**: normal, lognormal, or fat-tailed (Student's t)
- **Fat-tail degrees of freedom**: for t-distribution
- **Initial balance**: starting value in real dollars

Returns are generated independently per asset (no correlation matrix for now).

### 3.3 Non-Risky Assets

Cash, treasuries, or similar, each with:
- **Fixed return**: real annual return rate
- **Initial balance**: starting value

### 3.4 Asset Groups and Rebalancing

- Assets can be assigned to named groups (e.g., "Aggressive", "Conservative")
- Each asset has a target weight within its group (e.g., 80% stocks, 20% gold)
- Groups can be set to rebalance annually to target weights

### 3.5 Reverse Mortgage Line of Credit

- Opens at a configurable age
- Credit limit grows annually
- Drawn when portfolio drawdown exceeds threshold (DD2)
- Partial coverage of shortfall (configurable fraction)
- Repaid when portfolio recovers to new highs
- Same mechanics as current `simulate.py` implementation

### 3.6 Equity Loan

- Amortized loan with configurable rate and term
- Proceeds held in a "loan bucket" with its own return rate
- Bucket accessed only during drawdowns exceeding threshold
- Lien paid off when reverse mortgage opens
- Same mechanics as current `simulate.py` implementation

### 3.7 Spending Guardrails

- Spending split into floor (non-discretionary) and flex (discretionary) components
- Flex spending cut based on portfolio drawdown thresholds:
  - DD1 threshold → CUT1 fraction of flex cut
  - DD2 threshold → CUT2 fraction of flex cut
- Floor spending always attempted (failure = plan failure)
- Configurable flex calibration parameters

### 3.8 Reserve Policy

- Cash + treasury reserves sized to N years of planned spending
- Configurable cash/treasury split
- Reserves refilled from risky assets when drawdown is low (< DD1)

### 3.9 Scenario Combinations (Sweep Grid)

Run multiple combinations simultaneously:
- Starting portfolio values (e.g., $1M, $1.5M, $2M)
- Reserve years (e.g., 0, 0.5, 1.0)
- Loan amounts (e.g., $0, $100K)
- Other sweepable parameters as needed

### 3.10 Optimization Targets

Binary search to find optimal values for:
- **Max yearly withdrawals (death-weighted)**: maximize spending with target success probability, weighted by mortality
- **Max yearly withdrawals at age 99**: maximize spending where all paths survive to 99
- **Minimum starting assets**: find smallest portfolio achieving target success at a given spending level
- **Blended metrics**: weighted combination of death-weighted and age-99 success
- Pluggable architecture for adding new optimization targets

### 3.11 Web Application Features

- **Scenario management**: Create, edit, duplicate, delete scenarios per user
- **Aggregate results**: Summary table of results across sweep grid (success rates, drawdowns, terminal balances)
- **Visualization**: Charts for success rates, drawdowns, portfolio balance fan charts (percentile bands over time)
- **Path explorer**: Drill into individual simulation paths — year-by-year account balances
- **Async execution**: Simulations run in background with progress tracking and polling

## 4. Project Structure

```
retirement-mc/
├── docker-compose.yml              # Local: Postgres only
├── apps/
│   ├── web/                        # Next.js + shadcn UI
│   │   ├── Dockerfile
│   │   ├── prisma/schema.prisma
│   │   └── src/
│   │       ├── app/                # Pages + API routes
│   │       ├── lib/                # auth, prisma, simulation-client
│   │       └── components/         # ui/, scenario/, results/, layout/
│   └── engine/                     # Python FastAPI
│       ├── Dockerfile
│       ├── requirements.txt
│       └── src/
│           ├── main.py             # FastAPI app
│           ├── models/             # Pydantic request/response
│           └── simulation/         # Modular engine
│               ├── engine.py       # Core year-by-year loop
│               ├── optimizer.py    # Binary search
│               ├── returns.py      # Return generators
│               ├── mortality.py    # SSA table + metrics
│               ├── income.py       # Flexible income streams
│               ├── accounts.py     # Account helpers
│               ├── guardrails.py   # Spending cuts
│               ├── reverse_mortgage.py
│               ├── loan.py
│               └── rebalancing.py  # Group rebalancing
└── legacy/                         # Backup of original simulate.py
```

## 5. Database Schema

### Auth Tables (Auth.js/NextAuth)

- **User**: id, email, name, image
- **Account**: OAuth provider links (Google)
- **Session**: JWT session tracking

### Application Tables

**Scenario** — Per-user scenario configuration:
- Core params: startAge, partialYearFraction, nSims, seed
- Mode: optimize/single, eFixed, targetSuccessRate, eLo/eHi, eSearchIters, optimizeMetric
- Spending: floorAnnualReal, incomeAppliesToSpend, surplusAllocation
- Reserve: reserveCashFraction, safeRealReturn
- Guardrails: dd1, dd2, cut1, cut2, flex calibration params
- Reverse mortgage: rmOpenAge, homeValueReal, rmPlfAtOpen, growth/rate/cover/repay params
- Equity loan: loanRealRate, loanTermYears, bucket params

**Asset** — Per-scenario asset:
- name, category (risky/non_risky), initialBalance
- Risky: expectedReturn, volatility, distributionType, fatTailDf
- Non-risky: fixedReturn
- targetWeight (within group), assetGroupId

**AssetGroup** — Named groups per scenario:
- name, rebalanceAnnually
- Has many Assets

**Income** — Per-scenario income stream:
- name, type (social_security/annuity/salary/freelancing/other)
- annualAmountReal, startAge, endAge, colaRate

**SweepValue** — Parameter sweep definitions:
- parameter name (start_portfolio/reserve_years/loan_amount/etc.)
- values (JSON array)

**SimulationRun** — Job tracking:
- status (pending/running/completed/failed), progress (0-1)
- configSnapshot (full scenario JSON at run time)
- errorMessage, startedAt, completedAt

**SimulationResult** — One row per grid point:
- Grid coords: startPortfolio, reserveYears, loanAmount
- Optimization: maxEOrFixedE
- Success metrics: pSuccessDeathWeighted, pSuccessToAge99
- Drawdown: medianMaxDdRisky, medianMaxDdTotal
- RM: homeEquityRemainingMedian, pAnyRmDraw, rmBalanceEndMedian
- Terminal: riskyEndMedian, totalNetEndMedian, netWorthEndMedian
- pathData (nullable JSON — per-path arrays for drill-down)

## 6. API Design

### Next.js API Routes (auth-protected)

| Method | Route | Purpose |
|--------|-------|---------|
| GET | /api/scenarios | List user's scenarios |
| POST | /api/scenarios | Create scenario |
| GET | /api/scenarios/:id | Get scenario with all sub-entities |
| PUT | /api/scenarios/:id | Update scenario |
| DELETE | /api/scenarios/:id | Delete scenario |
| POST | /api/scenarios/:id/duplicate | Deep copy scenario |
| POST | /api/simulations | Start simulation run |
| GET | /api/simulations?scenarioId=X | List runs for scenario |
| GET | /api/simulations/:id | Get run status + results |
| GET | /api/simulations/:id/paths | Get per-path drill-down data |

### Python FastAPI (internal only)

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /simulate | Run simulation, return results |
| POST | /simulate/progress | SSE stream with progress per grid point |
| GET | /health | Health check |

The Python service is stateless — no database access. Next.js serializes the scenario into JSON, POSTs to Python, writes results to Postgres.

## 7. Job Execution Flow

1. User clicks "Run" → `POST /api/simulations` → creates SimulationRun (pending), returns run ID
2. Next.js async-calls Python engine with full scenario config JSON
3. Python computes (5-30s), streams progress via SSE to Next.js
4. As results arrive, Next.js updates SimulationRun.progress in DB
5. On completion, Next.js inserts SimulationResult rows, sets status = completed
6. Frontend polls `GET /api/simulations/:id` every 2 seconds until done

## 8. Frontend Pages

| Route | Content |
|-------|---------|
| `/` | Dashboard or sign-in CTA |
| `/scenarios` | Card grid of user's scenarios |
| `/scenarios/new` | Tabbed scenario creation form |
| `/scenarios/[id]` | Edit scenario (tabs: General, Assets, Income, Guardrails, RM/Loans, Sweep Grid) |
| `/scenarios/[id]/results` | Summary table + charts + path explorer |

### Key Components

- **ScenarioForm**: Tabbed editor with dynamic add/remove lists for assets and incomes
- **AssetEditor / IncomeEditor / AssetGroupEditor**: Sub-forms for flexible entities
- **GuardrailsEditor / ReverseMortgageEditor / LoanEditor**: Parameter group editors
- **SummaryTable**: Sortable/filterable results across sweep dimensions
- **SuccessChart**: Bar/heat map of success rates across grid
- **BalanceChart**: Fan chart with percentile bands of portfolio balance over time
- **DrawdownChart**: Histogram of max drawdowns
- **PathExplorer**: Select individual MC paths, view year-by-year breakdown
- **SimulationStatus**: Progress bar with polling

### State Management

- **Server state**: React Query (TanStack Query) — scenario CRUD, simulation polling
- **Form state**: React Hook Form + Zod validation

## 9. Authentication

- Auth.js (NextAuth v5) with Google OAuth provider
- Prisma adapter stores users/accounts in PostgreSQL
- JWT session strategy (stateless)
- Next.js middleware protects all `/api/scenarios/*`, `/api/simulations/*`, and `/scenarios/*` routes
- Every API route extracts userId from JWT and scopes all queries to that user
- Python engine has no auth — internal network only

## 10. Implementation Phases

### Phase 1: Foundation
- Monorepo scaffolding (Next.js + shadcn + FastAPI + Docker Compose for Postgres)
- Prisma schema (simplified: Scenario with flat params, SimulationRun, SimulationResult)
- NextAuth Google OAuth
- Scenario CRUD (API routes + basic list/create/edit UI)
- Port simulate.py as-is into FastAPI POST endpoint
- End-to-end flow: create scenario → run sim → view summary table

### Phase 2: Flexible Assets & Incomes
- Add Asset, AssetGroup, Income, SweepValue to schema
- Build editor components
- Refactor Python engine into modular `simulation/` package
- Multi-asset return generation (normal, lognormal, fat-tailed)
- Flexible income processing
- Asset group rebalancing

### Phase 3: Results Visualization & Path Explorer
- Per-path data capture (opt-in flag)
- Fan charts, histograms, bar charts
- Path explorer with year-by-year drill-down
- Scenario duplication

### Phase 4: Advanced Optimization & Deployment
- "Minimum starting assets" optimization target
- SSE progress streaming
- Frontend progress bar
- Railway deployment
- CI pipeline (GitHub Actions)
- Error handling and polish

## 11. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Python for simulation engine | NumPy vectorized 25k-path computation; no benefit to rewriting in TS |
| No task queue (Celery/Redis) | Over-engineering for expected scale. FastAPI + asyncio.to_thread() suffices. Easy to add later. |
| Polling over WebSockets | Updates every few seconds. Polling is simpler, works behind all proxies. |
| Path data as JSON column | 25k paths × 47 years × N accounts = too many rows. JSON loaded on demand. |
| Config snapshot on SimulationRun | Results reproducible even if scenario is edited later |
| Prisma ORM | Type safety with TypeScript, Auth.js adapter, migration management |
| Independent asset returns (no correlation) | Simpler for v1. Correlation matrix is a future enhancement. |

## 12. Future Enhancements (Backlog)

- Correlated asset returns (correlation matrix)
- Tax modeling (Roth/traditional/taxable accounts)
- Glidepath support (changing allocation over time)
- Scenario comparison mode (side-by-side results)
- Sharing scenarios between users
- PDF report generation
- Alternative mortality tables
