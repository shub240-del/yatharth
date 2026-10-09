# Yatharth AI — Digital Safety MVP

An independent Python 3.12 modular monolith proving the authorized-message → risk
analysis → caregiver alert → acknowledgement → resolution loop. No OpenWorker
installation, AI key, or messaging integration is required. OpenWorker was inspected
as machinery; Yatharth owns intelligence, consent, family context, risk and response.

**Internal prototype, not an emergency-response product or a validated fraud detector.**
Risk scores and confidence are uncalibrated decision-support indicators, not fraud probabilities.

## V0.2 evaluation

Read `docs/V0.2-VALIDATION-REPORT.md` first. The frozen detector misses96/161 provisionally serious challenge cases; all260 labels are synthetic and unreviewed. Product behavior is unchanged. `evaluation/v02/README.md` provides reproduction and independent-review commands. Current combined tests:198 passed,24 skipped,98 expected failures. Historical V0.1 evidence below is distinct from the fresh V0.2 SQLite run; fresh PostgreSQL/Docker checks were unavailable.

## Quick start with Docker

From this directory, with Docker Engine/Desktop and Compose installed:

```sh
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000 for the dashboard and http://localhost:8000/docs for
Swagger. Compose binds the web port to loopback; PostgreSQL is not published.
The default database password is for isolated local development. Set a strong
`POSTGRES_PASSWORD` (URL-safe characters) and `JWT_SECRET` before deployment.
An empty JWT secret generates an ephemeral per-process signing key; restarting
invalidates login tokens. Docker was **not executable in the build workspace**;
PostgreSQL itself and the application were tested directly. See `docs/HANDOFF.md`.

Run the explicitly synthetic demo in another terminal:

```sh
docker compose exec backend python -m app.demo --synthetic-consent
```

It creates fictitious Rajesh/Amit Gupta accounts, joins them to a family, grants
**synthetic-only** consent, submits low/medium/critical messages, verifies restricted
raw-message access, acknowledges/resolves the alert, verifies revocation, then restores
the synthetic grant. It prints generated demo login credentials. It never grants
consent for real people. No automatic seed runs at startup.

## Local Python start

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Windows PowerShell: activate with `.venv\Scripts\Activate.ps1`; use `python` if
that is your Python 3.12 command. Default storage is a local SQLite file. For
PostgreSQL set `DATABASE_URL=postgresql+psycopg://user:password@host:5432/database`.
Local Python does not load `.env` automatically: export variables in your shell;
Compose loads `.env` itself. Use one worker for SQLite and ephemeral signing keys.

```sh
python -m app.demo --synthetic-consent
pytest
python -m app.evaluation.run
python -m app.retention
```

The retention command erases raw content older than `RETENTION_DAYS` (default 30),
keeping minimal risk/audit metadata. Schedule it through your deployment's scheduler;
it is not automatically run by this prototype. Do not treat this as a complete
user-deletion or backup-retention policy.

## Manual Swagger walkthrough

1. `POST /api/v1/users`: create the caregiver with `name`, `email`, role `CAREGIVER`,
   and a password of at least 12 characters. Optional `phone`.
2. `POST /api/v1/auth/login` with email/password. Copy `access_token` into Swagger's
   **Authorize** bearer field (token only).
3. `POST /api/v1/families` with `{"name":"Gupta Family"}`. Save `id` and `join_code`.
   The creator is automatically a member. Use the members endpoint with your own
   `user_id` and `relationship: "Son"` to update the creator relationship.
4. Create Rajesh through `/users` with role `PROTECTED_PERSON`. Log in as Rajesh and
   replace the token in Authorize.
5. `POST /families/{id}/members` with Rajesh's `user_id`, `relationship: "Father"`,
   and the family `join_code`. Nobody can join on behalf of another account.
6. As Rajesh, `POST /consents` with `family_id`, `protected_person_id` and
   `scope: "DIGITAL_SAFETY"`. Keep `external_ai_allowed: false` for deterministic mode.
7. `POST /messages/analyze` with the family ID, Rajesh's sender ID, and content:
   - `Beta, I reached the market.` → LOW, no alert.
   - `I received a strange message from an unknown number.` → MEDIUM, no alert.
   - `Your bank account will be blocked today. Send ₹50,000 immediately.` → HIGH, alert.
   - See `app/evaluation/demo-messages.json` for 25 labeled demo messages.
8. Save `risk_event_id`, `message_id`, and `alert_id`. Read the persisted risk event.
9. Log back in as Amit. `GET /alerts`, then `GET /alerts/{id}`. Original message content
   is unavailable to the caregiver; only assigned risk summaries can be read.
10. `POST /alerts/{id}/acknowledge`, then `/resolve`. Optional `/feedback` stores
    `TRUE_RISK`, `FALSE_POSITIVE`, or `MISSED_RISK`; it does not retrain anything.
11. `GET /audit?family_id=...` shows the current account's action trail.
12. Log in as Rajesh; revoke the consent. The next analysis must return 403 and
    persist no message/risk/alert. Regrant explicitly to resume.

Real use requires a protected person to make the actual consent choice. Family
membership alone is never consent. Adding a caregiver revokes prior grants because
the audience changed; the parent must review the new family roster and regrant.

## Optional machinery

By default `LLM_ENABLED=false` and `OPENWORKER_ENABLED=false`.

For a separately authorized external classifier, set `LLM_ENABLED=true`,
`LLM_URL` to an HTTPS OpenAI-compatible chat-completions endpoint, `LLM_API_KEY`,
and `LLM_MODEL`. The protected person must separately opt into external AI use.
Without this extra grant no message leaves the rule engine. Missing credentials,
provider failures, malformed output and unknown signals fall back to rules.

`OpenWorkerScamClassifier` can wrap a ProviderClient-compatible client without
importing OpenWorker in the normal application. The optional lazy router wrapper
requires separately installed OpenWorker and its provider configuration. Set
`OPENWORKER_ENABLED=true` and `LLM_MODEL` only when configuring that path. The router
is built in a bounded child process; it receives no tools or family identifiers.
Real provider integrations were **not** credential-tested. Contract/failure tests
use fakes. If both provider flags are set and a complete LLM configuration exists,
the direct LLM path takes precedence. No core OpenWorker files are vendored.

## Documentation

- `docs/HANDOFF.md`: architecture, schema, threat model, privacy, results, limitations,
  technical debt, and V1.1/V2 recommendations.
- `research/openworker-assessment.md`: inspected commit and reuse decisions.
- `docs/openapi.json`: full machine-readable API reference; `/docs` is interactive.
- `docs/schema.sql`: generated PostgreSQL DDL for all entities.
- `docs/test-results.txt`, `docs/postgres-test-results.txt`: actual test runs.
- `docs/evaluation-results.txt`: all metrics and severity mismatches.
- `docs/http-demo-results.json`: sanitized live HTTP workflow evidence.

For the remaining Docker verification gate on a Docker-capable machine, run
`sh infrastructure/verify-docker.sh`. This starts Compose, runs tests and evaluation,
and exercises the actual PostgreSQL-backed HTTP demo using only fictitious data.
