from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

API = "http://127.0.0.1:8765"

_KINDS = [
    "idea", "candidate", "requirement", "decision", "assumption", "constraint",
    "change_order", "task", "test", "verification", "reference", "conversation",
]
_STATUSES = ["draft", "proposed", "approved", "implemented", "verified", "rejected", "archived"]


class CreateArtifactDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Artifact")
        self.setMinimumWidth(520)

        self._kind = QComboBox()
        for k in _KINDS:
            self._kind.addItem(k)

        self._title = QLineEdit()
        self._title.setPlaceholderText("Required")

        self._status = QComboBox()
        for s in _STATUSES:
            self._status.addItem(s)

        self._body = QTextEdit()
        self._body.setPlaceholderText("Artifact body text")
        self._body.setFixedHeight(100)

        self._source = QLineEdit()
        self._source.setPlaceholderText("e.g. IDEA-0001 (optional)")

        self._implements = QLineEdit()
        self._implements.setPlaceholderText("Space-separated IDs (tasks)")

        self._related_reqs = QLineEdit()
        self._related_reqs.setPlaceholderText("Space-separated REQ IDs")

        self._depends_on = QLineEdit()
        self._depends_on.setPlaceholderText("Space-separated IDs (tasks)")

        self._verified_by = QLineEdit()
        self._verified_by.setPlaceholderText("Space-separated TEST/VER IDs")

        form = QFormLayout()
        form.addRow("Kind:", self._kind)
        form.addRow("Title:", self._title)
        form.addRow("Status:", self._status)
        form.addRow("Body:", self._body)
        form.addRow("Source:", self._source)
        form.addRow("Implements:", self._implements)
        form.addRow("Related reqs:", self._related_reqs)
        form.addRow("Depends on:", self._depends_on)
        form.addRow("Verified by:", self._verified_by)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _validate_and_accept(self) -> None:
        if not self._title.text().strip():
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        self.accept()

    @staticmethod
    def _ids(field: QLineEdit) -> list[str]:
        return field.text().split() if field.text().strip() else []

    def payload(self) -> dict[str, object]:
        return {
            "kind": self._kind.currentText(),
            "title": self._title.text().strip(),
            "status": self._status.currentText(),
            "body": self._body.toPlainText(),
            "source": self._source.text().strip() or None,
            "implements": self._ids(self._implements),
            "related_requirements": self._ids(self._related_reqs),
            "depends_on": self._ids(self._depends_on),
            "verified_by": self._ids(self._verified_by),
            "references": [],
        }


