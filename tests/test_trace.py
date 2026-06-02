from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.trace import TraceIndex


def test_trace_finds_unverified_requirement(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF files",
        "The system shall export DXF files.",
        status=ArtifactStatus.APPROVED,
    )
    index = TraceIndex(project)
    index.rebuild()
    rows = index.unverified_requirements()
    assert rows == [{"id": req.id, "title": req.title, "status": "approved"}]


def test_trace_graph_includes_source_link(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF", "Explore DXF")
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF files",
        "The system shall export DXF files.",
        status=ArtifactStatus.APPROVED,
        source=idea.id,
    )
    index = TraceIndex(project)
    index.rebuild()
    graph = index.artifact_graph(req.id)
    assert {"dst_id": idea.id, "link_type": "source"} in graph["outgoing"]
