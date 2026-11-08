# Cakra Aksara (UAIL) — Master Documentation

Consolidated Edition v1.2 · 8 November 2026 · License: Apache 2.0
Status: working baseline for owner review. Checked against the `main` branch on 8 November 2026.

## 0. How to read this document

This file merges the earlier plans (Master Baseline v1.0, SRS and API Specification v1.0, Database Schema and Migration Specification v1.0), the database starter, the ChatGPT memory export, and a review of the GitHub repository.

| Label | Meaning |
|---|---|
| **FINAL** | The owner decided this. |
| **BASELINE** | Recommended starting choice. It can be replaced later. |
| **PROPOSED** | Chosen while merging documents. The owner must confirm it. |
| **OPEN** | Not decided yet. |
| **VERIFIED** | Confirmed by reading the repository code. Not always run. |
| **REPORTED** | From the ChatGPT export. Not checked. |

Where the old documents disagreed, this file picks one answer and records it in Section 14.

## 1. Vision and problem

**Cakra Aksara** is the project name. **UAIL** (Universal AI Intelligence Layer) is the technical name. They are the same project.

Cakra Aksara is an independent layer between AI apps, agents, LLM providers and knowledge sources. It checks context, manages memory, detects assumptions, verifies claims and keeps context continuous across models. Models can change, but memory, protection and verification stay the same.

It does **not** replace LLMs, train models, or promise to remove all hallucinations.

**Tagline (OPEN).** The README says *One Intelligence. Connected Everywhere.* The ChatGPT export says *One Intelligence Layer. Every AI. Consistent Knowledge.* Choose one.

**Problems it solves**

1. AI treats assumptions as facts.
2. AI pulls in irrelevant memory or conversation.
3. AI uses old information without knowing it changed.
4. AI makes claims without enough sources.
5. AI misses contradictions in its context.
6. AI loses context when the model or platform changes.
7. Users cannot control what is stored and used.

## 2. Design principles (FINAL)

- **Evidence before assertion:** every claim needs a traceable basis.
- **Explicit uncertainty:** say when you do not know.
- **User-controlled memory:** the user controls storing, fixing and deleting.
- **Privacy by design:** collect less; process locally when possible.
- **Model agnostic:** no lock-in to one vendor.
- **Modular:** modules can be used and tested alone.
- **Fail safely:** a failed check is never shown as a successful check.
- **Human oversight:** risky changes need a person to approve.

## 3. Names and structure

### 3.1 Product surfaces (REPORTED)

Research, Intelligence and Protect. Their exact scope is OPEN.

### 3.2 Seven layers and twelve modules (PROPOSED mapping)

| Layer | Modules and components |
|---|---|
| Core Engine | UAIL-12 Universal AI Bridge, Request and Identity Manager, Policy Engine, Intelligence Orchestrator |
| Protection | UAIL-02 Context Firewall, UAIL-01 Assumption Killer |
| Intelligence | UAIL-08 Intent Intelligence, UAIL-09 Knowledge Gap Detector |
| Memory | UAIL-03 Memory Intelligence, UAIL-04 Memory Repair Engine |
| Verification | UAIL-06 Truth Ledger, UAIL-07 Contradiction Detector, UAIL-05 Hallucination Detector, UAIL-11 AI Self-Audit |
| Continuity | UAIL-10 AI Continuity Engine |
| Interface | REST API, SDK, MCP server, admin dashboard |

## 4. Scope, priorities and roadmap

### 4.1 MVP goal

Prove that the system can receive a request, check the context and return a clear result through one consistent interface.

**In the MVP (P0):** Universal AI Bridge (REST API), Policy Engine, basic Context Firewall, Assumption Killer, basic Memory Intelligence with versioning, basic Truth Ledger, basic Contradiction Detector, audit log and policy configuration, SQLite (local) and PostgreSQL (server), API documentation and examples.

**P1:** Memory Repair Engine, advanced Hallucination Detector, Intent Intelligence, Knowledge Gap Detector, AI Continuity Engine, AI Self-Audit.

