"""Launch the one-click live rehearsal on loopback with disposable synthetic cases."""

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from scripts.brane_client import load_env

from .brane_client import check_policy
from .demo import make_principals
from .main import create_app, enable_demo_desks


@contextmanager
def rehearsal_app():
    with TemporaryDirectory(prefix="clearance-live-") as directory:
        app = create_app(Path(directory) / "rehearsal.sqlite3", make_principals(), mode="live")
        enable_demo_desks(app)
        yield app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    load_env()
    try:
        verified = check_policy()
    except RuntimeError as error:
        sys.exit(str(error))
    print(f"Live BRANE rehearsal · {verified} · new synthetic cases", flush=True)
    with rehearsal_app() as app:
        uvicorn.run(app, host="127.0.0.1", port=args.port, proxy_headers=False, access_log=False)


if __name__ == "__main__":
    main()
