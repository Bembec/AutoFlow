# AutoFlow web app

Next.js 16 (App Router, TypeScript, Tailwind CSS 4) with React Flow for the workflow canvas.

## Run it

```bash
# 1. API (in backend/)
python -m autoflow.api            # http://127.0.0.1:8000

# 2. Web app (in frontend/)
npm install
npm run dev                       # http://localhost:3000
```

The browser only talks to the web app. `next.config.ts` forwards `/api/*` and
`/hooks/*` to the API (`AUTOFLOW_API_URL`, default `http://127.0.0.1:8000`),
so the two share one origin and no CORS setup is needed. Set the API's
`AUTOFLOW_PUBLIC_URL` to the web app's address so webhook and OAuth callback
URLs point here.

## Pages

| Path | What it does |
| --- | --- |
| `/` | Landing page |
| `/register`, `/login` | Accounts (a new account gets its own workspace) |
| `/dashboard` | Time saved, today's runs and limits, recent runs |
| `/workflows/new` | Describe a workflow in plain words (AI builder), or start from a template |
| `/workflows/[id]` | Canvas, step inspector, test/live runs, publish, pause, versions and rollback, webhook setup |
| `/executions`, `/executions/[id]` | Run history; step-by-step input and output; cancel and retry |
| `/approvals` | Approve emails and steps, correct AI categories and results |
| `/connections` | Connect Airtable, SMTP, HTTP APIs and Google (OAuth) |
| `/settings` | Emergency stop, daily limits, team members, new workspace |
| `/oauth/callback/[provider]` | Finishes "Connect Google" sign-in |

## Structure

- `src/lib/api.ts`: typed fetch client (bearer token, error messages)
- `src/lib/session.tsx`: current user, workspace and role checks
- `src/lib/useApi.ts`: data loading with stale-response protection
- `src/components/`: app shell, UI primitives and `WorkflowCanvas`

## Checks

```bash
npx tsc --noEmit
npm run lint
npm run build
```
