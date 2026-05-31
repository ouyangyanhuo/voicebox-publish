from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(description="AudioScribe FastAPI sidecar server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=int(os.environ.get("AUDIOSCRIBE_PORT", "17493")), type=int)
    parser.add_argument("--install-dir", default=os.environ.get("AUDIOSCRIBE_INSTALL_DIR"))
    args = parser.parse_args()

    if args.install_dir:
        os.environ["AUDIOSCRIBE_INSTALL_DIR"] = str(Path(args.install_dir).resolve())

    uvicorn.run(
        "audioscribe.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
