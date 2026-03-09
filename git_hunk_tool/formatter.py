"""JSON and table output formatting."""
from __future__ import annotations

import json
import sys
from typing import Optional

from git_hunk_tool.models import FileDiff, Hunk
from git_hunk_tool.dependency import compute_dependencies


def _hunk_to_dict(h: Hunk, deps: dict[int, list[int]]) -> dict:
    m = h.metadata
    return {
        "id": str(h.id),
        "global_id": h.id.global_index,
        "fingerprint": h.fingerprint,
        "old_range": f"{m.old_start},{m.old_count}",
        "new_range": f"{m.new_start},{m.new_count}",
        "function_context": m.function_context,
        "lines_added": m.lines_added,
        "lines_deleted": m.lines_deleted,
        "is_pure_add": m.is_pure_add,
        "is_pure_delete": m.is_pure_delete,
        "depends_on": deps.get(h.id.global_index, []),
        "summary_line": m.summary_line,
    }


def _file_to_dict(fd: FileDiff, deps: dict[int, list[int]]) -> dict:
    return {
        "file_index": fd.file_index,
        "path": fd.new_path or fd.old_path or "(unknown)",
        "old_path": fd.old_path,
        "new_path": fd.new_path,
        "change_type": fd.change_type.value,
        "is_binary": fd.is_binary,
        "hunks": [_hunk_to_dict(h, deps) for h in fd.hunks],
    }


def format_json(files: list[FileDiff], source: str) -> str:
    """Format file diffs as JSON."""
    deps = compute_dependencies(files)
    total_hunks = sum(len(fd.hunks) for fd in files)
    data = {
        "source": source,
        "total_hunks": total_hunks,
        "total_files": len(files),
        "files": [_file_to_dict(fd, deps) for fd in files],
    }
    return json.dumps(data, indent=2)


def format_table(files: list[FileDiff], source: str) -> str:
    """Format file diffs as a human-readable table."""
    deps = compute_dependencies(files)
    total_hunks = sum(len(fd.hunks) for fd in files)
    lines: list[str] = []
    lines.append(f"Source: {source}")
    lines.append(f"Files: {len(files)}  Hunks: {total_hunks}")
    lines.append("")

    for fd in files:
        path = fd.new_path or fd.old_path or "(unknown)"
        ct = fd.change_type.value.upper()
        if fd.is_binary:
            lines.append(f"  [{fd.file_index}] {path} ({ct}, binary)")
            continue

        lines.append(f"  [{fd.file_index}] {path} ({ct})")
        for h in fd.hunks:
            m = h.metadata
            dep_str = ""
            hunk_deps = deps.get(h.id.global_index, [])
            if hunk_deps:
                dep_str = f"  deps:{hunk_deps}"
            func = f"  {m.function_context}" if m.function_context else ""
            fp_str = f"  fp:{h.fingerprint}" if h.fingerprint else ""
            lines.append(
                f"    {h.id.global_index:>3} ({h.id})  "
                f"+{m.lines_added}/-{m.lines_deleted}  "
                f"@@ -{m.old_start},{m.old_count} +{m.new_start},{m.new_count} @@"
                f"{func}{dep_str}{fp_str}"
            )
            if m.summary_line:
                summary = m.summary_line[:80]
                lines.append(f"         {summary}")
        lines.append("")

    return "\n".join(lines)


def format_hunk_detail(hunk: Hunk, fd: FileDiff) -> str:
    """Format a single hunk with full diff content."""
    lines: list[str] = []
    path = fd.new_path or fd.old_path or "(unknown)"
    lines.append(f"File: {path} (file {fd.file_index})")
    lines.append(f"Hunk: {hunk.id} (global {hunk.id.global_index})")
    m = hunk.metadata
    lines.append(f"Range: -{m.old_start},{m.old_count} +{m.new_start},{m.new_count}")
    if m.function_context:
        lines.append(f"Function: {m.function_context}")
    lines.append(f"Added: {m.lines_added}  Deleted: {m.lines_deleted}")
    lines.append("")
    lines.append(hunk.raw_header)
    lines.extend(hunk.raw_lines)
    return "\n".join(lines)


def auto_format(files: list[FileDiff], source: str) -> str:
    """Auto-detect format: JSON when piped, table when TTY."""
    if sys.stdout.isatty():
        return format_table(files, source)
    return format_json(files, source)


def format_status_json(staged: list[FileDiff], unstaged: list[FileDiff]) -> str:
    """Format staged + unstaged state as JSON."""
    staged_deps = compute_dependencies(staged)
    unstaged_deps = compute_dependencies(unstaged)
    data = {
        "staged": {
            "total_hunks": sum(len(fd.hunks) for fd in staged),
            "total_files": len(staged),
            "files": [_file_to_dict(fd, staged_deps) for fd in staged],
        },
        "unstaged": {
            "total_hunks": sum(len(fd.hunks) for fd in unstaged),
            "total_files": len(unstaged),
            "files": [_file_to_dict(fd, unstaged_deps) for fd in unstaged],
        },
    }
    return json.dumps(data, indent=2)


def format_status_table(staged: list[FileDiff], unstaged: list[FileDiff]) -> str:
    """Format staged + unstaged state as a table."""
    parts: list[str] = []
    parts.append("=== STAGED ===")
    parts.append(format_table(staged, "staged"))
    parts.append("=== UNSTAGED ===")
    parts.append(format_table(unstaged, "unstaged"))
    return "\n".join(parts)
