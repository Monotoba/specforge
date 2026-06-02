import time

from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.trace import TraceIndex
from specforge_daemon.watcher import ProjectWatcher


def test_watcher_rebuilds_trace_on_file_change(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()

    watcher = ProjectWatcher(project)
    watcher.start()
    try:
        project.create_artifact(
            ArtifactKind.REQUIREMENT,
            "Export DXF",
            "The system shall export DXF.",
            status=ArtifactStatus.APPROVED,
        )
        time.sleep(0.5)
    finally:
        watcher.stop()

    assert TraceIndex(project).db_path.exists()
    rows = TraceIndex(project).unverified_requirements()
    assert len(rows) == 1
    assert rows[0]["title"] == "Export DXF"
