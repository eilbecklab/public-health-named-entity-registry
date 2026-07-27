from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_local_markdown_links_resolve(repository_root: Path):
    missing: list[str] = []
    for document in sorted(repository_root.rglob("*.md")):
        if any(part in {".venv", "build"} for part in document.parts):
            continue
        for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_text = unquote(target.split("#", 1)[0]).strip("<>")
            if not path_text:
                continue
            target_path = (document.parent / path_text).resolve()
            if not target_path.exists():
                missing.append(f"{document.relative_to(repository_root)} -> {path_text}")
    assert not missing, "Missing local Markdown links:\n" + "\n".join(missing)
