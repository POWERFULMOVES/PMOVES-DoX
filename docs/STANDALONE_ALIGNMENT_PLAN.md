# PMOVES-DoX Standalone Alignment Plan

**Created:** 2026-01-14
**Updated:** 2026-01-14
**Status:** Draft - Pending Review
**Parent Repository:** [PMOVES.AI](https://github.com/POWERFULMOVES/PMOVES.AI)
**Target Branch:** `PMOVES.AI-Edition-Hardened-v3-clean`

---

## Executive Summary

This document outlines the plan to align PMOVES-DoX as a standalone repository while ensuring all features from the parent PMOVES.AI repository are present. The goal is to enable PMOVES-DoX to operate independently while maintaining compatibility with the PMOVES.AI ecosystem when "docked."

---

## PMOVES-DoX Open PRs Status

### Critical PRs Requiring Merge

| PR | Title | Commits | Status | Features |
|----|-------|---------|--------|----------|
| [#44](https://github.com/POWERFULMOVES/PMOVES-DoX/pull/44) | Environment Variables Integration | 74 | Open | Model Lab, A2UI, Geometry page, Neo4j, TensorZero |
| [#42](https://github.com/POWERFULMOVES/PMOVES-DoX/pull/42) | Dual-Mode Deployment | 19 | Open | Makefile, docker-compose.docked.yml, CI/CD |

### Features in PRs NOT in Local Branch

| Feature | PR | Local Status |
|---------|-----|--------------|
| `/modellab` page | #44 | **Missing** |
| `/a2ui` page | #44 | **Missing** |
| `/geometry` page | #42, #44 | **Missing** |
| `docker-compose.docked.yml` | #42 | **Missing** |
| `Makefile` (mode switching) | #42 | **Missing** |
| Neo4j integration | #44 | **Missing** |
| TensorZero env vars | #44 | **Missing** |
| NATS WebSocket config | #44 | **Missing** |
| CI/CD workflows | #42 | **Missing** |
| `CLAUDE.md`, `AGENT_GUIDE.md` | #44 | **Missing** |

### PR Review Issues to Address

See [PR_REVIEW_LEARNINGS.md](./PR_REVIEW_LEARNINGS.md) for complete catalog.

#### Open Issues (Not Yet Fixed)

| File | Issue | PR |
|------|-------|-----|
| `backend/app/api/routers/search.py:16` | Unsupported `threshold` parameter | #44 |
| `backend/app/api/routers/analysis.py:275` | `force_refresh` not forwarded | #44 |

#### Addressed Issues (Verify in Latest Commits)

| Category | Count | Status |
|----------|-------|--------|
| Security (hardcoded credentials) | 7 | Addressed |
| Environment variable expansion | 4 | Addressed |
| Build/config issues | 4 | Addressed |
| Frontend issues | 3 | Addressed |

---

## Current State Assessment

### Local Repository Status

- **Current Branch:** `feat/supabase-integration` (outdated)
- **Default Branch:** `PMOVES.AI-Edition-Hardened`
- **Needs:** Merge PRs #42 and #44

### PMOVES-DoX Repository Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend (FastAPI) | Complete | Python 3.10+, Docling, FAISS |
| Frontend (Next.js 14) | **Incomplete** | Missing new UI pages |
| Docker Configs | **Incomplete** | Missing docked mode |
| Database Layer | Complete | SQLite + Supabase support |
| Documentation | **Incomplete** | Missing critical docs |
| Claude CLI Integration | **Missing** | `.claude/` directory needed |
| CI/CD | **Missing** | No GitHub Actions workflows |

### Missing Documentation

| Document | Priority | Purpose |
|----------|----------|---------|
| `README.md` (root) | Critical | Project overview, quick start |
| `.claude/` directory | Critical | Claude Code CLI integration |
| `CONTRIBUTING.md` | High | Contribution guidelines |
| `SECURITY.md` | High | Security policies |
| `LICENSE` | High | Legal terms |
| `ARCHITECTURE.md` | Medium | System design overview |
| `API.md` | Medium | REST API documentation |
| `DEVELOPMENT.md` | Medium | Developer setup guide |
| `CHANGELOG.md` | Low | Version history |

---

## Parent Repository Analysis

### PMOVES.AI Branch Status

| Branch | Commits Ahead | Status |
|--------|---------------|--------|
| `PMOVES.AI-Edition-Hardened-v3-clean` | 193 (vs main) | Active, PR #483 open |
| `gpu-orchestrator-fixes` | 4 | GPU fixes NOT in v3-clean |
| `gpu-review-fixes` | 2 | Codex review feedback |
| `restore/main-files-to-v3-clean` | 1 | Restores 1,797 files |
| `revert/remove-transcribe-submodule` | 1 | Removes transcribe submodule |

### PR #483 Contents (193 commits)

Key components being merged to main:
- 26 critical stabilization commits
- 13 aligned submodules (including PMOVES-DoX)
- Security infrastructure (999-line architecture guide)
- PBnJ Kubernetes deployment system
- TAC (Tactical Agentic Coding) CLI integration
- A2UI NATS bridge for agent-to-user interface

---

## Learnings from PR Reviews

### Security Best Practices (from PR #42)

```yaml
NEVER_DO:
  - Hardcode credentials in docker-compose.yml
  - Commit passwords to source control
  - Use literal strings for API keys

ALWAYS_DO:
  - Use ${VARIABLE} substitution for secrets
  - Store credentials in .env files (gitignored)
  - Document required variables in .env.example
```

### Environment Variable Pattern

```yaml
# docker-compose.yml - CORRECT
DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

# docker-compose.yml - WRONG
DATABASE_URL: postgres://postgres:postgres@db:5432/app
```

### Frontend API Calls Pattern

```typescript
// WRONG - routes to Next.js API routes
fetch('/api/v1/data')

// CORRECT - uses backend URL
fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/data`)
```

### CI/CD Permissions Pattern

```yaml
# Always add explicit permissions
permissions:
  contents: read
  security-events: write
```

---

## Operational Modes

### Mode 1: Standalone

```yaml
Configuration: Local
Database: SQLite (backend/db.sqlite3)
Search: FAISS/NumPy
Ports: 8000 (API), 3001 (UI)
MCP Integration: No
Networks: Isolated
```

### Mode 2: Docked (PMOVES.AI Ecosystem)

```yaml
Configuration: Shared Ecosystem
Database: Supabase (DB_BACKEND=supabase)
Search: Qdrant via Hi-RAG
Ports: 8092 (ecosystem standard)
MCP Integration: Yes (Agent Zero)
Networks: pmoves_app, pmoves_bus
NATS: Real-time geometry bus updates
```

---

## Implementation Plan

### Phase 0: PR Merge & Sync (Immediate)

#### Task 0.1: Merge Open PRs
- [ ] Review and merge PR #44 (74 commits)
- [ ] Verify PR #42 changes included in #44
- [ ] Resolve any merge conflicts
- [ ] Update local branch to latest

#### Task 0.2: Address Open Review Comments
- [ ] Fix `search.py` - remove unsupported `threshold` parameter
- [ ] Fix `analysis.py` - forward `force_refresh` flag
- [ ] Verify all "addressed" security issues are actually fixed
- [ ] Run test suite after fixes

#### Task 0.3: Verify New Features Work
- [ ] Test `/modellab` page
- [ ] Test `/a2ui` page
- [ ] Test `/geometry` page
- [ ] Test `make standalone` command
- [ ] Test `make docked` command

---

### Phase 1: Critical Documentation (Week 1)

#### Task 1.1: Create Root README.md
- [ ] Project overview and description
- [ ] Feature list (PDF processing, table extraction, Q&A, vector search)
- [ ] Quick start guide (standalone mode)
- [ ] Docker deployment instructions
- [ ] Link to detailed documentation
- [ ] Badges (build status, license, version)

#### Task 1.2: Copy Claude CLI Configuration
Copy from `PMOVES.AI/.claude/` to `PMOVES-DoX/.claude/`:

| File/Directory | Size | Purpose |
|----------------|------|---------|
| `CLAUDE.md` | 12KB | Always-on context |
| `README.md` | - | CLI setup guide |
| `settings.json` | - | 131 allowed bash commands |
| `commands/` | 50+ | Custom slash commands |
| `context/` | 19 files | Reference documentation |
| `hooks/` | - | Pre/post tool scripts |

#### Task 1.3: Copy Standard Documents
- [ ] `CONTRIBUTING.md` - Contribution guidelines
- [ ] `SECURITY.md` - Security policies
- [ ] `LICENSE` - License terms

---

### Phase 2: Architecture Documentation (Week 2)

#### Task 2.1: Create ARCHITECTURE.md
- [ ] High-level architecture diagram
- [ ] Backend components (FastAPI, Docling, FAISS)
- [ ] Frontend components (Next.js, React)
- [ ] Data flow diagrams
- [ ] Database schema

#### Task 2.2: Create API.md
Document REST endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | File upload |
| `/api/facts` | GET | Facts retrieval |
| `/api/qa` | POST | Question/answer |
| `/api/search` | POST | Vector search |
| `/api/health` | GET | Health check |

---

### Phase 3: Development & Deployment (Week 3)

#### Task 3.1: Create DEVELOPMENT.md
- [ ] Prerequisites
- [ ] Local setup
- [ ] Environment variables
- [ ] Running tests

#### Task 3.2: Create DEPLOYMENT.md
- [ ] Docker standalone
- [ ] Docker docked mode
- [ ] Troubleshooting

#### Task 3.3: Verify Docker Configurations
- [ ] Test all compose variants
- [ ] Document any issues

---

### Phase 4: Integration & Testing (Week 4)

#### Task 4.1: Verify Feature Parity
- [ ] All features from PRs present
- [ ] No regressions

#### Task 4.2: CI/CD Setup
- [ ] GitHub Actions workflows
- [ ] Security scanning
- [ ] Dependabot

---

## Files to Copy from PMOVES.AI

### Priority 1: Critical

| Source | Destination | Action |
|--------|-------------|--------|
| `.claude/*` | `.claude/` | Copy + Adapt |
| `CONTRIBUTING.md` | `CONTRIBUTING.md` | Copy |
| `SECURITY.md` | `SECURITY.md` | Copy |
| `LICENSE` | `LICENSE` | Copy |

### Priority 2: Integration Guides

| Source | Destination |
|--------|-------------|
| `docs/MODULAR_ARCHITECTURE.md` | `docs/` |
| `pmoves/docs/ENVIRONMENT_SETUP.md` | `docs/` |

---

## Success Criteria

### PR Merge Complete
- [ ] PR #44 merged
- [ ] All review comments addressed
- [ ] New UI pages functional
- [ ] Dual-mode deployment works

### Standalone Operation
- [ ] `docker-compose up` starts without errors
- [ ] `make standalone` works
- [ ] All UI pages accessible
- [ ] Health endpoint returns OK

### Documentation Complete
- [ ] README provides clear quick-start
- [ ] All APIs documented
- [ ] Learnings documented

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PR merge conflicts | High | Careful review, test after merge |
| Open review issues | Medium | Address before merge |
| Missing features | High | Comprehensive testing |
| Security issues | High | Apply all security fixes |

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 0 | Now | PR merge, fix open issues |
| Phase 1 | Week 1 | README, .claude/, standard docs |
| Phase 2 | Week 2 | ARCHITECTURE, API docs |
| Phase 3 | Week 3 | DEVELOPMENT, DEPLOYMENT |
| Phase 4 | Week 4 | Tests, CI/CD |

---

## Review Checklist

- [ ] PRs #42 and #44 merged
- [ ] All review comments addressed
- [ ] Security issues fixed
- [ ] New UI pages tested
- [ ] Documentation complete
- [ ] Both modes (standalone/docked) work

---

## Related Documents

- [PR_REVIEW_LEARNINGS.md](./PR_REVIEW_LEARNINGS.md) - Catalog of learnings from PR reviews
- [ADVANCED_FEATURES_PLAN.md](../ADVANCED_FEATURES_PLAN.md) - Feature roadmap
- [PR #44](https://github.com/POWERFULMOVES/PMOVES-DoX/pull/44) - Environment Variables Integration
- [PR #42](https://github.com/POWERFULMOVES/PMOVES-DoX/pull/42) - Dual-Mode Deployment

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Author | Claude Code | 2026-01-14 | Draft |
| Reviewer | | | Pending |
| Approver | | | Pending |

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-14 | Claude Code | Initial draft |
| 2026-01-14 | Claude Code | Added PMOVES-DoX PR analysis, learnings section, Phase 0 |
