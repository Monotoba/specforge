import git as gitpython

from specforge_core.gitwrap import artifact_log, commit_artifact, find_repo
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project


def _init_repo(path):
    repo = gitpython.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    return repo


def test_find_repo_returns_none_outside_git(tmp_path):
    assert find_repo(tmp_path / "not_a_repo") is None


def test_find_repo_finds_repo(tmp_path):
    _init_repo(tmp_path)
    assert find_repo(tmp_path) is not None


def test_commit_artifact_returns_sha(tmp_path):
    _init_repo(tmp_path)
    project = Project(tmp_path / "proj")
    project.init()
    artifact = project.create_artifact(ArtifactKind.IDEA, "Test idea", "Body.")
    assert artifact.path is not None
    sha = commit_artifact(tmp_path, artifact.path, "Add test idea")
    assert sha is not None
    assert len(sha) == 8


def test_commit_artifact_outside_repo_returns_none(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    artifact = project.create_artifact(ArtifactKind.IDEA, "Test idea", "Body.")
    assert artifact.path is not None
    sha = commit_artifact(tmp_path, artifact.path, "Should skip")
    assert sha is None


def test_create_artifact_with_git_commit(tmp_path):
    _init_repo(tmp_path)
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Git idea", "Body.", git_commit=True)
    entries = artifact_log(tmp_path)
    assert any("Git idea" in e["message"] for e in entries)


def test_update_status_with_git_commit(tmp_path):
    _init_repo(tmp_path)
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export.", status=ArtifactStatus.APPROVED,
    )
    project.update_status(req.id, ArtifactStatus.IMPLEMENTED, git_commit=True)
    entries = artifact_log(tmp_path)
    assert any("implemented" in e["message"] for e in entries)


def test_promote_artifact_with_git_commit(tmp_path):
    _init_repo(tmp_path)
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF export", "Explore.")
    project.promote_artifact(idea.id, ArtifactKind.CANDIDATE, git_commit=True)
    entries = artifact_log(tmp_path)
    assert any("Promote" in e["message"] for e in entries)


def test_artifact_log_empty_outside_repo(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    assert artifact_log(project.root) == []
