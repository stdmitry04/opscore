# OpsCore

This is a small demo of scaled down patterns from production systems built at APS Data Technologies. The production systems are under NDA. This exists to show the decisions concretely

## How to read this code

- Start: `backend/apps/rbac/permissions_registry.py` — permission model and registry
- Then: `backend/apps/agent/tools.py` — tool execution, permission enforcement, failure handling
- Then: `backend/apps/agent/agent.py` — agent loop, memory, async task architecture
- Then: `backend/apps/hr/views.py` — RAG pipeline wired to document search

## Stack

- Python 3.11, Django 4.2, Django REST Framework
- PostgreSQL (main data store)
- Redis (permission cache, Celery broker, agent session memory)
- Celery (async tasks: document embedding, agent execution)
- Qdrant (vector store for document chunks)
- Anthropic Claude API (agent)
- Next.js 14 App Router, TypeScript

## Running locally

Copy `.env.example` to `.env` and fill it in. You need PostgreSQL and Redis. Qdrant is optional; document search degrades to a text fallback without it.

```bash
# Backend
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver

# Worker (required for agent and document embedding)
celery -A opscore worker -Q default,embeddings --loglevel=info

# Frontend
cd frontend
npm install
npm run dev
```

## Architecture decisions

Each decision below came from a real constraint. The business context is included because the constraint is what makes the decision make sense.

---

### RBAC: capability-based, deny by default

**The constraint**

K-12 school districts have dozens of distinct staff roles — principals, HR coordinators, payroll admins, substitute teachers, building managers — each needing access scoped differently across modules, buildings, and data types. The districts needed to manage this themselves through an admin UI, without filing tickets or waiting on a developer.

The earlier system had permissions stored in the database with no registry to validate them against. A developer could reference any permission string on the backend, like `hr.employee.salary` or `payroll.run`, and it would not be checked at startup that the string was valid. Over time this caused divergence between what was in the database and what endpoints actually expected. Because the model was allow-by-default, that divergence meant users had access they should not have had. The district would configure a role, the admin would save it, and a staff member would get through an endpoint that was never intended to be open to them.

**The decision**

Permissions follow `module.submodule.view` or `module.submodule.edit`. That's it — no arbitrary action suffixes, no free-form strings. Every valid permission is declared in one place:

```python
permission_registry = PermRegistry([
    Perm("hr.employee",        description="employees",       category="hr"),
    Perm("hr.employee.salary", description="employee salary", category="hr", sensitive=True),
    Perm("hr.job",             description="job postings",    category="hr"),
    ...
])
```

`Perm("hr.employee")` produces exactly two leaf permissions: `hr.employee.view` and `hr.employee.edit`. The registry holds only leaf variants. When any view or tool references a permission:

```python
required_permission = permission_registry[Perm("hr.employee").view]
```

If `hr.employee` is not in the registry, this raises `KeyError` at import time. The server does not start. There is no way to ship code that references a permission that does not exist without it being caught immediately on deploy.

The model is deny-by-default: a user has exactly the permissions explicitly granted to their roles. A missing grant means denied. No deny rules. No allow-by-default with carve-outs. This matters because allow-by-default with deny rules is non-monotonic, meaning adding a grant can decrease effective permissions if a deny rule now partially matches, which makes the model hard to reason about and audit. Deny-by-default makes the permission set for any user fully readable from their role grants alone.

For the district admin, this translated to a simple UI: create a role, toggle permissions to view, edit, or off, save. The admin could see exactly what a role could do, change it in real time, and the effect propagated to active sessions within one request cycle. A change that previously needed a developer now took a few clicks.

**The tradeoff**

Capability-based is more verbose than role-based on the common case. Assigning a "manager" role is one operation; listing every specific permission that manager needs is more. We accepted this cost because the district's roles were not standard — they overlapped, conflicted, and changed frequently enough that a fixed role hierarchy would have needed constant developer maintenance anyway.

---

### Agent: Celery task, not streaming HTTP

**The constraint**

The users asking questions of the agent are HR administrators and district staff, many of whom are not technical. Their questions are not simple — "pull payroll status for all employees in Building 4 who have not completed onboarding, then check the third-party HR system for their benefits enrollment" is a realistic query. That kind of question requires multiple tool calls, hitting internal APIs and external payroll systems, and can take 15 to 30 seconds to complete.

A 30-second blocking HTTP request exhausts connection pools at any meaningful scale. A streaming response solves the latency problem but creates a different one: if the user's browser tab closes or their connection drops mid-run, the agent loop is either orphaned or interrupted. The question does not get answered, and the user has to retype it and wait again. For non-technical district staff, that is not acceptable.

**The decision**

Agent runs as a Celery task. The HTTP request does one thing: create the task record and return a task ID. The frontend polls the task status endpoint until the task completes. The agent loop runs fully decoupled from any HTTP connection.

```python
# views.py — the HTTP layer just creates the task
task_record = TaskRecord.objects.create(task_type='agent_chat', org=org, ...)
run_agent_task.apply_async(kwargs={...}, queue='default')
return Response({'task_id': str(task_record.id)}, status=202)

# tasks.py — the agent runs in a worker, independent of the client
@shared_task
def run_agent_task(message, session_id, user_id, org_id, task_record_id):
    result = run_agent(message, session_id, user, org)
    task_record.status = 'success'
    task_record.result = result
    task_record.save()
```

