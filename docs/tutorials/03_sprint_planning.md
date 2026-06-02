# Tutorial 3: Agile Sprint Planning with SpecForge

## Introduction

This tutorial shows how SpecForge fits into an agile team's sprint
process. Many teams believe that structured requirements management
and agile development are in tension — that requirements docs are
a waterfall relic, incompatible with iterative delivery. This is a
false dichotomy.

Agile does not mean "no requirements". It means requirements are
refined iteratively, at the appropriate level of detail, just in time.
SpecForge supports this: you capture rough ideas during discovery,
formalise them into requirements sprint by sprint, and maintain a
living, traceable record that a team of 10 can navigate as easily as
a team of 1.

The scenario: a mobile app team starting Sprint 12, with three features
coming off the backlog into active development.

---

## Part 1: Project setup and backlog preparation

### Project state entering Sprint 12

The project already has a history: requirements from earlier sprints,
linked decisions, a set of verified requirements from Sprint 11.

```bash
specforge status ./mobile-app
```

```
Project: Mobile App
Release Gate: ✅ PASS (Sprint 11 scope)

Artifacts (67 total)
  requirement:  15 (8 verified, 4 approved, 3 draft)
  task:         24 (20 archived, 4 draft)
  test:         8 (8 draft)
  verification: 8 (8 verified)
  idea:         12 (5 archived, 3 rejected, 4 draft)
  decision:     8 (all approved)

Open tasks: (none)
Unverified requirements: (none — Sprint 11 scope only)
```

Sprint 11 scope is clean. The release gate passes for the shipped
features. Now begin Sprint 12.

### Pulling features from the backlog

The product manager has prioritised three features for Sprint 12.
These exist as approved requirements in the backlog:

```bash
specforge list ./mobile-app --kind requirement --status approved
# REQ-0009: Offline feed reading
# REQ-0010: Push notification opt-in
# REQ-0011: Profile photo upload
```

Tag these for Sprint 12:

```bash
specforge bulk ./mobile-app tag-add \
  --kind requirement \
  --status approved \
  --tag backlog \
  --add-tag sprint-12
```

Review the requirements before sprint planning:

```bash
specforge show ./mobile-app REQ-0009
specforge show ./mobile-app REQ-0010
specforge show ./mobile-app REQ-0011
```

### Refining requirements during sprint planning

During the sprint planning meeting, the team notices that REQ-0009
(Offline feed reading) is too broad. It needs to be split: the offline
read capability and the sync-on-reconnect behaviour are separate
concerns with potentially separate implementations.

```bash
# Update REQ-0009 to be offline-read only
specforge edit ./mobile-app REQ-0009
# Edit body to scope it to: "The app shall serve cached feed content
# when no network connection is available, using the most recently
# cached data (up to 50 items)."

# Create REQ-0016 for sync
specforge add-req ./mobile-app "Feed sync on reconnect" \
  --text "When a network connection is restored after being offline,
  the app shall synchronise the feed cache with the server within 30
  seconds of connection detection. No data entered offline shall be
  lost during sync." \
  --source REQ-0009 --tag sprint-12
```

The `--source REQ-0009` link records that REQ-0016 was derived from the
original REQ-0009 scope. This is traceability at the requirement level.

---

## Part 2: Sprint task creation with AI drafting

### Using AI to generate task bodies

Sprint planning is a good time to use AI drafting. The team knows what
needs to be built; the AI helps write the structured task body that
would otherwise consume 10 minutes per task.

```bash
specforge draft ./mobile-app task \
  "Implement SQLite offline cache for feed items — store the last 50
  posts with images, update on successful network fetch, serve from cache
  when network unavailable. Android and iOS platforms." \
  --title "Feed offline cache implementation" \
  --tag sprint-12 --tag platform-mobile
```

The AI generates a structured task body with implementation notes,
exit criteria, and platform considerations. Review it, accept it, and
it becomes TASK-0025.

