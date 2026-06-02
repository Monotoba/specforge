# Desktop Studio Guide

The SpecForge Studio is a native desktop application built with PySide6
(Qt). It provides the same functionality as the web UI in a standalone
window, without needing a browser.

---

## Starting the Studio

```bash
specforge-studio
```

Requires the desktop extras:

```bash
pip install "specforge[desktop]" --break-system-packages
```

The Studio connects to the daemon at `http://127.0.0.1:8765` — start
`specforge-daemon` before opening a project.

---

## Opening a project

Click **Open Project** and select your project directory in the file
browser. The artifact list populates automatically.

---

## Toolbar buttons

| Button | Action |
|--------|--------|
| Open Project | Browse to and open a project directory |
| Refresh | Reload the artifact list from the daemon |
| Search | Full-text search (type in the search bar and press Enter) |
| Rebuild Trace | Rebuild the SQLite traceability index |
| Validate | Check for broken links and status errors |
| Context Pack | Show the AI context pack JSON in the detail panel |
| Acceptance Report | Show the Markdown acceptance report |
| Status | Show the project health dashboard |
| Export Matrix | Export the traceability matrix |
| Git Log | Show recent artifact commits |
| Create Artifact… | Open the Create Artifact dialog |
| Promote… | Promote the selected artifact to a new kind |
| Link… | Add links to the selected artifact |
| Update Status… | Change the selected artifact's status |

---

## Artifact list

The left panel shows all artifacts as `[STATUS] ID — Title` entries.
Click an entry to show its full detail JSON in the right panel.

---

## Creating an artifact

Click **Create Artifact…** to open the dialog:

1. Select the **kind** and **status**.
2. Enter the **title** (required).
3. Enter the **body** text.
4. Optionally fill in the **source ID** and any link fields.
5. Click **OK**.

---

## Promoting an artifact

1. Select the artifact in the list.
2. Click **Promote…**.
3. Choose the target kind and optionally override the title.
4. Click **OK**.

---

## Linking an artifact

1. Select the artifact.
2. Click **Link…**.
3. Enter IDs for each link type (space-separated).
4. Click **OK**.

---

## Updating status

1. Select the artifact.
2. Click **Update Status…**.
3. Choose the new status.
4. Click **OK**.

---

## Help menu

The **Help** menu in the menu bar contains:

- **Getting Started** — quick start guide
- **User Manual** — full CLI and feature reference
- **Troubleshooting** — common problems and solutions
- **About SpecForge** — version and links

Help content is fetched from the daemon if it is running, or read from
the filesystem directly if offline.

---

## Troubleshooting

**"Connection refused" errors** — the daemon is not running. Start it
with `specforge-daemon` in a separate terminal.

**"No project opened"** — click **Open Project** before using any
other action.

**Studio won't start** — check that `PySide6` is installed:
```bash
pip install "specforge[desktop]" --break-system-packages
```

**Artifacts list is empty after opening** — click **Refresh**, or
check that the path is a valid SpecForge project (it should contain
subdirectories like `specification/`, `development/`, etc.).