**P2:** admin dashboard (can move earlier), wide multi-platform integrations.

**Not in v1.0:** training foundation models, replacing vendor memory systems, guaranteeing all hallucinations are found, auto-verifying external sources, risky autonomous actions without approval, production integrations with every AI platform.

### 4.2 Roadmap (PROPOSED)

Two roadmaps existed. This file uses the phase 0–7 order, because the MVP needs memory and verification before the intelligence expansion.

| Phase | Focus | Main result | Export roadmap name |
|---|---|---|---|
| 0 | Project foundation | Repo, license, contribution rules, ADRs | Foundation |
| 1 | Core infrastructure | API, config, database, logging, auth baseline | Foundation |
| 2 | Protection MVP | Context Firewall, Assumption Killer, Policy Engine, test dataset | Protection |
| 3 | Memory MVP | CRUD, versions, source tracking, export/import | Memory |
| 4 | Verification | Truth Ledger, claim and evidence linking, Contradiction Detector | Intelligence (part) |
| 5 | Intelligence expansion | Hallucination, Intent, Knowledge Gap | Intelligence |
| 6 | Continuity | Portable packages, adapters, MCP server, SDK | Continuity |
| 7 | Production readiness | Security review, load test, deployment, monitoring | Ecosystem |

**Where the project is now:** Phase 0 is mostly done, and Phase 1 is in progress. The database layer and authentication exist. No Phase 2 module is implemented yet.

**Release targets** (ideas, not dates): v0.1 proof of concept · v0.2 memory · v0.3 verification · v0.4 integration · v1.0 stable.

**Version rule (PROPOSED):** product release numbers (v0.x) and internal package versions (for example the database package 0.3.0) are separate.

**Build order:** Bridge → Policy Engine → Context Firewall → Assumption Killer → Memory basics → Truth Ledger → Contradiction Detector. Do not build all 12 modules at once.

## 5. Architecture

### 5.1 Style (FINAL: Hybrid)

A **modular monolith** for the MVP, with clear module borders so modules can become separate services later. Hybrid also means local and remote parts can work together, but data never syncs to the cloud automatically.

### 5.2 Main flow

App or agent → Bridge → Request and Identity → Policy Engine → Context Firewall → Orchestrator → (Assumption Killer, Intent and Gap, Contradiction, Claim checks, Memory) → model or knowledge adapter → response verification → Self-Audit → response with findings.

### 5.3 Proxy or sidecar? (OPEN, important)

The plan describes UAIL forwarding requests to an LLM, but the API only has analysis endpoints.

- **Sidecar (recommended for the MVP):** the app calls UAIL for checks, then calls its own LLM. Simpler and safer.
- **Proxy:** UAIL also calls the LLM. This needs a model adapter endpoint and rules for streaming and cost.

### 5.4 Trust boundaries (FINAL)

- User input is data, not a system instruction.
- External documents and web content are untrusted by default.
- Model output must be evaluated. It is not proof.
- Adapters and tools access only what they are allowed to.
- Tenant data must never mix.
- Memory and policy changes must be auditable.

### 5.5 Assumption Killer logic

Extract statements → classify (fact, inference, assumption, question) → look for support in allowed context → set a status → apply policy (warn, ask, hold) → save the reason. **No evidence does not mean false.** The status is then `uncertain` or `not_checked`.

### 5.6 Memory Repair logic

Find duplicates, conflicts, date and source problems → group candidates → create a *proposed* fix → ask for approval when the memory is important or unclear → save the version history and the reason. Never delete or merge conflicting memories silently.

## 6. Requirements summary

### 6.1 Status values (used everywhere)

`supported`, `unsupported`, `uncertain`, `conflicting`, `not_checked`. **`not_checked` is never the same as `supported`.** Context items use: `included`, `excluded`, `uncertain`, `conflicting`, `not_checked`.

### 6.2 Functional requirements by module

