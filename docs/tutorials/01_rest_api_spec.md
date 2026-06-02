# Tutorial 1: Specifying a REST API

## Introduction

This tutorial walks through the complete SpecForge lifecycle for a
real-world scenario: designing and specifying a REST API for a user
authentication service. By the end, you will have a project with:
- Ideas captured from stakeholder discussions
- Formal, verifiable requirements
- Architectural decisions with rationale
- Development tasks linked to requirements
- Test specifications written before implementation
- Verification evidence closing the loop
- An acceptance report ready for review

The scenario is a JWT-based authentication API that a small team is
building to replace a legacy session-based system.

---

## Part 1: Project setup and exploration

### Creating the project

Start by initialising the project with git tracking and a project name.
The name appears in reports and the status dashboard.

```bash
specforge init ./auth-api --git --name "User Auth API v2"
```

This creates the directory scaffold, initialises a git repository, and
writes a commented `.specforge.yaml`. Inspect the scaffold:

```bash
ls ./auth-api/
# exploration/  specification/  development/  trace/  .specforge.yaml
```

Configure the LLM provider for AI-assisted drafting:

```bash
specforge config ./auth-api --set llm.provider=anthropic
# Reads ANTHROPIC_API_KEY env var automatically
```

### Capturing ideas from a stakeholder meeting

The product team held a kickoff meeting. You have notes. Turn them
into SpecForge idea artifacts while the context is fresh:

```bash
specforge add-idea ./auth-api "JWT-based authentication" \
  "Replace session cookies with JWT tokens. Access tokens expire in 15 min,
  refresh tokens valid for 7 days. Enables stateless API scaling." \
  --tag auth

specforge add-idea ./auth-api "Token revocation" \
  "When a user logs out or changes their password, all existing tokens for
  that user should be invalidated immediately. Not possible with pure JWTs —
  needs a token blocklist or short-lived tokens only." \
  --tag auth --tag security

specforge add-idea ./auth-api "Rate limiting on auth endpoints" \
  "Prevent brute-force attacks on /login. Suggested: 5 attempts per minute
  per IP. Lockout mechanism after 20 failed attempts." \
  --tag security

specforge add-idea ./auth-api "OAuth 2.0 provider integration" \
  "Allow users to log in with Google and GitHub. Lower-priority for v2 —
  requested by one customer, not in the core spec." \
  --tag auth --tag future
```

**Why record ideas this way?** Ideas are cheap and fast to create.
Recording them in SpecForge means they are permanent, searchable, and
linked to the requirements that eventually come from them. The OAuth
idea, tagged `future`, becomes a traceable record that the feature was
considered and explicitly deferred — not forgotten.

### Using AI drafting for a rough idea

The engineering lead mentioned something about CORS configuration during
the meeting. You are not sure of the details yet. Use AI drafting to
create a structured idea artifact from your rough notes:

```bash
specforge draft ./auth-api idea \
  "CORS configuration: the auth API needs to specify which origins can
  call it, with different rules for production and development environments" \
  --title "CORS configuration policy"
```

SpecForge calls the LLM, generates a structured idea body, and shows
it to you. Review, accept, and the idea is created. The AI handles the
blank-page problem; you handle the review.

---

## Part 2: Specification

### Evaluating and promoting candidates

After the meeting, review the ideas and decide which ones belong in
v2 of the spec. Promote the ones that pass evaluation:

```bash
specforge promote ./auth-api IDEA-0001 candidate \
  --text "JWT tokens confirmed as the right approach by the lead architect.
  Stateless authentication is required for the horizontal scaling plan.
  Implementation feasibility confirmed with the platform team." --git

specforge promote ./auth-api IDEA-0002 candidate \
  --text "Token revocation is required by the security team — it is a
  compliance requirement for SOC 2. The pure-JWT approach is insufficient.
  We will implement a Redis blocklist for revoked token IDs." --git

specforge promote ./auth-api IDEA-0003 candidate \
  --text "Rate limiting confirmed as required by security review.
  Threshold and lockout values need refinement with the security team."
```

Explicitly reject the OAuth idea for this version with a reason:

```bash
specforge update-status ./auth-api IDEA-0004 rejected
specforge edit ./auth-api IDEA-0004
# In the editor, add to the body:
# Rejected for v2: insufficient customer demand to justify scope.
# Will be revisited in v3 planning.
```

**Why explicit rejection matters**: an idea that was considered and
rejected is more valuable than an idea that was ignored. The rejection
reason prevents the same conversation happening again in three months.