class LinkDialog(QDialog):
    def __init__(self, artifact_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Link {artifact_id}")
        self.setMinimumWidth(460)

        self._implements = QLineEdit()
        self._implements.setPlaceholderText("Space-separated REQ IDs")
        self._related_reqs = QLineEdit()
        self._related_reqs.setPlaceholderText("Space-separated REQ IDs")
        self._verified_by = QLineEdit()
        self._verified_by.setPlaceholderText("Space-separated TEST/VER IDs")
        self._depends_on = QLineEdit()
        self._depends_on.setPlaceholderText("Space-separated TASK IDs")
        self._source = QLineEdit()
        self._source.setPlaceholderText("Source artifact ID (replaces existing)")
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("Space-separated tags")

        form = QFormLayout()
        form.addRow("Implements:", self._implements)
        form.addRow("Related reqs:", self._related_reqs)
        form.addRow("Verified by:", self._verified_by)
        form.addRow("Depends on:", self._depends_on)
        form.addRow("Source:", self._source)
        form.addRow("Tags:", self._tags)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @staticmethod
    def _ids(field: QLineEdit) -> list[str]:
        return field.text().split() if field.text().strip() else []

    def payload(self) -> dict[str, object]:
        return {
            "implements": self._ids(self._implements),
            "related_requirements": self._ids(self._related_reqs),
            "verified_by": self._ids(self._verified_by),
            "depends_on": self._ids(self._depends_on),
            "source": self._source.text().strip() or None,
            "tags": self._ids(self._tags),
        }


class PromoteDialog(QDialog):
    def __init__(self, artifact_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Promote {artifact_id}")

        self._kind = QComboBox()
        for k in _KINDS[1:]:  # exclude "idea" as target
            self._kind.addItem(k)
        self._title = QLineEdit()
        self._title.setPlaceholderText("Leave blank to inherit")

        form = QFormLayout()
        form.addRow("Target kind:", self._kind)
        form.addRow("Override title:", self._title)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def values(self) -> dict[str, object]:
        payload: dict[str, object] = {"target_kind": self._kind.currentText()}
        title = self._title.text().strip()
        if title:
            payload["title"] = title
        return payload


class UpdateStatusDialog(QDialog):
    def __init__(self, artifact_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Update status: {artifact_id}")

        self._status = QComboBox()
        for s in _STATUSES:
            self._status.addItem(s)

        form = QFormLayout()
        form.addRow("New status:", self._status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def status(self) -> str:
        return self._status.currentText()


def _md_to_html(md: str) -> str:
    """Convert a subset of Markdown to HTML for QTextBrowser."""
    import re

    h = md
    # Fenced code blocks
    h = re.sub(r'```\w*\n([\s\S]*?)```', lambda m:
        f'<pre style="background:#2a2a2e;color:#e4e4e7;padding:8px;border-radius:4px;font-size:11px">'
        f'<code>{m.group(1).strip()}</code></pre>', h)
    # Inline code
    h = re.sub(r'`([^`]+)`', r'<code style="background:#e4e4e7;color:#18181b;padding:1px 4px;border-radius:2px">\1</code>', h)
    # Headers
    h = re.sub(r'^### (.+)$', r'<h3 style="color:#555">\1</h3>', h, flags=re.MULTILINE)
    h = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', h, flags=re.MULTILINE)
    h = re.sub(r'^# (.+)$',   r'<h1 style="color:#4f46e5">\1</h1>', h, flags=re.MULTILINE)
    # Bold
    h = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', h)
    # Tables
    def _table(m: re.Match) -> str:
        hdr, _, body = m.group(0).strip().split('\n', 2)
        ths = ''.join(f'<th style="background:#f0f0f2;padding:4px 8px;text-align:left">{c.strip()}</th>'
                      for c in hdr.split('|')[1:-1])
        rows = ''
        for row in body.strip().split('\n'):
            tds = ''.join(f'<td style="padding:3px 8px">{c.strip()}</td>'
                          for c in row.split('|')[1:-1])
            rows += f'<tr>{tds}</tr>'
        return f'<table border="1" cellspacing="0" style="border-collapse:collapse;width:100%"><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table>'
    h = re.sub(r'\|.+\|\n\|[-| :]+\|\n(?:\|.+\|\n?)+', _table, h)
    # Unordered list
    h = re.sub(r'((?:^- .+\n?)+)', lambda m:
        '<ul>' + ''.join(f'<li>{l[2:]}</li>' for l in m.group(0).strip().split('\n')) + '</ul>',
        h, flags=re.MULTILINE)
    # Ordered list
    h = re.sub(r'((?:^\d+\. .+\n?)+)', lambda m:
        '<ol>' + ''.join(f'<li>{re.sub(r"^\d+\. ", "", l)}</li>' for l in m.group(0).strip().split('\n')) + '</ol>',
        h, flags=re.MULTILINE)
    # Links
    h = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', h)
    # Horizontal rule
    h = re.sub(r'^---$', '<hr/>', h, flags=re.MULTILINE)
    # Paragraphs
    h = re.sub(r'^(?!<[houpl])(.+)$', r'<p>\1</p>', h, flags=re.MULTILINE)
    return f'<html><body style="font-family:system-ui,sans-serif;font-size:13px;padding:8px">{h}</body></html>'


class HelpDialog(QDialog):
    """A tabbed help viewer that fetches content from the daemon or filesystem."""

    _TOPICS = [
        ("Getting Started",  "getting_started"),
        ("Workflow",         "workflow"),
        ("Artifact Types",   "artifacts"),
        ("CLI Commands",     "user_manual"),
        ("Configuration",    "configuration"),
        ("Web UI",           "web_ui"),
        ("Studio",           "studio"),
        ("AI Drafting",      "ai_drafting"),
        ("Webhooks",         "webhooks"),
        ("Plugins",          "plugins"),
        ("Templates",        "templates"),
        ("MCP",              "mcp"),
        ("Troubleshooting",  "troubleshooting"),
    ]

    def __init__(self, parent: QWidget | None = None, initial_topic: str = "getting_started") -> None:
        super().__init__(parent)
        self.setWindowTitle("SpecForge Help")
        self.resize(820, 640)

        self._tabs = QTabWidget()
        self._browsers: dict[str, QTextBrowser] = {}

        for label, topic in self._TOPICS:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            browser.setHtml("<p><i>Loading…</i></p>")
            self._browsers[topic] = browser
            self._tabs.addTab(browser, label)
            self._load_topic(topic, browser)

        # Switch to requested tab
        for i, (_, t) in enumerate(self._TOPICS):
            if t == initial_topic:
                self._tabs.setCurrentIndex(i)
                break

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_topic(self, topic: str, browser: QTextBrowser) -> None:
        # Try daemon first, fall back to filesystem
        try:
            url = f"{API}/help/{topic}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            browser.setHtml(_md_to_html(data["markdown"]))
            return
        except Exception:
            pass
        # Filesystem fallback
        from pathlib import Path
        candidates = [
            Path(__file__).resolve().parent.parent / "specforge_web" / "help",
        ]
        fname = {
            "getting_started": "GETTING_STARTED.md",
            "workflow":        "WORKFLOW.md",
            "artifacts":       "ARTIFACTS.md",
            "user_manual":     "USER_MANUAL.md",
            "configuration":   "CONFIGURATION.md",
            "web_ui":          "WEB_UI.md",
            "studio":          "STUDIO.md",
            "ai_drafting":     "AI_DRAFTING.md",
            "webhooks":        "WEBHOOKS.md",
            "plugins":         "PLUGINS.md",
            "templates":       "TEMPLATES.md",
            "mcp":             "MCP.md",
            "troubleshooting": "TROUBLESHOOTING.md",
        }.get(topic, "")
        for d in candidates:
            p = d / fname
            if p.exists():
                browser.setHtml(_md_to_html(p.read_text(encoding="utf-8")))
                return
        browser.setHtml(f"<p>Help file not found for topic <b>{topic}</b>.</p>"
                        "<p>Start the SpecForge daemon to load help content.</p>")


class SpecForgeStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SpecForge Studio")
        self.resize(1200, 760)
        self.project_label = QLabel("No project open")
        self.artifacts = QListWidget()
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        # Search bar
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search artifacts…")
        self._search_input.returnPressed.connect(self.do_search)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.do_search)

        # Buttons
        open_button = QPushButton("Open Project")
        open_button.clicked.connect(self.open_project)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        trace_button = QPushButton("Rebuild Trace")
        trace_button.clicked.connect(self.rebuild_trace)
        context_button = QPushButton("Context Pack")
        context_button.clicked.connect(self.fetch_context_pack)
        report_button = QPushButton("Acceptance Report")
        report_button.clicked.connect(self.fetch_report)
        status_dash_button = QPushButton("Status")
        status_dash_button.clicked.connect(self.do_status)
        export_button = QPushButton("Export Matrix")
        export_button.clicked.connect(self.do_export)
        validate_button = QPushButton("Validate")
        validate_button.clicked.connect(self.do_validate)
        log_button = QPushButton("Git Log")
        log_button.clicked.connect(self.do_git_log)

        create_button = QPushButton("Create Artifact…")
        create_button.clicked.connect(self.create_artifact)
        promote_button = QPushButton("Promote…")
        promote_button.clicked.connect(self.promote_selected)
        link_button = QPushButton("Link…")
        link_button.clicked.connect(self.link_selected)
        status_button = QPushButton("Update Status…")
        status_button.clicked.connect(self.update_status_selected)

        # Layout
        left = QVBoxLayout()
        left.addWidget(self.project_label)

        row1 = QHBoxLayout()
        row1.addWidget(open_button)
        row1.addWidget(refresh_button)
        left.addLayout(row1)

        search_row = QHBoxLayout()
        search_row.addWidget(self._search_input)
        search_row.addWidget(search_button)
        left.addLayout(search_row)

        row2 = QHBoxLayout()
        row2.addWidget(trace_button)
        row2.addWidget(validate_button)
        left.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(context_button)
        row3.addWidget(report_button)
        left.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(status_dash_button)
        row4.addWidget(export_button)
        left.addLayout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(log_button)
        left.addLayout(row5)

        left.addWidget(QLabel("Artifacts"))
        left.addWidget(self.artifacts)

        left.addWidget(create_button)

        action_row = QHBoxLayout()
        action_row.addWidget(promote_button)
        action_row.addWidget(link_button)
        left.addLayout(action_row)

        status_row = QHBoxLayout()
        status_row.addWidget(status_button)
        left.addLayout(status_row)

        root = QHBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(420)
        root.addWidget(left_widget)
        root.addWidget(self.detail)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)
        self.artifacts.itemSelectionChanged.connect(self.show_selected)
        self._artifact_data: list[dict[str, object]] = []

        # Menu bar
        menu_bar = self.menuBar()
        help_menu: QMenu = menu_bar.addMenu("Help")
        help_menu.addAction("Getting Started",  lambda: self._open_help("getting_started"))
        help_menu.addAction("Workflow Guide",   lambda: self._open_help("workflow"))
        help_menu.addAction("Artifact Types",   lambda: self._open_help("artifacts"))
        help_menu.addSeparator()
        help_menu.addAction("CLI Commands",     lambda: self._open_help("user_manual"))
        help_menu.addAction("Configuration",    lambda: self._open_help("configuration"))
        help_menu.addAction("Web UI Guide",     lambda: self._open_help("web_ui"))
        help_menu.addAction("Desktop Studio",   lambda: self._open_help("studio"))
        help_menu.addSeparator()
        help_menu.addAction("AI Drafting",      lambda: self._open_help("ai_drafting"))
        help_menu.addAction("Webhooks",         lambda: self._open_help("webhooks"))
        help_menu.addAction("Plugins",          lambda: self._open_help("plugins"))
        help_menu.addAction("Templates",        lambda: self._open_help("templates"))
        help_menu.addAction("MCP / Claude Code",lambda: self._open_help("mcp"))
        help_menu.addSeparator()
        help_menu.addAction("Troubleshooting",  lambda: self._open_help("troubleshooting"))
        help_menu.addSeparator()
        help_menu.addAction("About SpecForge",  self._show_about)

    def _open_help(self, topic: str = "getting_started") -> None:
        dlg = HelpDialog(self, initial_topic=topic)
        dlg.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About SpecForge",
            "<b>SpecForge</b><br/>"
            "Local-first spec and workflow system.<br/><br/>"
            "Tracks requirements, tasks, decisions, and verification evidence "
            "as plain Markdown files with full traceability.<br/><br/>"
            "Commands: <code>specforge --help</code><br/>"
            "Web UI: <a href='http://127.0.0.1:8765/ui'>http://127.0.0.1:8765/ui</a>"
        )

    def _selected_id(self) -> str | None:
        row = self.artifacts.currentRow()
        if row < 0:
            return None
        return str(self._artifact_data[row]["id"])

    def open_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open SpecForge Project")
        if not path:
            return
        try:
            response = post_json("/projects/open", {"path": path})
        except Exception as exc:
            QMessageBox.critical(self, "Daemon error", str(exc))
            return
        self.project_label.setText(str(response["path"]))
        self.refresh()

    def refresh(self) -> None:
        try:
            self._artifact_data = get_json("/artifacts")
        except Exception as exc:
            QMessageBox.warning(self, "Refresh failed", str(exc))
            return
        self._populate_list(self._artifact_data)

    def _populate_list(self, data: list[dict[str, object]]) -> None:
        self.artifacts.clear()
        for artifact in data:
            self.artifacts.addItem(
                f"{artifact['id']}  [{artifact['kind']}]  {artifact['title']}"
            )
        self._artifact_data = data

    def show_selected(self) -> None:
        row = self.artifacts.currentRow()
        if row < 0:
            return
        artifact = self._artifact_data[row]
        self.detail.setPlainText(json.dumps(artifact, indent=2, default=str))

    def create_artifact(self) -> None:
        dialog = CreateArtifactDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            response = post_json("/artifacts", dialog.payload())
        except Exception as exc:
            QMessageBox.warning(self, "Create failed", str(exc))
            return
        self.detail.setPlainText(json.dumps(response, indent=2, default=str))
        self.refresh()

    def rebuild_trace(self) -> None:
        try:
            response = post_json("/trace/rebuild", {})
        except Exception as exc:
            QMessageBox.warning(self, "Trace failed", str(exc))
            return
        self.detail.setPlainText(json.dumps(response, indent=2, default=str))

    def fetch_context_pack(self) -> None:
        try:
            response = get_json("/context-pack")
        except Exception as exc:
            QMessageBox.warning(self, "Context pack failed", str(exc))
            return
        self.detail.setPlainText(json.dumps(response, indent=2, default=str))

    def fetch_report(self) -> None:
        try:
            text = get_text("/report")
        except Exception as exc:
            QMessageBox.warning(self, "Report failed", str(exc))
            return
        self.detail.setPlainText(text)

    def do_status(self) -> None:
        try:
            data = get_json("/status")
        except Exception as exc:
            QMessageBox.warning(self, "Status failed", str(exc))
            return
        gate = data.get("gate", "?")
        unverified = data.get("unverified_requirements", [])
        open_tasks = data.get("open_tasks", [])
        kind_counts = data.get("kind_counts", {})
        lines = [f"Release Gate: {gate}", "", f"Total artifacts: {data.get('total_artifacts', 0)}"]
        for k, n in sorted(kind_counts.items()):
            lines.append(f"  {k}: {n}")
        lines += ["", f"Unverified requirements: {len(unverified)}"]
        for r in unverified:
            lines.append(f"  {r['id']}: {r['title']}")
        lines += ["", f"Open tasks: {len(open_tasks)}"]
        for t in open_tasks:
            lines.append(f"  {t['id']} [{t['status']}]: {t['title']}")
        self.detail.setPlainText("\n".join(lines))

    def do_export(self) -> None:
        try:
            response = get_json("/export")
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        lines = ["Exported:"] + [f"  {k}: {v}" for k, v in response.items()]
        self.detail.setPlainText("\n".join(lines))

    def do_validate(self) -> None:
        try:
            response = get_json("/validate")
        except Exception as exc:
            QMessageBox.warning(self, "Validate failed", str(exc))
            return
        if response.get("ok"):
            self.detail.setPlainText("Validation passed.")
        else:
            errors = response.get("errors", [])
            self.detail.setPlainText("Validation errors:\n" + "\n".join(str(e) for e in errors))

    def do_git_log(self) -> None:
        try:
            entries = get_json("/git/log")
        except Exception as exc:
            QMessageBox.warning(self, "Git log failed", str(exc))
            return
        if not entries:
            self.detail.setPlainText("No git history found.")
            return
        lines = [f"{e['sha']}  {e['date']}  {e['author']}\n  {e['message']}" for e in entries]
        self.detail.setPlainText("\n\n".join(lines))

    def do_search(self) -> None:
        query = self._search_input.text().strip()
        if not query:
            self.refresh()
            return
        try:
            results = get_json(f"/search?q={urllib.parse.quote(query)}")
        except Exception as exc:
            QMessageBox.warning(self, "Search failed", str(exc))
            return
        if not results:
            self.detail.setPlainText("No results.")
            self._populate_list([])
            return
        self._populate_list(results)
        lines = [f"{r['id']}  [{r['kind']}/{r['status']}]  {r['title']}\n  {r['snippet']}"
                 for r in results]
        self.detail.setPlainText("\n\n".join(lines))

    def link_selected(self) -> None:
        artifact_id = self._selected_id()
        if artifact_id is None:
            QMessageBox.information(self, "Link", "Select an artifact first.")
            return
        dialog = LinkDialog(artifact_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = {k: v for k, v in dialog.payload().items() if v}
        if not payload:
            QMessageBox.information(self, "Link", "No links specified.")
            return
        try:
            response = post_json(f"/artifacts/{artifact_id}/link", payload)
        except Exception as exc:
            QMessageBox.warning(self, "Link failed", str(exc))
            return
        self.detail.setPlainText(json.dumps(response, indent=2, default=str))
        self.refresh()

    def promote_selected(self) -> None:
        artifact_id = self._selected_id()
        if artifact_id is None:
            QMessageBox.information(self, "Promote", "Select an artifact first.")
            return
        dialog = PromoteDialog(artifact_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            response = post_json(f"/artifacts/{artifact_id}/promote", dialog.values())
        except Exception as exc:
            QMessageBox.warning(self, "Promote failed", str(exc))
            return
        self.detail.setPlainText(json.dumps(response, indent=2, default=str))
        self.refresh()

    def update_status_selected(self) -> None:
        artifact_id = self._selected_id()
        if artifact_id is None:
            QMessageBox.information(self, "Update Status", "Select an artifact first.")
            return
        dialog = UpdateStatusDialog(artifact_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            response = patch_json(
                f"/artifacts/{artifact_id}/status", {"status": dialog.status()}
            )
        except Exception as exc:
            QMessageBox.warning(self, "Update status failed", str(exc))
            return
        self.detail.setPlainText(json.dumps(response, indent=2, default=str))
        self.refresh()


def get_json(path: str) -> Any:
    with urllib.request.urlopen(API + path, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def get_text(path: str) -> str:
    with urllib.request.urlopen(API + path, timeout=5) as response:
        return response.read().decode("utf-8")


def post_json(path: str, data: dict[str, object]) -> Any:
    request = urllib.request.Request(
        API + path,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8")) from exc


def patch_json(path: str, data: dict[str, object]) -> Any:
    request = urllib.request.Request(
        API + path,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8")) from exc


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SpecForge Studio")
    window = SpecForgeStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