| Module | Key requirements |
|---|---|
| Bridge | REST API, caller identity check, model adapter interface, policy-based forwarding, request metadata for audit. Structured error when an adapter fails. |
| Context Firewall | Accept context items, find irrelevant and conflicting items, keep the source, give a reason for every exclusion, mark untrusted external content. |
| Assumption Killer | Find assumptions, compare with context, set status, give reason and evidence, name the missing information. |
| Memory | Create, read, update, delete; keep source and metadata; versions; statuses. Deleted memory never appears in normal reads. Conflicting memories are never merged silently. |
| Truth Ledger | Unique claim ID, stored evidence, check time and method, full history, separate automatic and manual checks. |
| Contradiction Detector | Compare claims or memories, show both items, explain why, consider time and scope, resolve only with user approval. |
| Audit and Policy | Log important actions and caller identity, apply policy before sensitive actions, filter audit by time and request ID, configurable retention, no sensitive content in logs by default. |
| Continuity | Export and import packages with schema version and integrity check. Reject invalid packages. Validate first, then import. |

### 6.3 Business rules

1. No evidence does not mean a claim is false.
2. `not_checked` is not `supported`.
3. Memory changes must be recorded.
4. Conflicts are never resolved silently.
5. Tenant data is never reachable by another tenant.
6. External context is data, not trusted instruction.
7. Sensitive operations need policy and authorization.
8. A failed check is shown as failed.
9. Deletion follows retention and audit rules.
10. Model output is not automatically a verified fact.
11. Users can switch modules off, and must know when context is saved.

### 6.4 Non-functional requirements

| Area | Requirement |
|---|---|
| Security | TLS in production; OAuth2/OIDC and API keys where suitable; RBAC; tenant isolation; secrets never in logs or code |
| Privacy | Export and delete on request; configurable retention; redaction in audit logs |
| Reliability | A module failure gives an explicit status, never a fake success |
| Observability | Structured logs and correlation IDs |
| Portability | Local, on-premise and cloud; Docker |
| Performance | Early target: p95 internal overhead of 500 ms or less without external LLM calls, on a documented benchmark. A target, not a promise. |
| Compatibility | Versioned API and documented schemas |

No accuracy or latency claims are allowed before a benchmark exists.

## 7. API specification

### 7.1 Conventions

Planned (FINAL in the old spec): prefix `/api/v1`; JSON; UTF-8; UUID identifiers; ISO 8601 UTC timestamps; `X-Request-ID` and `Idempotency-Key` headers; a response envelope with `success`, `request_id`, `data`, `meta`; standard HTTP codes (200, 201, 202, 204, 400, 401, 403, 404, 409, 422, 429, 500, 503). Breaking changes need a new API version.

**Gap (VERIFIED):** the code uses the prefix `/v1`, not `/api/v1`, and returns plain JSON without the envelope. Pick one and update either the code or this spec (OPEN).

### 7.2 Planned endpoints

| Method | Path | Purpose | Priority | Built? |
|---|---|---|---|---|
| GET | `/health` | Health check | P0 | Yes |
| GET | `/ready` | Database readiness | P0 | Yes (not in old spec) |
| POST | `/requests/analyze` | Analyze a request and context | P0 | No |
| POST | `/context/filter` | Filter and classify context | P0 | No |
| POST | `/assumptions/check` | Find and evaluate assumptions | P0 | No |
| POST | `/claims/verify` | Verify claims against evidence | P0 | No |
| POST, GET | `/memories` | Create / list memories | P0 | No |
| PATCH, DELETE | `/memories/{id}` | Update (needs `expected_version`) / delete | P0 | No |
| GET | `/ledger/claims/{id}` | Claim history | P0 | No |
| POST | `/continuity/export`, `/continuity/import` | Export / import packages | P1 | No |

### 7.3 Authentication endpoints (VERIFIED)

Authentication uses **two layers**. Every call needs a tenant **API key** in `X-API-Key`. Calls that act as a user also need a **Bearer token** from login.

