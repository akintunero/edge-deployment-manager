# Production roadmap (3 phases)

## Phase 1 — Security & trust

**Goal:** Hostile-network baseline with operable secret handling and certificate lifecycle.

| Item | Deliverable |
|------|-------------|
| Secrets | `SecretProvider` (env, file, Docker secrets mount) |
| API rate limits | Global limiter on authenticated control plane routes |
| Distributed replay | Redis-backed nonce store (optional; sqlite/memory remain) |
| Cert rotation | `POST /v1/devices/{id}/certificates/rotate` + operator script |
| Docs | `docs/guides/security-operations.md` |

**Exit criteria:** Unit tests green; rotation and rate limits documented; Redis replay configurable.

---

## Phase 2 — HA control plane

**Goal:** Multiple control plane replicas with shared state and safe command issuance.

| Item | Deliverable |
|------|-------------|
| Registry | PostgreSQL backend + migrations |
| Leader election | Single active command publisher (DB advisory lock or lease) |
| MQTT | Shared mTLS client credentials via secrets volume |
| Compose/Helm | Postgres + 2× control plane smoke layout |

**Exit criteria:** Two replicas share registry; only leader publishes commands; failover tested.

---

## Phase 3 — Production deploy & OSS bar

**Goal:** Installable, testable, publishable full stack.

| Item | Deliverable |
|------|-------------|
| Helm | Full stack: Mosquitto, control plane, agent |
| E2E CI | Docker Compose job: enroll → signed deploy |
| OSS | README accuracy, architecture doc, committed `requirements.lock` |
| Release | PyPI trusted publishing checklist |
| Tests | Remove/fix legacy tests; coverage artifact upload |

**Exit criteria:** `helm install` brings up stack; CI e2e green; tag publishes to PyPI.

---

## Current status

- **Phase 1:** Complete
- **Phase 2:** Complete
- **Phase 3:** Complete
