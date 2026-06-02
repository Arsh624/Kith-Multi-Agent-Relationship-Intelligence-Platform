# Kith, Relationship Intelligence Platform

**Design spec** · 2026-06-11

## 1. Purpose

A personal relationship-intelligence app that remembers the people you meet so you
don't have to. You feed it messages (Gmail automatically; LinkedIn or WhatsApp by
pasting). AI reads each message and extracts **people, the companies they're tied to,
and open "threads"** (for example, "offered to intro me to X", or "email them next week
about the PM role"). It stores this as a **graph** of your network plus a **searchable
memory**, and every morning surfaces **who to follow up with, why, and a ready-to-send
draft.**

The builder is the primary user (an active job-seeker and networker). The system is
designed to be multi-user-ready with bring-your-own-key (BYOK) so others can run it on
their own API credits.

### Success criteria
- Paste or sync a real message, and the correct people, companies, and threads are extracted.
- The Map shows your real network (companies with people branching off).
- The Good Morning tab gives a genuinely useful daily follow-up list with drafts.
- Runs at **$0/month** for the builder (Gemini free tier plus local Docker); roughly $5/mo
  only if and when hosted live.
- Every architectural choice (3 databases, agent layer, auth, evals) is justified by a
  real product need, defensible in a 15-minute interview.

## 2. Scope

### v1 (build now)
- **Capture:** Gmail auto-sync plus a "paste anything" box.
- **Extraction to graph:** raw text becomes structured facts stored in Postgres and Neo4j
  (plus a Qdrant embedding pipeline).
- **Tab 1, Good Morning:** ranked follow-ups (who, why, draft).
- **Tab 2, The Map:** companies (logo plus name) with people branching off; click for detail.

### Later (explicitly deferred)
- Smart "who can help with Stripe?" semantic search (pipeline built in v1, feature exposed later).
- Business-card and voice-note ingestion.
- Real LinkedIn and WhatsApp automation (paste-in only for now).
- Multi-user accounts beyond the single builder.

## 3. Architecture

### Frontend (Vercel)
- Next.js and React. Two tabs: Good Morning (follow-up cards) and The Map (interactive graph).
- Graph rendering: **Cytoscape.js**.

### Backend (FastAPI, Python)
- REST API; **JWT auth**; per-user encrypted storage of API keys and Gmail OAuth tokens.

### Agent layer (LangGraph)
A pipeline of cooperating agents:
1. `Extractor`: raw text becomes people, companies, and promises (structured JSON).
2. `Resolver`: is this a new person or one already known? (dedupe via Postgres and Qdrant).
3. `Graph-writer`: merge facts into Neo4j; embed the message into Qdrant.
4. `Follow-up engine`: detect open threads and timing, then create a task plus a draft message.

Wrapped with **Langfuse** observability (per-step traces) and an **eval set** (fixed
sample emails with known-correct answers, scored on every prompt change).

### Databases (each with a distinct job)
- **Postgres:** source of truth, holding `users`, `messages` (raw plus processed flag),
  `people`, `companies`, `threads` (follow-ups).
- **Neo4j:** the network itself, with `Person` and `Company` nodes and `WORKS_AT`,
  `KNOWS`, `REFERRED`, `CAN_INTRO` edges. Powers the Map and "warm path" queries.
- **Qdrant:** vector search, one embedding per message and per person for semantic recall.

Postgres is authoritative; **Neo4j and Qdrant are derived** and can be rebuilt from
Postgres at any time.

### LLM
- **Gemini** (free tier) behind a provider-agnostic interface. BYOK lets other users plug
  in Claude, OpenAI, or others on their own credits.

### Ingestion
- Gmail API (OAuth) for auto-sync; a `/paste` endpoint for LinkedIn, WhatsApp, and manual notes.

### Packaging and deployment
- One `docker-compose` for backend plus the 3 databases. Local-first, then deploy at the
  end: **Vercel** (frontend) plus a small **VPS** (around $5/mo, backend and databases via Docker).

## 4. Data flow (worked example)

Incoming email from *Priya Sharma*: "I'm a PM at Stripe. My friend Ravi leads recruiting
at Notion, ping me next week and I'll intro you."

1. **Capture:** saved raw in Postgres `messages` with `processed = false`.
2. **Extractor:** People: Priya (PM, Stripe), Ravi (recruiting, Notion); Companies:
   Stripe, Notion; Thread: `{intro_offer, ping next week, due ~+7d}`.
3. **Resolver:** known person or new? (Postgres plus Qdrant semantic match), then create or enrich.
4. **Graph-writer:** Neo4j edges (`Priya-WORKS_AT->Stripe`, `Ravi-WORKS_AT->Notion`,
   `You-KNOWS->Priya`, pending `Priya-CAN_INTRO->Ravi`); embed message into Qdrant.
5. **Follow-up engine:** Postgres task "Ping Priya re: Ravi/Notion intro, due +7d" plus a
   pre-drafted message.
6. **Morning:** Tab 1 shows the ranked card; Tab 2 shows new Stripe and Notion nodes plus a
   dotted "intro available" edge.
7. **Behind the scenes:** every step traced in Langfuse; the eval set guards extraction accuracy.

**Key choice:** raw text is persisted *before* processing (ingest, then queue, then
process). If extraction is wrong, re-run without re-fetching; if an agent crashes,
nothing is lost.

## 5. Data model (summary)

**Postgres**
- `users`: credentials, encrypted API keys, Gmail tokens.
- `messages`: raw text, source, `processed` flag, timestamps.
- `people`: name, title, current company, notes, source-message links.
- `companies`: name, domain, logo URL.
- `threads`: type, who and what, due date, status, draft.

**Neo4j:** `Person` and `Company` nodes; `WORKS_AT`, `KNOWS`, `REFERRED`, `CAN_INTRO` edges.

**Qdrant:** one vector per message and per person.

## 6. Build phases

- **Phase 0, Skeleton:** repo, `docker-compose` (Postgres, Neo4j, Qdrant, FastAPI),
  health check, JWT auth. Login works; the stack runs.
- **Phase 1, Capture and Extract:** `/paste` feeds the Extractor (Gemini), which writes to
  Postgres. Paste an email, see structured people and companies. Gmail auto-sync is layered
  on after paste works.
- **Phase 2, Graph:** Resolver and Graph-writer populate Neo4j. The Map tab renders the network.
- **Phase 3, Follow-ups:** the Follow-up engine plus the Good Morning tab. A daily to-do list
  with drafts.
- **Phase 4, Production polish:** Langfuse observability, the eval set, the Qdrant embedding
  pipeline, a README, and an architecture diagram.
- **Phase 5, Deploy:** Vercel (frontend) plus a VPS (backend), live URL.

Each phase is independently demoable and commit-worthy.

## 7. Tech defaults

| Layer | Choice |
|-------|--------|
| Frontend | Next.js plus Cytoscape.js |
| Backend | FastAPI plus LangGraph |
| LLM | Gemini (free tier), provider-agnostic and BYOK |
| Databases | Postgres, Neo4j, Qdrant |
| Observability | Langfuse |
| Packaging | Docker Compose |
| Hosting | Vercel (frontend) plus VPS (backend) |

## 8. Resume-matrix coverage

AI, Multi-Agent, LangGraph, RAG, Context Engineering, Vector Search, Backend,
Security (JWT), Databases (Postgres, Neo4j, Qdrant), Cloud, Docker, Observability,
Evals, Multimodal (later: cards and voice), and Product Thinking. Each is tied to a real
feature, not a checklist.