| Endpoint | Required key scope | Notes |
|---|---|---|
| `GET /v1/auth/check` | `auth:check` | Confirms the API key works |
| `POST /v1/auth/register` | `users:register` | Email, password (12 or more characters), optional display name. Role is always `user`. Returns 409 if the email exists in that tenant. |
| `POST /v1/auth/login` | `users:login` | Returns a Bearer token valid for 60 minutes |
| `GET /v1/auth/me` | `users:read` | Needs Bearer token |
| `POST /v1/auth/logout` | `users:logout` | Revokes the session |

Checks done on each user call: the token hash exists, the session is not revoked or expired, the session tenant matches the API key tenant, and the user is active and in the same tenant.

### 7.4 Missing endpoints (PROPOSED, needed by P0 rules)

| Need | Suggested endpoint |
|---|---|
| User data export and delete | `POST /account/export`, `DELETE /account/data` |
| Policy management | `GET/POST /policies`, `PATCH /policies/{id}` |
| Audit search | `GET /audit/events` |
| Resolve a conflict | `POST /contradictions/{id}/resolve`, `GET /contradictions` |
| API key lifecycle | `POST/GET /api-keys`, `DELETE /api-keys/{id}` |

### 7.5 Analyze response (PROPOSED merge)

One shape: `analysis_id`, `status`, `decision`, `assumptions`, `context_result` (`included`, `excluded`, `uncertain`), `contradictions`, `findings`, `evidence`, `uncertainties`, `warnings`, `policy_version`, `processing_metadata`.

### 7.6 Rules for specific endpoints

- **PATCH memory:** `expected_version` is required. A wrong version returns `409`.
- **DELETE memory:** returns `204`. The API must not claim permanent removal from backups until it has happened.
- **Import:** `validate_only` is true by default; the conflict strategy is `report`. Other strategies need clear user approval.
- **Claims:** a reference string alone must not produce `supported`. Evidence needs an excerpt or a content hash, otherwise the best status is `uncertain`.
- **Idempotency:** the same key with a different payload returns `409`.

### 7.7 OpenAPI

The target file is `openapi/uail-v1.yaml`. It does not exist yet. FastAPI generates a draft automatically, which can be the starting point.

## 8. Data model

### 8.1 Rules (FINAL)

The relational database is the source of truth. Vector indexes only help search. Data has an owner, a source, a time and a version. Local and remote data never sync without rules. SQLite and PostgreSQL share the same core model. Every change goes through a migration.

### 8.2 Tables (VERIFIED: 17 models in `database/src/uail_db/models.py`)

| Group | Tables |
|---|---|
| Identity | `tenants`, `users` (has `password_hash`), `user_sessions`, `api_keys` |
| Requests | `requests`, `context_items` |
| Intelligence | `assumptions`, `contradictions` |
| Memory | `memories`, `memory_versions` |
| Verification | `claims`, `verifications`, `evidence` |
| Governance | `policies`, `audit_events` |
| Continuity | `continuity_packages` |
| Infrastructure | `idempotency_records` |

**Not built yet (PROPOSED):** `sources` (shared provenance), `projects` (optional grouping), `export_jobs`. Decide before schema freeze whether to add them.

### 8.3 Key table notes

- **users:** unique `(tenant_id, email)`. Passwords are stored only as hashes.
- **user_sessions:** stores only a SHA-256 hash of the token, with expiry, revoke time and last-used time.
- **api_keys:** key prefix, key hash, scopes, expiry and revoke time.
- **memories:** `tenant_id`, `owner_user_id` (null means tenant-level, still policy-controlled), `content`, `category`, `status`, `current_version`, source fields, `metadata`, `expires_at`, `deleted_at`.
- **memory_versions:** unique `(memory_id, version_number)`. Old versions are never overwritten.
- **claims, verifications, evidence:** a claim can have many verification records. Old records are never overwritten. Source metadata is not proof the source is true.
- **contradictions:** point to two items by type and ID. Polymorphic IDs cannot use normal foreign keys, so use a relation table or strict service checks.
- **audit_events:** append-only at application level; no tokens, API keys or full sensitive payloads.
- **idempotency_records:** unique `(tenant_id, idempotency_key)`. PROPOSED: also store the endpoint, user, an in-progress state and the saved response, so retries can replay it.
- **continuity_packages:** a checksum only detects changes. It does not prove who made the package. Use digital signatures for authenticity.

