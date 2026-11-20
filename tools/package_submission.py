"""Export the committed, runnable jury hand-in with portable local evidence links."""
import io
import subprocess
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENTS = (
    "README.md", "SUBMISSION.md", "Makefile", ".env.example", ".gitignore",
    "requirements.txt", "requirements-dev.txt", "backend", "console", "data",
    "docs", "eval", "evidence", "legal", "output/pdf", "policy", "research",
    "submission", "tests", "tools", "scripts/brane_client.py",
    "scripts/check_failure_test.py", "scripts/case_tokeniser.py",
    ":(exclude,glob)docs/**/*.py",
)


def main():
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, text=True
    ).strip()
    snapshot = subprocess.check_output(
        ["git", "archive", "--format=tar", revision, "--", *CONTENTS], cwd=ROOT
    )
    directory = ROOT / ".clearance/submission"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"Redwood-submission-{revision[:7]}.zip"
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as source, zipfile.ZipFile(temporary, "w") as output:
            for file in source.getmembers():
                if not (file.isfile() or file.issym()):
                    continue
                # Older evidence links in the repo become ordinary CSVs in the ZIP.
                with source.extractfile(file) as contents:
                    entry = zipfile.ZipInfo("Redwood/" + file.name, time.gmtime(file.mtime)[:6])
                    entry.create_system = 3
                    mode = 0o644 if file.issym() else file.mode
                    entry.external_attr = (0o100000 | mode) << 16
                    output.writestr(entry, contents.read(), compress_type=zipfile.ZIP_DEFLATED)
            output.comment = ("Redwood submission from Git commit " + revision).encode("ascii")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(destination)


if __name__ == "__main__":
    main()
