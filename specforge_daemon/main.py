from __future__ import annotations

import os

import uvicorn


def main() -> None:
    dev = os.environ.get("SPECFORGE_DEV", "").lower() in ("1", "true", "yes")
    uvicorn.run(
        "specforge_daemon.api:app",
        host="127.0.0.1",
        port=8765,
        reload=dev,          # set SPECFORGE_DEV=1 to auto-reload on source changes
    )


if __name__ == "__main__":
    main()
