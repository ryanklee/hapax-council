# council-web

React SPA dashboard for the hapax-council agent system. Provides health monitoring, agent execution, chat, nudge management, and management oversight in a single-page interface.

## Quick start

```bash
pnpm install      # install dependencies
pnpm dev          # dev server on :5173
pnpm build        # type-check + production build
```

Requires the cockpit API running at :8051. Start it from the council root:

```bash
uv run cockpit    # FastAPI on :8051
```

Vite proxies `/api` requests to `http://127.0.0.1:8051` in dev mode.

## Stack

React 19, TypeScript 5.9 (strict), Vite 7, Tailwind CSS 4, TanStack React Query, React Router 7, Recharts, Lucide React, react-markdown + remark-gfm, JetBrains Mono.

## Structure

```
src/
  api/            API client, React Query hooks, SSE helpers, TypeScript types
  components/
    chat/         Chat UI (messages, input, streaming, tool calls)
    dashboard/    Agent grid, nudge list, output pane, copilot banner
    demos/        Demo list and detail views
    layout/       App layout shell, manual drawer, health toast watcher
    shared/       Command palette, error boundary, modals, markdown, toasts
    sidebar/      15 sidebar panels (health, VRAM, containers, timers, briefing,
                  goals, scout, cost, drift, management, accommodations, freshness)
  hooks/          useHealthToasts, useInputHistory, useKeyboardShortcuts, useSSE
  pages/          DashboardPage, ChatPage, DemosPage
```

## Routes

| Path | Page | Purpose |
|------|------|---------|
| `/` | DashboardPage | Health, agents, nudges, sidebar panels |
| `/chat` | ChatPage | Streaming chat with cockpit backend |
| `/demos` | DemosPage | Browse and view generated demos |

## Conventions

- **pnpm only** — never npm or yarn
- TypeScript strict mode enforced
- Tailwind for all styling — no CSS modules or styled-components
- Functional components only
- API types in `src/api/types.ts` mirror cockpit Python dataclasses
- No test runner currently configured
