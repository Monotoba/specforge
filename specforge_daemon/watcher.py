from __future__ import annotations

import logging
import os
import threading

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from specforge_core.idgen import ID_RE
from specforge_core.project import Project
from specforge_core.trace import TraceIndex

logger = logging.getLogger(__name__)


class _ArtifactHandler(FileSystemEventHandler):
    def __init__(self, project: Project) -> None:
        self._project = project
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = str(event.src_path)
        if not src.endswith(".md"):
            return
        # Only rebuild for artifact files (e.g. IDEA-0001-title.md), not
        # memory.md or other scaffold files that have no artifact front matter.
        if not ID_RE.search(os.path.basename(src)):
            return
        with self._lock:
            try:
                TraceIndex(self._project).rebuild()
                logger.debug("Trace index rebuilt after change: %s", src)
            except Exception:
                logger.exception("Failed to rebuild trace index")


class ProjectWatcher:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._observer: Observer | None = None

    def start(self) -> None:
        if self._observer is not None:
            self.stop()
        observer = Observer()
        observer.schedule(_ArtifactHandler(self._project), str(self._project.root), recursive=True)
        observer.start()
        self._observer = observer
        logger.info("Watching project: %s", self._project.root)

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
