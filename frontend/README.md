# AI Hedge Fund — Frontend

Next.js 14 (App Router) + React + TypeScript + Tailwind + Recharts + Zustand.  
Mobile-first, dark theme. See [FRONTEND_SYSTEM_SPEC.md](./FRONTEND_SYSTEM_SPEC.md) for full spec.

## Pages

- **Dashboard** — AUM, daily return, Sharpe, drawdown, equity curve, strategy leaderboard, AI pipeline
- **Market** — Symbols, K-line (stub)
- **Strategies** — Strategy pool table
- **Alpha Lab** — Funnel (generated → backtest → risk → deployed)
- **Evolution** — Generations, best strategy
- **Portfolio** — AUM, allocation pie, positions
- **Risk** — Max DD, VaR, exposure, checks
- **Trade** — Live trades table
- **Reports** — Monthly metrics, PDF export (stub)
- **Settings**

## Run

1. **Gateway** (from repo root):
   ```bash
   source .venv/bin/activate
   uv run uvicorn gateway.app:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend**:
   ```bash
   cd frontend
   rm -rf node_modules .next
   npm install
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000). The frontend calls the Gateway at `http://127.0.0.1:8000/api` by default (set `NEXT_PUBLIC_API_TARGET` to override). **Start the Gateway first**, otherwise API requests will fail.

## Build

```bash
npm run build
npm run start
```

## Structure

```
src/
  app/           # Next.js App Router (layout, page, market, strategies, ...)
  components/    # Nav, StatCard, EquityCurve
  api/           # client.ts (api.dashboard(), api.evolution(), ...)
  store/         # Zustand (useAppStore)
  hooks/         # useDashboard
  utils/         # format.ts
```