```bash
specforge link ./mobile-app TASK-0025 --implements REQ-0009

specforge draft ./mobile-app task \
  "iOS push notification permission prompt on first launch — native
  UNUserNotificationCenter request, respect user preference, provide
  in-app settings deep-link, remember choice in UserDefaults." \
  --title "Push notification opt-in (iOS)" \
  --tag sprint-12 --tag platform-ios

specforge link ./mobile-app TASK-0026 --implements REQ-0010

specforge draft ./mobile-app task \
  "Android push notification permission prompt — runtime permission
  request for Android 13+ (POST_NOTIFICATIONS), graceful degradation
  on older versions, notification channel setup." \
  --title "Push notification opt-in (Android)" \
  --tag sprint-12 --tag platform-android

specforge link ./mobile-app TASK-0027 --implements REQ-0010

specforge draft ./mobile-app task \
  "Profile photo upload — presigned S3 URL flow: client requests URL
  from server, uploads directly to S3, sends confirmation to server.
  Limit: 5MB JPEG/PNG. Client-side resize to 1024px before upload." \
  --title "Profile photo upload" \
  --tag sprint-12 --tag platform-mobile

specforge link ./mobile-app TASK-0028 --implements REQ-0011
```

### Reviewing the sprint board

```bash
specforge list ./mobile-app \
  --kind task --status draft --tag sprint-12
```

```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ ID           ┃ Title                               ┃ Status   ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ TASK-0025    │ Feed offline cache implementation   │ draft    │
│ TASK-0026    │ Push notification opt-in (iOS)      │ draft    │
│ TASK-0027    │ Push notification opt-in (Android)  │ draft    │
│ TASK-0028    │ Profile photo upload                │ draft    │
└──────────────┴─────────────────────────────────────┴──────────┘
```

Set tasks to `proposed` at sprint start to indicate active work:

```bash
specforge bulk ./mobile-app update-status \
  --kind task --status draft --tag sprint-12 --to proposed
```

---

## Part 3: Mid-sprint

### Tracking progress

The backend engineer finishes the photo upload service first:

```bash
specforge update-status ./mobile-app TASK-0028 implemented
```

Two days into the sprint, the offline cache is done:

```bash
specforge update-status ./mobile-app TASK-0025 implemented
specforge update-status ./mobile-app REQ-0009 implemented
```

A bug is discovered during iOS review: the notification prompt shows
on the second launch, not the first. Create a task to fix it:

```bash
specforge add-task ./mobile-app "Fix notification prompt — first launch only" \
  --text "Prompt shows on second launch instead of first. Root cause:
  launch check runs before UserDefaults migration on fresh install.
  Fix: move migration to app init, before the onboarding check." \
  --implements REQ-0010 \
  --depends-on TASK-0026 \
  --tag sprint-12 --tag bug
```

### Mid-sprint status check

```bash
specforge status ./mobile-app
```

```
Project: Mobile App
Release Gate: ❌ FAIL

Artifacts (sprint-12 scope)
  ...

Open tasks:
  TASK-0026 [proposed]: Push notification opt-in (iOS)
  TASK-0027 [proposed]: Push notification opt-in (Android)
  TASK-0029 [draft]:    Fix notification prompt — first launch only

Unverified requirements:
  REQ-0009: Offline feed reading
  REQ-0010: Push notification opt-in
  REQ-0011: Profile photo upload
```

This is expected mid-sprint. The gate shows exactly what remains.

---

## Part 4: Sprint close

### End-of-sprint work

After all features are implemented and tested:

