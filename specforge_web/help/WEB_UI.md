# Web UI Guide

The SpecForge web interface runs in your browser and connects to the
local daemon. It provides full access to all project operations without
using the command line.

---

## Starting the web UI

```bash
specforge-daemon
```

Then open **http://127.0.0.1:8765/ui** in your browser.

The daemon must stay running while you use the web UI. It serves on
port **8765** by default.

---

## Color modes

Three modes are available via the toggle in the top-right corner:

| Button | Mode |
|--------|------|
| ☀ Light | Bright theme — white backgrounds, dark text |
| ⊙ System | Follows your OS dark/light preference automatically |
| ☾ Dark | Dark theme — reduces glare, easier on sensitive eyes |

Your choice is saved in your browser and restored on the next visit.

**Recommended for migraine sensitivity:** use **☾ Dark** or **⊙ System**
with your OS set to dark mode. The dark theme uses a charcoal background
(`#18181b`) and muted indigo accents — chosen to minimise contrast and
avoid pure white or saturated colours.

---

## Help

Click **? Help** (top-right of the header) to open the help panel.
Three tabs are available: Getting Started, User Manual, Troubleshooting.

Press **Escape** or click outside the panel to close it.

---

## Opening a project

1. Enter the **full path** to your project directory in the path field.
2. Click **Open**.
3. The artifact table populates automatically.

The toolbar buttons become active once a project is open:

| Button | Action |
|--------|--------|
| Refresh | Reload the artifact list |
| Rebuild Trace | Rebuild the SQLite traceability index |
| Context Pack | Show the AI context pack JSON |
| Acceptance Report | Show the Markdown acceptance report |
| Status | Show the project health dashboard |
| Export Matrix | Export the traceability matrix to CSV/Markdown |
| Validate | Check for broken links and status errors |
| Git Log | Show the recent git artifact history |

---

## Creating an artifact

Fill in the **Create Artifact** panel:

1. Select the **kind** from the dropdown.
2. Select the **status** (leave as `draft` for new work).
3. Enter a **title**.
4. Enter the **body** (supports Markdown).
5. Optionally fill in link fields (source, implements, related reqs, etc.).
6. Click **Create Artifact**.

The new artifact appears in the table immediately.

---

## The artifacts table

Each row shows ID, kind (with colour badge), status (with colour badge),
title, and the last two path segments.

**Click any row** to:
- Auto-fill the Promote, Link, and Update Status panels with that ID.
- Show the full artifact JSON in the Output panel.

---

## Colour badges

**Kind colours:**

| Colour | Kinds |
|--------|-------|
| Cyan | idea |
| Sky blue | candidate |
| Blue | requirement |
| Indigo | decision |
| Violet | assumption |
| Pink | constraint |
| Amber | change_order |
| Orange | task |
| Lime | test |
| Teal | verification |
| Slate | reference, conversation |

**Status colours:**

| Colour | Status |
|--------|--------|
| Gray | draft |
| Amber | proposed |
| Blue | approved |
| Purple | implemented |
| Green | verified |
| Red | rejected |
| Dim gray | archived |

---

## Promoting an artifact

1. Click the row for the artifact to promote (fills the ID field), or
   type the ID directly.
2. Select the **target kind**.
3. Optionally enter an override title.
4. Click **Promote**.

---

## Linking an artifact

1. Select the artifact (click its row or type the ID).
2. Enter the IDs to link in the relevant fields (space-separated).
3. Click **Link**.

Existing links are preserved — this operation only **adds** links.

---

## Updating status

1. Select the artifact.
2. Choose the new status.
3. Click **Update**.

---

## Search

Enter one or more keywords. All terms must match (AND search). Results
appear in the Output panel with a snippet of the matching text.

---

## Output panel

All operation results appear in the Output panel below the action
sections. Successful operations show the artifact JSON or a formatted
summary. Errors appear with an "Error:" prefix.

---

## Daemon REST API

The web UI talks to the daemon REST API at `http://127.0.0.1:8765`.
You can call it directly from any HTTP client, script, or other tool.
See the **MCP Integration** help topic for the full endpoint list.