### 8.4 Memory update transaction (FINAL)

Load memory and version → check tenant and owner → compare `expected_version` → reject on mismatch → write the new version snapshot → update current content → increase `current_version` → write the audit event → commit. All steps are in one transaction.

### 8.5 Deletion and retention (PROPOSED fixes)

- Separate soft deletion, logical deletion, physical deletion, backup expiry and audit retention.
- Deleting a memory must also remove or mark its **version snapshots** and **vector embeddings**.
- Do not report deletion as complete while backups still hold copies.
- `context_items.content` is currently NOT NULL (VERIFIED). Make it nullable, because the privacy rule says request content need not be stored.
- Retention defaults are OPEN.

### 8.6 Tenant isolation

1. Every query is filtered by `tenant_id`.
2. The ORM tenant guard checks references on write (VERIFIED). **Gap:** `UserSession` is not in its map. The auth code checks the tenant by hand for now.
3. **PROPOSED:** composite foreign keys on `(tenant_id, id)`, so the database itself rejects cross-tenant links.
4. PostgreSQL Row-Level Security as a second layer.
5. SQLite has no RLS, so the service layer must enforce isolation.
6. Do not use hard-to-guess UUIDs instead of authorization.

### 8.7 Migrations

Rules: all schema changes use migrations; applied migrations are not edited; each migration is tested on both databases; destructive ones are reviewed; use forward-fix when a downgrade would lose data.

**State (VERIFIED):** migrations 0001 to 0011 exist. A fresh SQLite database reaches `0011 (head)` after the fix merged on 8 November 2026.

**Still a weak point:** migration `0001` builds all tables with `create_all` from the *current* models, and `0002`–`0010` are empty placeholders. That is why 0011 had to check before adding objects. **PROPOSED:** replace the baseline with explicit tables, then use real incremental migrations. Also test the upgrade path from revision 0010 on PostgreSQL.

## 9. Security and privacy

### 9.1 What exists (VERIFIED)

- Passwords: PBKDF2-HMAC-SHA256, 600,000 iterations, random 16-byte salt, constant-time compare. Minimum length 12.
- API keys: shown once, stored as a SHA-256 hash, with prefix `cak_`, scopes, expiry and revocation.
- Sessions: random token, SHA-256 hash stored, 60-minute life, revocable.
- Tenant checks between API key, session and user.
- No secrets in the repository. The Postgres helper script asks for the password at run time.
- `.gitignore` now ignores `.env` files.

### 9.2 Gaps

- No rate limiting or lockout on login or register.
- Login skips the password hash when the email does not exist, so response time can reveal which emails exist. Run a dummy hash in that case.
- Sessions have a fixed 60-minute life with no refresh token.
- No email verification or account recovery.
- `/health` returns the environment name. The spec says health checks must not expose infrastructure details.
- Audit events are not written by the auth routes yet.

### 9.3 Rules going forward

- **Authorization:** RBAC with roles owner, admin, developer, user, service; ownership checks; least privilege.
- **Data protection:** TLS; encryption at rest where the deployment supports it; redacted audit logs; user-controlled export and deletion.
- **Prompt injection:** external context is untrusted data. Instructions inside documents get no privilege. A result that comes only from an LLM cannot be `supported` (PROPOSED).
- **Errors:** no stack traces or secrets sent to clients in production.
- **Local mode:** single-user mode may run without login, but server mode must require authentication (PROPOSED).

## 10. Implementation status

### 10.1 Repository (VERIFIED)

`github.com/kiisafezone/cakra-aksara`, public, Apache 2.0, branch `main`.

