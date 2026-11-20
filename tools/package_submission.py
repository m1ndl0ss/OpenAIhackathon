"""Package the committed Redwood project and its evidence in a ZIP."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, text=True
    ).strip()
    directory = ROOT / ".clearance/submission"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"Redwood-submission-{revision[:7]}.zip"
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        subprocess.run(
            ["git", "archive", "--format=zip", "--prefix=Redwood/", "--output", str(temporary), revision],
            check=True, cwd=ROOT,
        )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(destination)


if __name__ == "__main__":
    main()
