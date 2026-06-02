from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from specforge_core.adapter import handle_tool_call
from specforge_core.config import ProjectConfig, load_config, save_config, write_default_config
from specforge_core.contextpack import build_context_pack
from specforge_core.export import ExportFormat, export_project
from specforge_core.gitwrap import artifact_log
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.report import build_acceptance_report
from specforge_core.search import search_artifacts
from specforge_core.status import project_status
from specforge_core.trace import TraceIndex
from specforge_core.validation import validate_project

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def init(
    path: Path,
    git: bool = typer.Option(False, "--git", help="Initialize a git repository and commit the scaffold"),
    name: Optional[str] = typer.Option(None, "--name", help="Project name for reports"),
) -> None:
    """Create a new SpecForge project folder."""
    project = Project(path)
    project.init()
    write_default_config(project.root)
    if name:
        cfg = load_config(project.root)
        cfg_updated = ProjectConfig(project_name=name, git_commit=cfg.git_commit)
        save_config(project.root, cfg_updated)
        project.reload_config()
    console.print(f"Created SpecForge project: {project.root}")
    if git:
        _git_init_project(project.root)


@app.command("add-idea")
def add_idea(
    path: Path, title: str,
    text: str = typer.Argument("", help="Body text (defaults to title)"),
    tag: List[str] = typer.Option([], "--tag", help="Tag (repeatable)"),
    git: bool = typer.Option(False, "--git", help="Commit artifact to git"),
) -> None:
    """Record a raw exploration idea (status: draft)."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.IDEA, title, text or title, git_commit=_eg(project, git), tags=tag or None,
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-candidate")
def add_candidate(
    path: Path, title: str,
    text: str = typer.Argument("", help="Body text (defaults to title)"),
    source: Optional[str] = None,
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git", help="Commit artifact to git"),
) -> None:
    """Promote an idea to a candidate for evaluation (status: proposed)."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.CANDIDATE, title, text or title,
        source=source, status=ArtifactStatus.PROPOSED, git_commit=_eg(project, git), tags=tag or None,
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-req")
def add_requirement(
    path: Path,
    title: str,
    text: str = typer.Option(..., "--text", "-t", help="Requirement body text"),
    source: Optional[str] = None,
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git", help="Commit artifact to git"),
) -> None:
    """Create an approved requirement linked to the spec traceability chain."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.REQUIREMENT, title, text,
        status=ArtifactStatus.APPROVED, source=source, git_commit=_eg(project, git), tags=tag or None,
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-co")
def add_change_order(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t", help="Change order body text"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git", help="Commit artifact to git"),
) -> None:
    """Propose a change order — scope or requirement change for review."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.CHANGE_ORDER, title, text,
        status=ArtifactStatus.PROPOSED, git_commit=_eg(project, git), tags=tag or None,
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-decision")
def add_decision(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    source: Optional[str] = None,
    related_requirements: List[str] = typer.Option([], "--req"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Record an architectural or design decision."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.DECISION, title, text,
        status=ArtifactStatus.APPROVED, source=source,
        related_requirements=related_requirements or None,
        tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-assumption")
def add_assumption(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    source: Optional[str] = None,
    related_requirements: List[str] = typer.Option([], "--req"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Record a project assumption."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.ASSUMPTION, title, text,
        status=ArtifactStatus.APPROVED, source=source,
        related_requirements=related_requirements or None,
        tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-constraint")
def add_constraint(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    source: Optional[str] = None,
    related_requirements: List[str] = typer.Option([], "--req"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Record a project constraint."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.CONSTRAINT, title, text,
        status=ArtifactStatus.APPROVED, source=source,
        related_requirements=related_requirements or None,
        tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-task")
def add_task(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    implements: List[str] = typer.Option([], "--implements"),
    depends_on: List[str] = typer.Option([], "--depends-on"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Create a development task linked to requirements."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.TASK, title, text,
        implements=implements or None, depends_on=depends_on or None,
        tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-test")
def add_test(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    related_requirements: List[str] = typer.Option([], "--req"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Define a test artifact linked to requirements."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.TEST, title, text,
        related_requirements=related_requirements or None,
        tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-verification")
def add_verification(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    related_requirements: List[str] = typer.Option([], "--req"),
    verified_by: List[str] = typer.Option([], "--test"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Record verification evidence for one or more requirements."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.VERIFICATION, title, text,
        related_requirements=related_requirements or None,
        verified_by=verified_by or None,
        tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-ref")
def add_ref(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Record an external reference (URL, document, paper, etc.)."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.REFERENCE, title, text, tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command("add-conv")
def add_conv(
    path: Path, title: str,
    text: str = typer.Option(..., "--text", "-t"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Record a conversation note or AI session summary."""
    project = Project(path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.CONVERSATION, title, text, tags=tag or None, git_commit=_eg(project, git),
    )
    console.print(f"Created {artifact.id}: {artifact.title}")


@app.command()
def list(  # noqa: A001
    path: Path,
    kind: Optional[ArtifactKind] = None,
    status: Optional[ArtifactStatus] = typer.Option(None, "--status", "-s"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
) -> None:
    """List artifacts, optionally filtered by kind, status, and/or tag."""
    project = Project(path)
    table = Table("ID", "Kind", "Status", "Title", "Tags", "Path")
    for artifact in project.artifacts():
        if kind and artifact.kind != kind:
            continue
        if status and artifact.status != status:
            continue
        if tag and tag not in artifact.tags:
            continue
        table.add_row(
            artifact.id,
            artifact.kind.value,
            artifact.status.value,
            artifact.title,
            " ".join(artifact.tags) if artifact.tags else "",
            str(artifact.path.relative_to(project.root) if artifact.path else ""),
        )
    console.print(table)


@app.command()
def trace(path: Path) -> None:
    """Rebuild the SQLite traceability index from the artifact files."""
    project = Project(path)
    index = TraceIndex(project)
    index.rebuild()
    console.print(f"Rebuilt trace index: {index.db_path}")
    unverified = index.unverified_requirements()
    if unverified:
        console.print("Unverified approved/implemented requirements:")
        for row in unverified:
            console.print(f"  {row['id']}: {row['title']}")


@app.command()
def status(path: Path) -> None:
    """Show a project health dashboard: counts, open tasks, release gate."""
    from rich.rule import Rule

    project = Project(path)
    data = project_status(project)

    title = project.config.project_name or str(project.root)
    console.print(Rule(f"[bold]SpecForge[/bold]  {title}", style="blue"))
    console.print()

    # Artifact counts table
    counts_table = Table("Kind", "Total", "Breakdown", box=None, show_header=True, padding=(0, 2))
    counts_table.add_column("Kind", style="cyan")
    counts_table.add_column("Total", justify="right")
    counts_table.add_column("Breakdown", style="dim")
    kind_counts: dict[str, int] = data["kind_counts"]  # type: ignore[assignment]
    breakdown: dict[str, dict[str, int]] = data["breakdown"]  # type: ignore[assignment]
    for kind in sorted(kind_counts):
        total = kind_counts[kind]
        detail = "  ".join(f"{s}:{n}" for s, n in sorted(breakdown[kind].items()))
        counts_table.add_row(kind, str(total), detail)
    console.print(Panel(counts_table, title="Artifacts", expand=False))

    # Release gate
    gate = str(data["gate"])
    unverified: list[dict[str, str]] = data["unverified_requirements"]  # type: ignore[assignment]
    open_tasks: list[dict[str, str]] = data["open_tasks"]  # type: ignore[assignment]
    gate_color = "green" if gate == "PASS" else "red"
    gate_lines: list[str] = [f"[{gate_color}][bold]{gate}[/bold][/{gate_color}]"]
    if unverified:
        gate_lines.append(f"  [yellow]Unverified requirements ({len(unverified)}):[/yellow]")
        for row in unverified:
            gate_lines.append(f"    {row['id']}: {row['title']}")
    else:
        gate_lines.append("  [green]All requirements verified[/green]")
    if open_tasks:
        gate_lines.append(f"  [yellow]Open tasks ({len(open_tasks)}):[/yellow]")
        for t in open_tasks:
            gate_lines.append(f"    {t['id']}  [{t['status']}]  {t['title']}")
    else:
        gate_lines.append("  [green]No open tasks[/green]")
    console.print(Panel("\n".join(gate_lines), title="Release Gate", expand=False))
    console.print()


@app.command()
def graph(path: Path, artifact_id: str) -> None:
    """Show the link graph for an artifact as a tree."""
    project = Project(path)
    index = TraceIndex(project)
    try:
        data = index.artifact_graph(artifact_id)
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)
    art: dict[str, object] = data["artifact"]  # type: ignore[assignment]
    root = Tree(
        f"[bold]{art['id']}[/bold]  [{art['kind']}]  {art['title']}  ({art['status']})"
    )
    outgoing: list[dict[str, str]] = data.get("outgoing", [])  # type: ignore[assignment]
    incoming: list[dict[str, str]] = data.get("incoming", [])  # type: ignore[assignment]
    if outgoing:
        out_branch = root.add("[cyan]outgoing[/cyan]")
        for link in outgoing:
            out_branch.add(f"{link['dst_id']}  [dim]{link['link_type']}[/dim]")
    if incoming:
        in_branch = root.add("[green]incoming[/green]")
        for link in incoming:
            in_branch.add(f"{link['src_id']}  [dim]{link['link_type']}[/dim]")
    if not outgoing and not incoming:
        root.add("[dim]no links[/dim]")
    console.print(root)


@app.command()
def promote(
    path: Path,
    artifact_id: str,
    target_kind: ArtifactKind,
    title: Optional[str] = None,
    text: Optional[str] = typer.Option(None, "--text", "-t"),
    implements: List[str] = typer.Option([], "--implements", help="Req IDs this artifact implements"),
    related_requirements: List[str] = typer.Option([], "--req"),
    verified_by: List[str] = typer.Option([], "--test"),
    depends_on: List[str] = typer.Option([], "--depends-on"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git", help="Commit promoted artifact to git"),
) -> None:
    """Promote an artifact to a new kind, creating a trace link."""
    project = Project(path)
    try:
        promoted = project.promote_artifact(
            artifact_id, target_kind, title=title, body=text, git_commit=_eg(project, git),
            implements=implements or None,
            related_requirements=related_requirements or None,
            verified_by=verified_by or None,
            depends_on=depends_on or None,
            tags=tag or None,
        )
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)
    console.print(f"Promoted {artifact_id} → {promoted.id}: {promoted.title}")


@app.command()
def unlink(
    path: Path,
    artifact_id: str,
    implements: List[str] = typer.Option([], "--implements"),
    related_requirements: List[str] = typer.Option([], "--req"),
    verified_by: List[str] = typer.Option([], "--test"),
    depends_on: List[str] = typer.Option([], "--depends-on"),
    tag: List[str] = typer.Option([], "--tag"),
    source: bool = typer.Option(False, "--source", help="Clear the source link"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Remove specific links from an existing artifact."""
    project = Project(path)
    try:
        artifact = project.unlink_artifact(
            artifact_id,
            clear_source=source,
            git_commit=_eg(project, git),
            implements=implements or None,
            related_requirements=related_requirements or None,
            verified_by=verified_by or None,
            depends_on=depends_on or None,
            tags=tag or None,
        )
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)
    console.print(f"Unlinked {artifact.id}: {artifact.title}")


@app.command()
def link(
    path: Path,
    artifact_id: str,
    implements: List[str] = typer.Option([], "--implements"),
    related_requirements: List[str] = typer.Option([], "--req"),
    verified_by: List[str] = typer.Option([], "--test"),
    depends_on: List[str] = typer.Option([], "--depends-on"),
    source: Optional[str] = typer.Option(None, "--source"),
    tag: List[str] = typer.Option([], "--tag"),
    git: bool = typer.Option(False, "--git"),
) -> None:
    """Add links to an existing artifact (append, no duplicates)."""
    project = Project(path)
    try:
        artifact = project.link_artifact(
            artifact_id,
            git_commit=_eg(project, git),
            implements=implements or None,
            related_requirements=related_requirements or None,
            verified_by=verified_by or None,
            depends_on=depends_on or None,
            source=source,
            tags=tag or None,
        )
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)
    console.print(f"Linked {artifact.id}: {artifact.title}")


@app.command("update-status")
def update_status(
    path: Path, artifact_id: str, status: ArtifactStatus,
    git: bool = typer.Option(False, "--git", help="Commit status change to git"),
) -> None:
    """Update the status of an existing artifact."""
    project = Project(path)
    try:
        artifact = project.update_status(artifact_id, status, git_commit=git)
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)
    console.print(f"Updated {artifact.id} status → {artifact.status.value}")


@app.command()
def edit(path: Path, artifact_id: str) -> None:
    """Open an artifact in $EDITOR (or $VISUAL) for direct editing."""
    import os
    import subprocess

    from specforge_core.markdown import read_artifact

    project = Project(path)
    try:
        artifact = project.get_artifact(artifact_id)
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)

    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        console.print("[red]No editor found. Set $EDITOR or $VISUAL.[/red]")
        raise typer.Exit(1)

    assert artifact.path is not None
    try:
        subprocess.run([editor, str(artifact.path)], check=True)
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor!r}[/red]")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Editor exited with code {exc.returncode}[/red]")
        raise typer.Exit(1)

    project.invalidate_cache()

    try:
        updated = read_artifact(artifact.path)
        console.print(f"Saved {updated.id}: {updated.title}")
    except Exception as exc:
        console.print(f"[yellow]Warning: YAML parse error after edit — {exc}[/yellow]")


@app.command()
def show(path: Path, artifact_id: str) -> None:
    """Show details of a single artifact."""
    project = Project(path)
    try:
        artifact = project.get_artifact(artifact_id)
    except KeyError:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        raise typer.Exit(1)

    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="bold cyan")
    meta.add_column()
    meta.add_row("ID", artifact.id)
    meta.add_row("Kind", artifact.kind.value)
    meta.add_row("Status", artifact.status.value)
    meta.add_row("Created", artifact.created_at.strftime("%Y-%m-%d %H:%M UTC"))
    meta.add_row("Updated", artifact.updated_at.strftime("%Y-%m-%d %H:%M UTC"))
    if artifact.source:
        meta.add_row("Source", artifact.source)
    if artifact.tags:
        meta.add_row("Tags", " ".join(artifact.tags))
    if artifact.path:
        meta.add_row("Path", str(artifact.path.relative_to(project.root)))

    link_fields = {
        "depends_on": artifact.depends_on,
        "implements": artifact.implements,
        "related_requirements": artifact.related_requirements,
        "related_decisions": artifact.related_decisions,
        "related_assumptions": artifact.related_assumptions,
        "verified_by": artifact.verified_by,
        "references": artifact.references,
    }
    for field, values in link_fields.items():
        if values:
            resolved = []
            for link_id in values:
                try:
                    linked = project.get_artifact(link_id)
                    resolved.append(f"{link_id}  [{linked.kind.value}/{linked.status.value}]")
                except KeyError:
                    resolved.append(f"{link_id}  [missing]")
            meta.add_row(field, "\n".join(resolved))

    console.print(Panel(meta, title=f"[bold]{artifact.title}[/bold]", expand=False))
    if artifact.body.strip():
        console.print(Panel(artifact.body.strip(), title="Body", expand=False))


@app.command("context-pack")
def context_pack(
    path: Path,
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Build a JSON context pack for AI agents."""
    import json

    project = Project(path)
    pack = build_context_pack(project)
    text = json.dumps(pack, indent=2, default=str)
    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"Context pack written to {output}")
    else:
        console.print(text)


@app.command()
def report(
    path: Path,
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate an acceptance report for release readiness."""
    project = Project(path)
    index = TraceIndex(project)
    index.rebuild()
    text = build_acceptance_report(project, index)
    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"Report written to {output}")
    else:
        console.print(text)


@app.command()
def log(
    path: Path,
    n: int = typer.Option(20, "--count", "-n", help="Number of commits to show"),
) -> None:
    """Show git history for this project."""
    project = Project(path)
    entries = artifact_log(project.root, max_count=n)
    if not entries:
        console.print("[yellow]No git history found — project may not be in a git repo.[/yellow]")
        return
    table = Table("SHA", "Date", "Author", "Message")
    for entry in entries:
        table.add_row(entry["sha"], entry["date"], entry["author"], entry["message"])
    console.print(table)


@app.command()
def search(
    path: Path,
    query: str,
    kind: List[ArtifactKind] = typer.Option([], "--kind", "-k", help="Filter by kind (repeatable)"),
    status: List[ArtifactStatus] = typer.Option([], "--status", "-s", help="Filter by status (repeatable)"),
    tag: List[str] = typer.Option([], "--tag", help="Filter by tag (repeatable)"),
) -> None:
    """Search artifact titles and bodies. All terms must match."""
    project = Project(path)
    results = search_artifacts(
        project,
        query,
        kinds=kind or None,
        statuses=status or None,
        tags=tag or None,
    )
    if not results:
        console.print("[yellow]No results.[/yellow]")
        return
    table = Table("ID", "Kind", "Status", "Title", "Snippet")
    for r in results:
        table.add_row(
            str(r["id"]), str(r["kind"]), str(r["status"]),
            str(r["title"]), str(r["snippet"]),
        )
    console.print(table)


@app.command("tool-call")
def tool_call(
    path: Path,
    call_json: str = typer.Argument(..., help='JSON tool-call dict, e.g. \'{"action":"search","query":"DXF"}\''),
) -> None:
    """Dispatch a structured JSON tool call — the AI adapter entry point."""
    import json

    project = Project(path)
    try:
        call = json.loads(call_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        raise typer.Exit(1)
    result = handle_tool_call(project, call)
    console.print(json.dumps(result, indent=2, default=str))
    if not result["ok"]:
        raise typer.Exit(1)


@app.command()
def export(
    path: Path,
    fmt: ExportFormat = typer.Option(ExportFormat.BOTH, "--format", "-f"),
) -> None:
    """Export traceability matrix to trace/exports/ as CSV and/or Markdown."""
    project = Project(path)
    written = export_project(project, fmt)
    for kind, out_path in written.items():
        console.print(f"Exported {kind}: {out_path.relative_to(project.root)}")


@app.command()
def check(path: Path) -> None:
    """CI gate: validate referential integrity and assert release gate is PASS. Exits 1 on failure."""
    from specforge_core.status import project_status

    project = Project(path)
    errors = validate_project(project)
    data = project_status(project)
    gate = str(data["gate"])
    unverified: list[dict[str, str]] = data["unverified_requirements"]  # type: ignore[assignment]
    open_tasks: list[dict[str, str]] = data["open_tasks"]  # type: ignore[assignment]

    ok = not errors and gate == "PASS"
    gate_color = "green" if gate == "PASS" else "red"
    console.print(f"Validate: {'[green]OK[/green]' if not errors else '[red]FAIL[/red]'}")
    console.print(f"Gate:     [{gate_color}]{gate}[/{gate_color}]")

    if errors:
        for e in errors:
            console.print(f"  [red]{e}[/red]")
    if unverified:
        console.print(f"  Unverified requirements: {len(unverified)}")
        for r in unverified:
            console.print(f"    {r['id']}: {r['title']}")
    if open_tasks:
        console.print(f"  Open tasks: {len(open_tasks)}")
        for t in open_tasks:
            console.print(f"    {t['id']} [{t['status']}]: {t['title']}")

    if not ok:
        raise typer.Exit(1)


@app.command()
def validate(path: Path) -> None:
    """Check all artifact links and status consistency. Exits 1 on errors."""
    project = Project(path)
    errors = validate_project(project)
    if not errors:
        console.print("Project validation passed.")
        return
    for error in errors:
        console.print(f"[red]{error}[/red]")
    raise typer.Exit(1)


@app.command("config")
def config_cmd(
    path: Path,
    set_kv: Optional[str] = typer.Option(None, "--set", help="Set key=value (e.g. --set git_commit=true)"),
) -> None:
    """Show or update project configuration (.specforge.yaml)."""
    project = Project(path)
    write_default_config(project.root)  # create default if missing
    cfg = load_config(project.root)

    if set_kv:
        key, _, raw = set_kv.partition("=")
        key = key.strip()
        raw = raw.strip()
        data = cfg.model_dump()

        # Support dotted keys for nested config (e.g. llm.provider)
        if "." in key:
            top, _, sub = key.partition(".")
            if top not in data or not isinstance(data[top], dict):
                console.print(f"[red]Unknown config key: {key!r}[/red]")
                raise typer.Exit(1)
            nested = data[top]
            if sub not in nested:
                console.print(f"[red]Unknown config key: {key!r}[/red]")
                raise typer.Exit(1)
            current = nested[sub]
            if isinstance(current, bool):
                nested[sub] = raw.lower() in ("true", "1", "yes")
            elif isinstance(current, int):
                nested[sub] = int(raw)
            else:
                nested[sub] = raw
            data[top] = nested
        else:
            if key not in data:
                console.print(f"[red]Unknown config key: {key!r}[/red]")
                raise typer.Exit(1)
            current = data[key]
            if isinstance(current, bool):
                data[key] = raw.lower() in ("true", "1", "yes")
            elif isinstance(current, int):
                data[key] = int(raw)
            else:
                data[key] = raw

        updated = ProjectConfig(**data)
        save_config(project.root, updated)
        project.reload_config()
        console.print(f"Set {key} = {raw}")
    else:
        console.print(f"[dim]{project.root / '.specforge.yaml'}[/dim]")
        for k, v in cfg.model_dump().items():
            console.print(f"  {k}: {v}")


@app.command()
def mcp(path: Path) -> None:
    """Start the MCP stdio server for this project (for Claude Code integration)."""
    from specforge_daemon.mcp_server import serve
    serve(str(path))


@app.command("mcp-config")
def mcp_config(path: Path) -> None:
    """Print the Claude Code MCP config snippet for this project."""
    import json
    import shutil

    exe = shutil.which("specforge") or "specforge"
    config = {
        "mcpServers": {
            "specforge": {
                "command": exe,
                "args": ["mcp", str(path.resolve())],
            }
        }
    }
    console.print(json.dumps(config, indent=2))
    console.print()
    console.print("[dim]Add the 'mcpServers' block to your Claude Code settings.json[/dim]")


@app.command("draft")
def draft_cmd(
    path: Path,
    kind: str = typer.Argument(..., help="Artifact kind (idea, requirement, task, test, …)"),
    prompt: str = typer.Argument(..., help="Free-form description of what to generate"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Artifact title (defaults to first 60 chars of prompt)"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Create artifact without confirmation prompt"),
    git: bool = typer.Option(False, "--git", help="Commit the new artifact to git"),
    tag: Optional[List[str]] = typer.Option(None, "--tag", help="Tag(s) for the new artifact"),
) -> None:
    """Generate artifact body with AI and create the artifact."""
    from specforge_core.llm import LLMError, _DRAFT_SYSTEM, complete_with_fallback
    from specforge_core.models import ArtifactKind

    project = Project(path)

    # Resolve kind
    kind_map = {k.value: k for k in ArtifactKind}
    kind_lower = kind.lower().replace("-", "_").replace(" ", "_")
    artifact_kind = kind_map.get(kind_lower)
    if artifact_kind is None:
        console.print(f"[red]Unknown artifact kind: {kind!r}[/red]")
        console.print(f"Valid kinds: {', '.join(k.value for k in ArtifactKind)}")
        raise typer.Exit(1)

    cfg = project.config
    artifact_title = title or (prompt[:60].rstrip() + ("…" if len(prompt) > 60 else ""))

    system = _DRAFT_SYSTEM + f"\n\nArtifact kind: {artifact_kind.value}"

    def _ask_fallback(error_msg: str) -> bool:
        console.print(f"[yellow]LLM error:[/yellow] {error_msg}")
        return typer.confirm("Use local Ollama instead?", default=False)

    console.print(f"[dim]Generating {artifact_kind.value} body via {cfg.llm.provider}…[/dim]")
    try:
        body = complete_with_fallback(prompt, system, cfg.llm, _ask_fallback)
    except LLMError as exc:
        console.print(f"[red]Draft failed:[/red] {exc}")
        raise typer.Exit(1)

    console.print(Panel(body, title=f"[bold]{artifact_title}[/bold]", border_style="cyan"))

    if not no_confirm:
        if not typer.confirm("Create artifact?", default=True):
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    artifact = project.create_artifact(
        artifact_kind,
        artifact_title,
        body,
        git_commit=_eg(project, git),
        tags=tag or None,
    )
    console.print(f"[green]Created:[/green] {artifact.id}  {artifact.title}")


@app.command("webhook")
def webhook_cmd(
    path: Path,
    action: str = typer.Argument(..., help="add, list, remove, or test"),
    url: Optional[str] = typer.Argument(None, help="Webhook URL (for add/remove/test)"),
    event: Optional[List[str]] = typer.Option(None, "--event", help="Event filter (can repeat; empty = all events)"),
    secret: Optional[str] = typer.Option(None, "--secret", help="Optional HMAC secret"),
) -> None:
    """Manage webhook subscriptions for artifact events."""
    import json as _json
    import urllib.request

    from specforge_core.webhooks import WebhookEntry

    project = Project(path)
    write_default_config(project.root)
    cfg = load_config(project.root)

    if action == "add":
        if not url:
            console.print("[red]URL required for 'add'[/red]")
            raise typer.Exit(1)
        entry = WebhookEntry(url=url, events=event or [], secret=secret or "")
        cfg.webhooks.append(entry)
        save_config(project.root, cfg)
        console.print(f"[green]Added webhook:[/green] {url}")
        if event:
            console.print(f"  events: {', '.join(event)}")
        if secret:
            console.print("  secret: (set)")

    elif action == "list":
        if not cfg.webhooks:
            console.print("[dim]No webhooks configured.[/dim]")
            return
        table = Table(title="Webhooks")
        table.add_column("URL")
        table.add_column("Events", style="cyan")
        table.add_column("Secret", style="dim")
        for entry in cfg.webhooks:
            events_str = ", ".join(entry.events) if entry.events else "(all)"
            secret_str = "(set)" if entry.secret else "(none)"
            table.add_row(entry.url, events_str, secret_str)
        console.print(table)

    elif action == "remove":
        if not url:
            console.print("[red]URL required for 'remove'[/red]")
            raise typer.Exit(1)
        original_count = len(cfg.webhooks)
        cfg.webhooks = [e for e in cfg.webhooks if e.url != url]
        if len(cfg.webhooks) < original_count:
            save_config(project.root, cfg)
            console.print(f"[green]Removed webhook:[/green] {url}")
        else:
            console.print(f"[yellow]Webhook not found:[/yellow] {url}")

    elif action == "test":
        if not url:
            console.print("[red]URL required for 'test'[/red]")
            raise typer.Exit(1)
        entry = next((e for e in cfg.webhooks if e.url == url), None)
        if not entry:
            console.print(f"[yellow]Webhook not found:[/yellow] {url}")
            raise typer.Exit(1)
        # Fire a synthetic ping event
        payload = {
            "event": "webhook.ping",
            "project": cfg.project_name or "specforge",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "artifact": None,
        }
        body = _json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if entry.secret:
            import hashlib
            import hmac
            sig = hmac.new(entry.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            headers["X-SpecForge-Signature"] = f"sha256={sig}"
        try:
            request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=5) as response:
                response.read()
            console.print(f"[green]Ping sent to[/green] {url}")
        except Exception as exc:
            console.print(f"[red]Ping failed:[/red] {exc}")
            raise typer.Exit(1)

    else:
        console.print(f"[red]Unknown action: {action!r}. Use 'add', 'list', 'remove', or 'test'.[/red]")
        raise typer.Exit(1)


@app.command("plugin")
def plugin_cmd(
    path: Path,
    action: str = typer.Argument(default="list", help="list (default)"),
) -> None:
    """Manage project plugins (.specforge/plugins/*.py)."""
    from specforge_core.plugins import PLUGINS_DIR

    project = Project(path)
    plugin_dir = project.root / PLUGINS_DIR

    if action != "list":
        console.print(f"[red]Unknown action: {action!r}. Only 'list' is supported.[/red]")
        raise typer.Exit(1)

    if not plugin_dir.is_dir():
        console.print(f"[dim]No plugins directory: {plugin_dir}[/dim]")
        return

    py_files = sorted(plugin_dir.glob("*.py"))
    if not py_files:
        console.print(f"[dim]No plugins found in {plugin_dir}[/dim]")
        console.print("[dim]Drop a .py file there to activate it.[/dim]")
        return

    table = Table(title=f"Plugins ({plugin_dir})")
    table.add_column("File", style="cyan")
    table.add_column("on_event", justify="center")
    for pyfile in py_files:
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location(f"_check_{pyfile.stem}", pyfile)
            if spec and spec.loader:
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                has_hook = "[green]yes[/green]" if hasattr(mod, "on_event") else "[yellow]no[/yellow]"
            else:
                has_hook = "[dim]?[/dim]"
        except Exception as exc:
            has_hook = f"[red]error: {exc}[/red]"
        table.add_row(pyfile.name, has_hook)
    console.print(table)


@app.command("bulk")
def bulk_cmd(
    path: Path,
    action: str = typer.Argument(..., help="update-status | archive | tag-add | tag-remove"),
    kind: Optional[List[str]] = typer.Option(None, "--kind", help="Filter by kind (repeatable)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by current status"),
    tag: Optional[List[str]] = typer.Option(None, "--tag", help="Filter by tag (repeatable, all must match)"),
    to: Optional[str] = typer.Option(None, "--to", help="Target status (for update-status)"),
    add_tag: Optional[List[str]] = typer.Option(None, "--add-tag", help="Tags to add (for tag-add)"),
    remove_tag: Optional[List[str]] = typer.Option(None, "--remove-tag", help="Tags to remove (for tag-remove)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing"),
) -> None:
    """Batch-update artifacts matching kind/status/tag filters."""
    from specforge_core.bulk import bulk_update

    project = Project(path)

    filters: dict = {}
    if kind:
        filters["kind"] = [*kind]
    if status:
        filters["status"] = status
    if tag:
        filters["tag"] = [*tag]

    params: dict = {}
    if to:
        params["to_status"] = to
    if add_tag:
        params["tags"] = [*add_tag]
    if remove_tag:
        params["tags"] = [*remove_tag]

    try:
        affected = bulk_update(project, action, filters, params, dry_run=dry_run)
    except (ValueError, KeyError) as exc:
        console.print(f"[red]Bulk error:[/red] {exc}")
        raise typer.Exit(1)

    if not affected:
        console.print("[dim]No artifacts matched the filters.[/dim]")
        return

    prefix = "[dim](dry-run)[/dim] " if dry_run else ""
    table = Table(title=f"{prefix}Bulk {action} — {len(affected)} artifact(s)")
    table.add_column("ID", style="cyan")
    table.add_column("Kind")
    table.add_column("Status")
    table.add_column("Title")
    for a in affected:
        table.add_row(a.id, a.kind.value, a.status.value, a.title)
    console.print(table)
    if dry_run:
        console.print("[dim]Dry run — no changes written.[/dim]")


@app.command("template")
def template_cmd(
    path: Path,
    action: str = typer.Argument(default="list", help="list, edit, or new"),
    kind: Optional[str] = typer.Argument(None, help="Artifact kind (for edit/new)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title for new artifact (for new)"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Create without confirmation (for new)"),
    git: bool = typer.Option(False, "--git"),
    tag: Optional[List[str]] = typer.Option(None, "--tag"),
) -> None:
    """Manage artifact templates (.specforge/templates/<kind>.md)."""
    from specforge_core.templates import TEMPLATES_DIR, list_templates, load_template
    from specforge_core.models import ArtifactKind

    project = Project(path)
    project.init()
    template_dir = project.root / TEMPLATES_DIR

    if action == "list":
        kinds = list_templates(project.root)
        if not kinds:
            console.print(f"[dim]No templates in {template_dir}[/dim]")
            return
        table = Table(title=f"Templates ({template_dir})")
        table.add_column("Kind", style="cyan")
        table.add_column("File")
        for k in kinds:
            table.add_row(k, f"{k}.md")
        console.print(table)

    elif action == "edit":
        if not kind:
            console.print("[red]Specify a kind: specforge template <path> edit <kind>[/red]")
            raise typer.Exit(1)
        template_file = template_dir / f"{kind}.md"
        if not template_file.exists():
            template_file.write_text(f"# {kind} template\n\n", encoding="utf-8")
        import os
        import subprocess
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
        if not editor:
            console.print("[red]No editor set. Export $VISUAL or $EDITOR.[/red]")
            raise typer.Exit(1)
        subprocess.call([editor, str(template_file)])
        console.print(f"[green]Template saved:[/green] {template_file}")

    elif action == "new":
        if not kind:
            console.print("[red]Specify a kind: specforge template <path> new <kind>[/red]")
            raise typer.Exit(1)
        kind_map = {k.value: k for k in ArtifactKind}
        artifact_kind = kind_map.get(kind.lower())
        if artifact_kind is None:
            console.print(f"[red]Unknown kind: {kind!r}[/red]")
            raise typer.Exit(1)
        body, metadata = load_template(project.root, kind.lower())
        if not body:
            console.print(f"[yellow]No template for {kind!r}. Use 'specforge template {path} edit {kind}' to create one.[/yellow]")
            raise typer.Exit(1)
        artifact_title = title or f"New {kind}"
        raw_tags = metadata.get("tags") or []
        try:
            template_tags = [str(t) for t in raw_tags]
        except (TypeError, ValueError):
            template_tags = []
        all_tags = (list(tag) if tag else []) + template_tags
        console.print(Panel(body, title=f"[bold]{artifact_title}[/bold] (from template)", border_style="cyan"))
        if not no_confirm:
            if not typer.confirm("Create artifact?", default=True):
                console.print("[dim]Cancelled.[/dim]")
                raise typer.Exit(0)
        artifact = project.create_artifact(
            artifact_kind, artifact_title, body,
            git_commit=_eg(project, git),
            tags=all_tags or None,
        )
        console.print(f"[green]Created:[/green] {artifact.id}  {artifact.title}")

    else:
        console.print(f"[red]Unknown action: {action!r}. Use 'list', 'edit', or 'new'.[/red]")
        raise typer.Exit(1)


def _eg(project: Project, flag: bool) -> bool:
    """Return effective git_commit: True if the flag was passed OR config has git_commit=true."""
    return flag or project.config.git_commit


def _git_init_project(root: Path) -> None:
    try:
        import git as gitpython
        repo = gitpython.Repo.init(root)
        with repo.config_writer() as cfg:
            if not cfg.has_option("user", "name"):
                cfg.set_value("user", "name", "SpecForge")
            if not cfg.has_option("user", "email"):
                cfg.set_value("user", "email", "specforge@local")
        repo.git.add(A=True)
        repo.index.commit("Initial SpecForge project structure")
        console.print(f"Git repository initialized and committed: {root}")
    except Exception as exc:
        console.print(f"[yellow]git init skipped: {exc}[/yellow]")