```bash
# Mark remaining tasks implemented
specforge update-status ./mobile-app TASK-0026 implemented
specforge update-status ./mobile-app TASK-0027 implemented
specforge update-status ./mobile-app TASK-0029 implemented
specforge update-status ./mobile-app REQ-0010 implemented
specforge update-status ./mobile-app REQ-0011 implemented

# Write tests
specforge add-test ./mobile-app "Offline feed — airplane mode" \
  --text "Enable airplane mode. Open app. Assert feed shows cached
  content (50 items). Assert no network error message shown." \
  --req REQ-0009

specforge add-test ./mobile-app "Push opt-in — first launch" \
  --text "Fresh install on iOS 17 device. Launch app. Assert notification
  permission prompt appears during onboarding flow (step 3 of 4).
  Decline. Assert no repeat on second launch. Enable in Settings.
  Assert push notification received." \
  --req REQ-0010

specforge add-test ./mobile-app "Photo upload — 4MB JPEG" \
  --text "Profile screen. Tap photo. Select 4MB JPEG from photo library.
  Assert progress indicator shown. Assert photo appears in profile
  within 10 seconds. Assert same photo appears after app restart." \
  --req REQ-0011

# Record QA results
specforge add-verification ./mobile-app "Offline feed — QA passed" \
  --text "QA: iOS 17 and Android 14. Airplane mode test: 50 items cached,
  no error message. Sync on reconnect: new items appear within 15s of
  reconnection. Build 3.12.0 (Sprint 12). Tester: QA team, 2026-06-02." \
  --req REQ-0009 --test TEST-0009

specforge add-verification ./mobile-app "Push opt-in — QA passed" \
  --text "QA: iOS 17 fresh install and Android 14. First-launch prompt
  confirmed on both platforms. Second-launch: no repeat prompt.
  Deep-link to Settings verified. Build 3.12.0. Tester: QA team." \
  --req REQ-0010 --test TEST-0010

specforge add-verification ./mobile-app "Photo upload — QA passed" \
  --text "4MB JPEG uploaded in 3.2s (WiFi), 8.1s (4G). Image persists
  across restart. CDN URL verified. Edge case: 5.1MB file rejected with
  'File too large' message. Build 3.12.0. Tester: QA team." \
  --req REQ-0011 --test TEST-0011

# Mark requirements verified
specforge bulk ./mobile-app update-status \
  --kind requirement --status implemented --tag sprint-12 --to verified
```

### Sprint close automation

Archive all completed sprint-12 tasks:

```bash
specforge bulk ./mobile-app archive \
  --kind task --status implemented --tag sprint-12
```

Verify the gate passes for sprint-12 scope:

```bash
specforge check ./mobile-app
# Release Gate: PASS ✅
```

Generate the sprint review report:

```bash
specforge report ./mobile-app \
  --output ./mobile-app/SPRINT_12_ACCEPTANCE.md
```

---

## Part 5: Sprint retrospective with AI

The context pack gives your AI assistant a structured view of the
sprint for retrospective analysis:

```bash
specforge context-pack ./mobile-app \
  --output ./mobile-app/sprint_12_context.json
```

Attach this file to a Claude conversation and ask:

> "Based on this sprint context pack, summarise what was delivered,
> identify any patterns in the issues encountered, and suggest
> process improvements for Sprint 13."

The AI has full visibility of all requirements, decisions, tasks,
and verification evidence — everything it needs to give a meaningful
retrospective analysis.

---

## Patterns from this tutorial

### Iterative refinement of requirements

REQ-0009 was split during sprint planning. This is normal and healthy.
The SpecForge record shows the split clearly: REQ-0016 has `source:
REQ-0009`. A future reader can trace back and understand that offline
sync was originally part of the offline reading feature.

### Task-to-requirement traceability as a sprint discipline

Every task in Sprint 12 has at least one `implements` link. This is
a discipline that should be enforced in sprint planning: if a task
cannot be linked to a requirement, either the requirement has not been
written yet (write it), or the task is technical debt (label it
explicitly and manage it separately).

### The bug-to-requirement link

TASK-0029 (the notification prompt bug) is linked to REQ-0010. This
creates a record that a defect was discovered and fixed within the
sprint, rather than hiding it. The traceability shows that REQ-0010
could not have been verified without resolving this task first.

### Verification evidence at sprint close

QA evidence includes specific version numbers, device configurations,
and test conditions. This is the difference between "tests passed" and
"we know it works because of this specific evidence, on this specific
date, in this specific environment." Future debugging is easier when
verification evidence is precise.
