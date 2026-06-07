"""
File system tools — extended version of ai_agent/tools.py
Same @tool pattern, same safe_path security, MORE tools.
"""
import pathlib
from langchain_core.tools import tool

import os

env_workspace = os.environ.get("AGENT_WORKSPACE")
if env_workspace:
    WORKSPACE = pathlib.Path(env_workspace)
else:
    WORKSPACE = pathlib.Path(__file__).parent.parent / "workspace"


def safe_path(path: str) -> pathlib.Path:
    """Same security function as ai_agent/tools.py — blocks path escapes."""
    # Strip workspace/ prefix if LLM adds it (avoids workspace/workspace/ double nesting)
    path = path.removeprefix("workspace/").removeprefix("./")
    p = (WORKSPACE / path).resolve()
    if WORKSPACE.resolve() not in p.parents and WORKSPACE.resolve() != p:
        raise ValueError(f"Path escape blocked: {path}")
    return p


# ── Tool 1: read_file (same as ai_agent) ──

@tool
def read_file(path: str) -> str:
    """Read the contents of a file at the given path inside the workspace."""
    p = safe_path(path)
    if not p.exists():
        return f"ERROR: File not found: {path}"
    return p.read_text(encoding="utf-8")


# ── Tool 2: write_file (same as ai_agent) ──

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed."""
    p = safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"✅ Wrote {len(content)} chars to {path}"


# ── Tool 3: edit_file (NEW — replace specific text) ──

@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace a specific piece of text in a file. Use this instead of rewriting the entire file."""
    p = safe_path(path)
    if not p.exists():
        return f"ERROR: File not found: {path}"
    content = p.read_text(encoding="utf-8")
    if old_text not in content:
        return f"ERROR: Text not found in {path}. Use read_file to see current content."
    count = content.count(old_text)
    content = content.replace(old_text, new_text, 1)
    p.write_text(content, encoding="utf-8")
    return f"✅ Replaced text in {path} (found {count} occurrence(s), replaced first)"


# ── Tool 4: list_files (same as ai_agent) ──

@tool
def list_files(directory: str = ".") -> str:
    """List all files in a directory inside the workspace. Use '.' for root."""
    p = safe_path(directory)
    if not p.exists():
        return "Directory does not exist."
    items = []
    for item in sorted(p.rglob("*")):
        if item.is_file():
            rel = item.relative_to(WORKSPACE)
            size = item.stat().st_size
            items.append(f"  {rel} ({size} bytes)")
    if not items:
        return "No files yet."
    return f"Files in workspace:\n" + "\n".join(items)


# ── Tool 5: search_in_files (NEW — grep) ──

@tool
def search_in_files(query: str, directory: str = ".") -> str:
    """Search for a text pattern across all files in the workspace. Like grep."""
    p = safe_path(directory)
    if not p.exists():
        return "Directory does not exist."
    results = []
    for fpath in p.rglob("*"):
        if fpath.is_file() and fpath.suffix in (".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md", ".txt", ".sh", ".yaml", ".yml", ".env", ".sql"):
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if query.lower() in line.lower():
                        rel = fpath.relative_to(WORKSPACE)
                        results.append(f"  {rel}:{i}: {line.strip()}")
            except Exception:
                pass
    if not results:
        return f"No matches found for '{query}'"
    return f"Found {len(results)} match(es):\n" + "\n".join(results[:30])


# ── Tool 6: delete_file (NEW) ──

@tool
def delete_file(path: str) -> str:
    """Delete a file from the workspace."""
    p = safe_path(path)
    if not p.exists():
        return f"ERROR: File not found: {path}"
    p.unlink()
    return f"✅ Deleted {path}"