### Writing formal requirements

With candidates approved, write formal requirements. Good requirements
are unambiguous, verifiable, and atomic. Note how each requirement
includes specific, measurable criteria:

```bash
specforge add-req ./auth-api "JWT access token expiry" \
  --text "The authentication service shall issue JSON Web Tokens (JWT,
  RFC 7519) as access tokens. Access tokens shall have a maximum lifetime
  of 15 minutes from the time of issuance. Clients shall treat a token as
  invalid upon or after its 'exp' claim time, with no grace period.

  Acceptance criteria:
  - An access token issued at time T is rejected by protected endpoints
    at time T+15m+1s
  - Token payload includes: sub (user ID), iat, exp, jti (unique ID)
  - Token is signed with RS256 (asymmetric, so public key can verify)" \
  --source CAND-0001 --tag auth --git

specforge add-req ./auth-api "Refresh token lifecycle" \
  --text "The authentication service shall issue opaque refresh tokens
  alongside each access token. Refresh tokens shall:
  - Have a maximum lifetime of 7 days from issuance
  - Be single-use: exchanging a refresh token for a new access token
    invalidates the used refresh token and issues a new refresh token
  - Be stored server-side with the associated user ID and expiry
  - Be revocable by user logout or password change

  Acceptance criteria:
  - A refresh token works exactly once; the second use returns 401
  - Refresh tokens older than 7 days are rejected with 401
  - After logout, the refresh token is rejected with 401" \
  --source CAND-0002 --tag auth --git

specforge add-req ./auth-api "Rate limiting on authentication endpoints" \
  --text "The POST /auth/login endpoint shall be rate-limited per source
  IP address. Limits:
  - Maximum 5 requests per 60-second rolling window per IP
  - Requests exceeding the limit receive HTTP 429 Too Many Requests
  - Response includes Retry-After header indicating seconds until reset
  - After 20 failed login attempts in 1 hour, the IP is locked out
    for 1 hour regardless of the rate limit window

  Acceptance criteria:
  - The 6th request within 60 seconds from one IP returns 429
  - The Retry-After header is present and accurate
  - IP lockout activates correctly after 20 failures" \
  --source CAND-0003 --tag security --git
```

### Recording decisions

Every non-obvious technical choice needs a decision artifact. Decisions
explain the *why* — they are the most valuable artifact to future team
members and to your future self.

```bash
specforge add-decision ./auth-api "RS256 for JWT signing" \
  --text "Access tokens are signed with RS256 (RSASSA-PKCS1-v1_5 using
  SHA-256) rather than HS256 (HMAC-SHA256).

  Rationale:
  RS256 uses an asymmetric key pair. The private key signs tokens
  (held only by the auth service); the public key verifies them
  (shared with all services that need to verify tokens). This means:

  1. Other services can verify tokens without sharing a secret key,
     which would create a security risk if any service were compromised.
  2. Token verification is possible without network calls — services
     cache the public key and verify locally.
  3. Key rotation can be phased: distribute new public key before
     switching signing to new private key.

  HS256 was rejected because sharing the HMAC secret with all consuming
  services creates a secret management problem and a blast radius if
  any service is compromised.

  Risk: RS256 signing is 10-30x slower than HS256. Acceptable given
  that token issuance (sign) happens once per login; verification
  happens on every request but is CPU-cheap with cached public key." \
  --req REQ-0001 --git

specforge add-decision ./auth-api "Redis for token storage" \
  --text "Refresh tokens and the revocation blocklist are stored in
  Redis rather than PostgreSQL.

  Rationale:
  1. TTL-based expiry: Redis natively expires keys after a set duration.
     PostgreSQL would require a background job to clean up expired tokens.
  2. Performance: token lookup on every request must be sub-millisecond.
     Redis typically answers in <1ms; PostgreSQL in 1-5ms under load.
  3. Simplicity: the data model for tokens (key → value with TTL) is
     a natural Redis use case.

  Risk: Redis is an additional operational dependency. Mitigation: Redis
  is already in the infrastructure stack for caching.

  PostgreSQL was evaluated and rejected due to TTL management overhead
  and higher latency." \
  --req REQ-0002 --git

specforge add-assumption ./auth-api "Redis 6+ available in all environments" \
  --text "The deployment specification requires Redis 6.0 or later.
  This is required for the SET NX EX atomic token storage command and
  for GETDEL (used in single-use refresh token implementation).
  Environments: dev (Docker), staging (managed Redis), prod (managed Redis).
  Verified: dev and staging confirmed. Production: pending ops confirmation." \
  --req REQ-0002

specforge add-constraint ./auth-api "No third-party auth-as-a-service" \
  --text "The authentication system must be self-hosted. Services such as
  Auth0, Okta, or Cognito are prohibited by the enterprise security
  policy. All token generation, storage, and validation must run on
  company-controlled infrastructure." \
  --req REQ-0001 --req REQ-0002
```