If the client disconnects mid-run, the task finishes anyway. The result is stored in the task record. When the user reconnects or reloads, the frontend picks up the completed result by polling the same task ID.

Permissions are re-checked at tool execution time, not just at task creation. This handles the edge case where a user's role is changed while an agent task is already running. The task was started with valid permissions; by the time a tool call fires, those permissions may have been revoked. Checking at creation time only would leave a window where revoked permissions still work inside a running task.

**The tradeoff**

Polling is less real-time than SSE or WebSockets. For a chat interface that takes 15 to 30 seconds per response, the difference between 1-second polling and true streaming is not meaningful to the user. The complexity saved — no connection management, no backpressure, full observability through task state — was worth the minor UX cost.

---

### RAG: two-stage retrieval

**The constraint**

The admissions platform handles thousands of documents per deployment — employee records, monthly reports, policy documents ranging from a single page to tens of pages. Users are looking for specific details: a particular month's payroll report, a specific employee's onboarding status, a policy clause. The corpus is large and the queries are precise.

Embedding similarity alone was not sufficient. The failure mode was not wrong documents — it was wrong chunks. The right document would surface but the retrieved chunk would miss the specific detail the query was asking about. A question about benefits enrollment for a particular employee would return a chunk from the right document but from a different section, causing the agent to report missing information that was actually present.

**The decision**

Two-stage retrieval: embedding similarity for recall, cross-encoder for precision.

1. Embed the query with `all-MiniLM-L6-v2`
2. Qdrant returns the top 20 chunks by cosine similarity — cheap, fast, good recall
3. A cross-encoder (`ms-marco-MiniLM-L-6-v2`) rescores each (query, chunk) pair — reads the full query and chunk together, not just their vector proximity
4. Chunks below 0.70 rerank score are dropped
5. Remaining results are returned sorted by rerank score

The cross-encoder is the key step. Cosine similarity measures whether two vectors are close in embedding space, which is a reasonable proxy for topic relevance but a poor proxy for specific detail relevance. The cross-encoder reads the query and the chunk together as a pair, which lets it distinguish between "this chunk is about the right topic" and "this chunk actually answers the question."

The 0.70 threshold was tuned against an eval set built from real query patterns observed during district user research — typical queries about employee status, payroll, benefits, and policies. Raising the threshold above 0.70 improved precision but dropped recall enough that valid answers were being filtered out. Below 0.70 the agent received too much noise and started returning approximate answers where exact ones existed.

**The tradeoff**

Two models to maintain instead of one, and cross-encoder inference adds latency per query. The candidate set is capped at 20 to keep the reranking cost bounded regardless of corpus size. An alternative was reranking with an LLM directly, which would be more accurate but would cost roughly one full inference call per candidate chunk — at 20 candidates per query and 200 daily queries, that cost does not scale. The cross-encoder runs locally and adds milliseconds, not dollars per query.

---

### Permission and tool registries

The earlier system had a YAML file, a code generator, and a StrEnum — three places to touch when adding a permission, with no enforcement that they stayed in sync.

Permissions are now defined in one place. `sync_permissions()` materializes them into Postgres on startup (convergent, safe to call repeatedly, removes stale rows). The registry validates at import time. The tool registry validates its permissions against the permission registry at startup — a tool that references a missing permission prevents the server from starting.

On the frontend, `TOOL_REGISTRY` in `permissions.ts` references `PERMS` constants typed as `PermKey`. TypeScript will not compile if a tool references a key that does not exist. Backend enforces at import time, frontend enforces at build time.

### Agent memory

Short-term: conversation history in Redis, 20-turn sliding window, 1-hour TTL. Trims from the front so recent context is always preserved. Expires on inactivity rather than a hard wall.

Long-term: user preferences in Postgres (`UserMemory` model), injected into the system prompt on every request. Infrastructure is in place; active write path (detecting and storing preferences mid-conversation) is not yet implemented in this demo.

### Audit log

Every request goes through `AuditLogMiddleware`, which records user, org, action, resource type, resource ID, and IP. Indexes on `(user, timestamp)`, `(org, timestamp)`, and `(resource_type, resource_id)` cover expected query patterns without full scans.

## Adding a permission

Add a `Perm(...)` entry to `permission_registry` in `backend/apps/rbac/permissions_registry.py`. Add the matching constants to `PERMS` in `frontend/src/lib/permissions.ts`. `sync_permissions()` materializes the new rows into Postgres on startup.

No YAML. No generation step. No enum to sync.

## Adding an agent tool

1. Write a `Tool` subclass in `backend/apps/agent/tools.py`. Set `required_permission = permission_registry[Perm("...").view]`. If the perm is not in the registry, the server refuses to start.
2. Add the instance to the `ToolRegistry` list at the bottom of the same file.
3. Add a `ToolDef` entry to `TOOL_REGISTRY` in `frontend/src/lib/permissions.ts`. If `required_permission` is not a valid `PermKey`, the frontend will not compile.
