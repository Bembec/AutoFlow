"""Copy docs/help/*.md into the backend package so the help assistant ships with the API.

    python scripts/sync_help.py

docs/help is the master copy. A test fails when the two differ.
"""

import shutil
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "docs" / "help"
TARGET = Path(__file__).resolve().parents[1] / "src" / "autoflow" / "help_docs"


def main():
    TARGET.mkdir(exist_ok=True)
    for old in TARGET.glob("*.md"):
        old.unlink()
    for path in sorted(SOURCE.glob("*.md")):
        shutil.copyfile(path, TARGET / path.name)
        print("copied", path.name)


if __name__ == "__main__":
    main()
