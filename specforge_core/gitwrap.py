from __future__ import annotations

from pathlib import Path

import git


def find_repo(root: Path) -> git.Repo | None:
    try:
        return git.Repo(root, search_parent_directories=True)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        return None


def commit_artifact(root: Path, artifact_path: Path, message: str) -> str | None:
    """Stage artifact_path and commit. Returns short SHA or None if no repo."""
    repo = find_repo(root)
    if repo is None:
        return None
    working = Path(str(repo.working_tree_dir))
    rel = artifact_path.relative_to(working)
    repo.index.add([str(rel)])
    commit = repo.index.commit(message)
    return str(commit.hexsha[:8])


def artifact_log(root: Path, max_count: int = 50) -> list[dict[str, str]]:
    """Return recent commits that touched files under root."""
    repo = find_repo(root)
    if repo is None:
        return []
    working = Path(str(repo.working_tree_dir))
    try:
        rel = str(root.relative_to(working))
    except ValueError:
        rel = "."
    commits = list(repo.iter_commits(paths=rel, max_count=max_count))
    return [
        {
            "sha": c.hexsha[:8],
            "date": c.committed_datetime.strftime("%Y-%m-%d %H:%M"),
            "author": c.author.name,
            "message": c.message.split("\n")[0].strip(),
        }
        for c in commits
    ]
