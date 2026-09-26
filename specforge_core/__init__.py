"""SpecForge core package."""

__version__ = "0.21.1"

from .models import ArtifactKind, ArtifactStatus, Artifact
from .project import Project
from .trace import TraceIndex

__all__ = [
    "__version__",
    "ArtifactKind",
    "ArtifactStatus",
    "Artifact",
    "Project",
    "TraceIndex",
]
