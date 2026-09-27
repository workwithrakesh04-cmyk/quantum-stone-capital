"""Generate docs/FILE_TREE.md from git-tracked files."""
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def get_files():
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [f for f in r.stdout.splitlines() if f.strip()]


def build_tree():
    files = get_files()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# File Tree - Quantum Stone Capital",
        "",
        "Auto-generated: " + now,
        "",
        "Total files: " + str(len(files)),
        "",
        "```",
    ]
    lines.extend(sorted(files))
    lines.append("```")
    lines.append("")
    out = Path("docs/FILE_TREE.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("OK: wrote docs/FILE_TREE.md (" + str(len(files)) + " files)")


if __name__ == "__main__":
    build_tree()