| Path | Content |
|---|---|
| `api/app/` | FastAPI app: `main.py`, `auth.py`, `security.py`, `config.py`, `dependencies.py` |
| `api/requirements.txt` | fastapi 0.115.14, uvicorn 0.54.0, pydantic 1.10.27, starlette 0.46.2 |
| `api/security_smoke_test.py` | Manual end-to-end auth and tenant test script |
| `database/` | `uail_db` package, Alembic migrations 0001–0011, 3 test files, Postgres helper script |
| `.github/workflows/ci.yml` | Tests on Python 3.12 and 3.14, `alembic heads`, and a fresh-database upgrade step |
| `README.md` | Banner and status only |

### 10.2 What works

- 17 database models, tenant-scoped repositories, memory versions and optimistic checks, soft delete, audit events, service layer.
- API key and user authentication (Section 7.3).
- 16 database tests pass locally (VERIFIED on 8 November 2026). PostgreSQL integration tests need a configured database.

### 10.3 Not built

None of the 12 intelligence modules is implemented. There is no Bridge endpoint, Policy Engine, Context Firewall, Assumption Killer or memory API yet.

### 10.4 Environment risks

- Pydantic 1.10.27 is pinned while CI and the dev machine use Python 3.14. Pydantic v1 may not support 3.14. CI does not install the API packages, so this is untested. Verify it, and plan a move to Pydantic v2.
- `api/requirements.txt` does not list the `uail_db` package. The API needs `pip install -e database` as well. Document this.
- `api/security_smoke_test.py` has a hardcoded tenant ID, changes real dev data (rotates a password, edits key scopes), and is not part of CI.

## 11. Testing and release rules

**Levels:** unit, integration, API contract, security, tenant isolation, performance, end-to-end, AI evaluation, regression, privacy and deployment tests.

**Minimum scenarios:** no authentication; wrong tenant; harmful instructions in context; assumption without evidence; conflicting evidence; duplicate memory; time-based conflict; claim without evidence; irrelevant evidence; memory deletion; broken import package; database failure; model failure; module failure.

**Next P0 task:** turn the smoke test into pytest with a temporary database, and add it to CI.

**Definition of Done for a module:** input and output spec; API or interface contract; unit and integration tests; evaluation test for AI behavior; configuration docs; error and timeout handling; privacy-compliant logging; usage example; passed code review.

**v1.0 release gate:** all in-scope P0 requirements pass; OpenAPI valid and matching the code; tenant isolation tested; no secrets in the repo; migrations run on both databases from empty; install and config docs exist; license and dependency review done; **no false success when a check fails**.

**Evaluation:** build a small, reproducible test dataset in Phases 0–2. Report precision, recall, false positives and false negatives.

## 12. Governance and licensing

- **License:** Apache 2.0 (FINAL). Keep LICENSE, add NOTICE, keep copyright notices, check dependency licenses, document code origin. Third-party models and datasets may have other licenses.
- **Open-source files to add:** CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG. Changes go through pull requests. Architecture changes are recorded as ADRs. API changes need versioning and a changelog entry.
- **Distribution:** open-source core, SDK and API, Docker image, docs, adapters, dashboard. Core features must not be crippled to push paid plans.
- **Roles:** Product Owner, Project Lead, Architect, Backend, AI, Data, Security, QA, Documentation, Community. One person can hold several roles at first.
- **Risks:** false positives and negatives, memory poisoning, privacy leaks, overblocking, vendor dependency, wrong memory repair, high model cost, exaggerated marketing about hallucination detection, misuse for collecting chat data. Mitigation: explain every decision, configurable policy, regular evaluation, human approval, versioning, rule-based checks first, clear statement of limits.
- **Legal:** this file is not legal advice. Get a legal review before production use.

## 13. Open decisions