---

## Part 3: Implementation tracking

### Creating tasks linked to requirements

Each task should implement one or more requirements. Use the
`--implements` flag to create the traceability link at creation time.

```bash
specforge add-task ./auth-api "Implement JWT issue endpoint" \
  --text "Build POST /auth/login endpoint:
  - Accept {email, password} JSON body
  - Validate credentials against users table
  - On success: issue access token (RS256, 15 min) and refresh token
    (opaque, store in Redis, 7 days)
  - Return {access_token, refresh_token, expires_in: 900}
  - On failure: return 401 with generic error (do not reveal if email
    or password was wrong)
  - Apply rate limiting via the middleware from TASK-0003

  Exit criteria: integration test passes, rate limit middleware hooked in" \
  --implements REQ-0001 --implements REQ-0002 --tag auth --git

specforge add-task ./auth-api "Implement token refresh endpoint" \
  --text "Build POST /auth/refresh endpoint:
  - Accept {refresh_token} JSON body
  - Look up token in Redis; if not found or expired, return 401
  - Use GETDEL to atomically retrieve and delete (single-use enforcement)
  - Issue new access token and new refresh token
  - Store new refresh token in Redis with 7-day TTL

  Exit criteria: unit tests cover single-use enforcement, expiry" \
  --implements REQ-0002 --depends-on TASK-0001 --tag auth --git

specforge add-task ./auth-api "Implement rate limiting middleware" \
  --text "Build Express/FastAPI middleware for rate limiting:
  - Sliding window counter in Redis using ZADD/ZCOUNT
  - Check window before handling request; increment after
  - If count >= 5 in 60s window: return 429 with Retry-After header
  - Lockout: separate key tracks failed attempts; after 20, lock for 1h

  Exit criteria: unit tests verify counting logic, 429 response,
  Retry-After header calculation" \
  --implements REQ-0003 --tag security --git

specforge add-task ./auth-api "Implement logout and token revocation" \
  --text "Build POST /auth/logout endpoint:
  - Accept Authorization header with access token
  - Add token JTI to Redis blocklist with TTL equal to remaining token
    lifetime (so the entry expires when the token would have expired)
  - Delete refresh token from Redis

  Exit criteria: after logout, both access token (until natural expiry
  of blocklist entry) and refresh token are rejected" \
  --implements REQ-0002 --depends-on TASK-0001 --tag auth --git
```

### Tracking implementation progress

```bash
# Rate limiting middleware is done first (others depend on it)
specforge update-status ./auth-api TASK-0003 implemented --git

# Login endpoint is next
specforge update-status ./auth-api TASK-0001 implemented --git

# Then refresh and logout
specforge update-status ./auth-api TASK-0002 implemented --git
specforge update-status ./auth-api TASK-0004 implemented --git

# Mark requirements implemented
specforge bulk ./auth-api update-status \
  --kind requirement --status approved --to implemented
```

---

## Part 4: Verification

### Writing test specifications before running tests

Write test specifications while the requirements are fresh — before
implementation begins if possible. The act of writing tests exposes
ambiguities in requirements (if you cannot write a test, the
requirement may not be verifiable).

