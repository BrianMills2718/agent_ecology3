"""Serve the dashboard on its own, e.g. the Plan 27 pilot bounty board.

    uv run python -m agent_ecology3.dashboard --pilot ~/.local/state/agent_ecology3/pilots/tinydb --port 9095

``--pilot`` falls back to env AE3_PILOT_PATH; ``--aes`` to env AE3_AES_BIN.
"""

from __future__ import annotations

import argparse

import uvicorn

from .server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", help="pilot sandbox path (env AE3_PILOT_PATH)")
    parser.add_argument("--aes", help="aes executable (env AE3_AES_BIN)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9095)
    args = parser.parse_args()
    app = create_app(pilot_path=args.pilot, aes_bin=args.aes)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