| # | Decision | Suggested default |
|---|---|---|
| 1 | Proxy or sidecar | Sidecar for the MVP |
| 2 | Auth for local mode | Single-user local mode without login; server mode requires login |
| 3 | Remaining auth details: rate limits, refresh tokens, email verification, account recovery (password hashing is decided: PBKDF2) | Not decided |
| 4 | API prefix and response envelope: `/v1` as built, or `/api/v1` as specified | Move code to `/api/v1` and add the envelope |
| 5 | Memory ownership | Tenant plus optional user owner |
| 6 | Verification engine | Rules first, LLM-assisted second; LLM-only never gives `supported` |
| 7 | Async jobs and queue | Not in the first MVP |
| 8 | External web evidence in v1.0 | Only evidence given by the app |
| 9 | Package signing | Checksum for MVP; digital signature before v1.0 |
| 10 | Retention defaults and backup lifetime | Not decided |
| 11 | Vector search | Optional pgvector adapter |
| 12 | Redis | Optional, not required |
| 13 | Model abstraction | LiteLLM or own adapter interface; keep the adapter interface either way |
| 14 | Frontend and dashboard | Dashboard after MVP; React and TypeScript is only a proposal |
| 15 | Tenant isolation level | ORM guard plus composite foreign keys plus optional RLS |
| 16 | Human approval flow for memory fixes | Not decided |
| 17 | Scope of Research, Intelligence and Protect surfaces | Not decided |
| 18 | First provider and agent protocol support | Not decided |
| 19 | Public benchmark and evaluation model | Not decided |
| 20 | Multi-tenant strategy for cloud | Not decided |
| 21 | Final tagline | Not decided |
| 22 | Pydantic v1 or v2 | Move to v2 |

## 14. Reconciliation log

| Conflict found | Resolution |
|---|---|
| Cakra Aksara vs UAIL | Same project. Cakra Aksara is the project name; UAIL is the technical name. |
| 7 layers vs 12 modules | Mapped in Section 3.2 (PROPOSED) |
| Two roadmaps | Phase 0–7 order used; export names mapped in Section 4.2 |
| Package v0.3.0 vs release v0.3 | Treated as separate numbering |
| Memory versioning priority P1, but PATCH requires versions | Versioning is **P0** |
| `FR-CON-` used for both contradiction and continuity | Rename continuity requirements to `FR-CNT-` |
| Two analyze response shapes | One merged shape (Section 7.5) |
| Memory statuses differ across documents | Use active, archived, expired, under_review, deleted. The `proposed` and `disputed` states are handled as `under_review` plus a proposal record. |
| Master DBD has `projects`, `sources`, `findings`, `export_jobs`; the DB spec and the code do not | Marked PROPOSED (Section 8.2) |
| Auth endpoints built but not in the old spec | Added from the code (Section 7.3) |
| Export said 7 models | Wrong. The code has 17 models. |
| Export said it could not find PRD to IPD | They exist as Master Baseline v1.0 and are merged here |
| Proposed technologies (React, pgvector, Redis, LiteLLM, MCP, Docker) listed as not established | Kept as BASELINE choices that can be replaced by adapters |
| Python 3.11+ vs 3.14 | Not a conflict. 3.11 is the minimum; 3.14 is the dev runtime. |
| Two taglines | OPEN (decision 21) |
| Migration 0011 failed on a fresh database | Fixed on 8 November 2026 and verified on SQLite |

## 15. Known issues, in priority order

1. Replace the `create_all` baseline in migration 0001 with explicit tables.
2. Add login rate limiting and equal-time login for unknown emails.
3. Add `UserSession` to the tenant guard map, and add composite tenant foreign keys.
4. Turn `api/security_smoke_test.py` into pytest with a temporary database, and run it in CI.
5. Install the API packages in CI so the Pydantic and Python 3.14 combination is tested.
6. Write audit events from the auth routes.
7. Make deletion cover version snapshots and embeddings.
8. Do not return `supported` from a reference string alone.
9. Make idempotency records able to replay responses.
10. Test the PostgreSQL upgrade path from revision 0010.
11. Settle the API prefix and response envelope.

## 16. Immediate next steps

1. Owner decides items 1, 2, 4 and 15 in Section 13.
2. Do issues 2 to 5 in Section 15.
3. Write the first Phase 2 pieces in the planned order, starting with the Bridge endpoint `POST /requests/analyze` and the Policy Engine.
4. Build a small evaluation dataset for Context Firewall and Assumption Killer.
5. Add the missing open-source files (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG).

---

This is a consolidated baseline. It does not replace a threat model, a benchmark, or a legal review before production use.