```bash
specforge add-test ./auth-api "JWT expiry enforcement" \
  --text "
## Objective
Verify REQ-0001: access tokens expire at or before 15 minutes from issuance.

## Setup
- Auth service running with 15-minute access token lifetime
- Test user account created

## Steps
1. POST /auth/login with valid credentials → save access_token
2. Decode token, verify exp = iat + 900 (±2 seconds for clock skew)
3. Wait 901 seconds (or mock time to T+901)
4. POST to a protected endpoint with the expired token
5. Observe response

## Expected result
- Step 2: exp claim is within 900-902 seconds of iat
- Step 4: HTTP 401 Unauthorized
- Step 4: Response body: {'error': 'token_expired'}

## Tooling
pytest + freezegun for time mocking" \
  --req REQ-0001 --git

specforge add-test ./auth-api "Refresh token single-use enforcement" \
  --text "
## Objective
Verify REQ-0002: refresh tokens are single-use (second use returns 401).

## Steps
1. Login → obtain refresh_token_1
2. POST /auth/refresh with refresh_token_1 → obtain access_token_2, refresh_token_2
3. POST /auth/refresh with refresh_token_1 again
4. Observe response

## Expected result
- Step 2: 200 OK, new tokens returned
- Step 3: 401 Unauthorized (token already used)
- Verify Redis: refresh_token_1 key no longer exists after step 2" \
  --req REQ-0002 --git

specforge add-test ./auth-api "Rate limit 429 response" \
  --text "
## Objective
Verify REQ-0003: 6th login attempt within 60s returns 429 with Retry-After.

## Steps
1. POST /auth/login (attempt 1-5) from same IP within 60s
2. POST /auth/login (attempt 6) within the same 60s window
3. Check response code and headers
4. Wait until window expires (60s from attempt 1)
5. POST /auth/login again

## Expected result
- Steps 1-5: each returns 200 (or 401 for wrong password — not rate limited)
- Step 6: HTTP 429 with Retry-After header (value 1-60)
- Step 5 after window: request is processed normally (not 429)" \
  --req REQ-0003 --git
```

### Recording verification evidence

After QA and CI run the tests:

```bash
specforge add-verification ./auth-api "JWT expiry — CI green" \
  --text "
## Result: PASS

Date:    2026-06-02
Build:   #247 (main, commit 6c9ea04)
Environment: Ubuntu 22.04, Python 3.12, Redis 7.2
Tester:  CI pipeline

## Test results
jwt_expiry_enforcement: PASS
  - exp claim verified: iat + 900s ✓
  - Expired token returns 401 ✓
  - Error body matches spec ✓

## Notes
Used freezegun to mock time; no 900s wait required.
Log: https://ci.example.com/builds/247" \
  --req REQ-0001 --test TEST-0001 --git

specforge add-verification ./auth-api "Refresh token single-use — CI green" \
  --text "Result: PASS. Build #247. All three assertions pass: 200 on first
  use, 401 on second use, Redis key absent after first use. Full log at CI." \
  --req REQ-0002 --test TEST-0002 --git

specforge add-verification ./auth-api "Rate limiting — CI green" \
  --text "Result: PASS. Build #247. 429 returned on 6th attempt. Retry-After
  header present and accurate (value 58s in test). Window reset confirmed." \
  --req REQ-0003 --test TEST-0003 --git

# Mark requirements verified
specforge bulk ./auth-api update-status \
  --kind requirement --status implemented --to verified --git
```

---

## Part 5: Release

### Release gate check

```bash
specforge check ./auth-api
```

Expected output:
```
Release Gate: PASS ✅
All 3 requirements verified.
No open tasks.
```

If anything fails, the output is specific:
```
Release Gate: FAIL ❌
Unverified requirements:
  REQ-0003: Rate limiting on authentication endpoints

Open tasks:
  (none)
```

### Generating release artefacts

```bash
specforge report ./auth-api \
  --output ./auth-api/ACCEPTANCE_REPORT.md

specforge export ./auth-api
# Creates: trace/exports/traceability.md, trace/exports/traceability.csv

specforge context-pack ./auth-api \
  --output ./auth-api/CONTEXT_PACK.json
```

### Final project state

```bash
specforge status ./auth-api
```

```
Project: User Auth API v2
Release Gate: ✅ PASS

Artifacts (22 total)
  idea:         4 (1 draft, 2 archived, 1 rejected)
  candidate:    3 (all archived)
  requirement:  3 (all verified)
  decision:     2 (all approved)
  assumption:   1 (draft)
  constraint:   1 (draft)
  task:         4 (all archived)
  test:         3 (all draft)
  verification: 3 (all verified)

Open tasks: (none)
Unverified requirements: (none)
```

---

## Summary

This tutorial demonstrated the full SpecForge lifecycle:

1. **Exploration**: captured ideas from a meeting, used AI drafting for
   a rough concept, explicitly rejected a deferred feature
2. **Specification**: promoted candidates to formal requirements with
   measurable acceptance criteria; recorded decisions with rationale
   and alternatives; documented assumptions and constraints
3. **Implementation**: created linked tasks with clear exit criteria;
   tracked progress with status updates
4. **Verification**: wrote test specifications before testing; recorded
   evidence with build numbers and environment details
5. **Release**: confirmed the gate, generated artefacts

The result is a project where every requirement is traceable to its
origin, every implementation decision is explained, and every
verification claim has documented evidence. Six months from now, a new
team member can read the project history and understand not just what
was built, but why every choice was made.
