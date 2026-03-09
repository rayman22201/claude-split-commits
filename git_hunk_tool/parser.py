"""Unified diff parser: raw diff text -> list[FileDiff]."""
from __future__ import annotations

import re
from typing import Optional

from git_hunk_tool.models import (
    ChangeType, FileDiff, Hunk, HunkId, HunkMetadata, compute_fingerprint,
)
from git_hunk_tool.errors import ParseError


_HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$"
)


def _detect_change_type(header_lines: list[str]) -> tuple[ChangeType, bool]:
    """Detect change type from diff header lines."""
    is_binary = False
    has_rename = False
    has_new_file = False
    has_deleted_file = False

    for line in header_lines:
        if line.startswith("Binary files"):
            is_binary = True
        if line.startswith("rename from ") or line.startswith("rename to "):
            has_rename = True
        if line.startswith("new file mode"):
            has_new_file = True
        if line.startswith("deleted file mode"):
            has_deleted_file = True

    if is_binary:
        return ChangeType.BINARY, True
    if has_rename:
        return ChangeType.RENAMED, False
    if has_new_file:
        return ChangeType.ADDED, False
    if has_deleted_file:
        return ChangeType.DELETED, False
    return ChangeType.MODIFIED, False


def _extract_paths(diff_line: str, header_lines: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Extract old and new paths from diff header."""
    # Check for rename headers first
    old_path = None
    new_path = None
    for line in header_lines:
        if line.startswith("rename from "):
            old_path = line[len("rename from "):]
        elif line.startswith("rename to "):
            new_path = line[len("rename to "):]

    if old_path and new_path:
        return old_path, new_path

    # Parse from --- and +++ lines
    for line in header_lines:
        if line.startswith("--- "):
            p = line[4:]
            if p == "/dev/null":
                old_path = None
            elif p.startswith("a/"):
                old_path = p[2:]
            else:
                old_path = p
        elif line.startswith("+++ "):
            p = line[4:]
            if p == "/dev/null":
                new_path = None
            elif p.startswith("b/"):
                new_path = p[2:]
            else:
                new_path = p

    # Fallback: parse from diff --git line
    if old_path is None and new_path is None:
        m = re.match(r"diff --git a/(.*?) b/(.*?)$", diff_line)
        if m:
            old_path = m.group(1)
            new_path = m.group(2)

    return old_path, new_path


def _make_summary(lines: list[str]) -> str:
    """Pick the first meaningful added/changed line as summary."""
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            stripped = line[1:].strip()
            if stripped:
                return line.rstrip()
    for line in lines:
        if line.startswith("-") and not line.startswith("---"):
            stripped = line[1:].strip()
            if stripped:
                return line.rstrip()
    return ""


def parse_diff(diff_text: str) -> list[FileDiff]:
    """Parse a unified diff into a list of FileDiff objects.

    Handles: modified, added, deleted, renamed, binary, no-newline-at-EOF.
    """
    if not diff_text.strip():
        return []

    lines = diff_text.split("\n")
    # Remove trailing empty line from split
    if lines and lines[-1] == "":
        lines = lines[:-1]

    file_diffs: list[FileDiff] = []
    global_index = 0

    # Split into per-file sections
    file_starts: list[int] = []
    for i, line in enumerate(lines):
        if line.startswith("diff --git "):
            file_starts.append(i)

    if not file_starts:
        raise ParseError("No 'diff --git' headers found in diff text")

    for sec_idx, start in enumerate(file_starts):
        end = file_starts[sec_idx + 1] if sec_idx + 1 < len(file_starts) else len(lines)
        section = lines[start:end]

        diff_line = section[0]

        # Collect header lines (everything before first @@ or end of section)
        header_lines: list[str] = []
        first_hunk_offset: Optional[int] = None
        for j, sl in enumerate(section):
            if j == 0:
                header_lines.append(sl)
                continue
            if _HUNK_HEADER_RE.match(sl):
                first_hunk_offset = j
                break
            header_lines.append(sl)

        change_type, is_binary = _detect_change_type(header_lines)
        old_path, new_path = _extract_paths(diff_line, header_lines)
        diff_header = "\n".join(header_lines)

        # Parse hunks
        hunks: list[Hunk] = []
        if first_hunk_offset is not None:
            hunk_starts: list[int] = []
            for j in range(first_hunk_offset, len(section)):
                if _HUNK_HEADER_RE.match(section[j]):
                    hunk_starts.append(j)

            for hi, hs in enumerate(hunk_starts):
                he = hunk_starts[hi + 1] if hi + 1 < len(hunk_starts) else len(section)
                hunk_header = section[hs]
                hunk_body = section[hs + 1:he]

                m = _HUNK_HEADER_RE.match(hunk_header)
                if not m:
                    raise ParseError(f"Failed to parse hunk header: {hunk_header}")

                old_start = int(m.group(1))
                old_count = int(m.group(2)) if m.group(2) is not None else 1
                new_start = int(m.group(3))
                new_count = int(m.group(4)) if m.group(4) is not None else 1
                func_ctx = m.group(5).strip()

                added = sum(1 for l in hunk_body if l.startswith("+"))
                deleted = sum(1 for l in hunk_body if l.startswith("-"))

                fp = compute_fingerprint(
                    new_path or old_path or "", hunk_body,
                )
                hunk = Hunk(
                    id=HunkId(
                        file_index=sec_idx,
                        hunk_index=hi,
                        global_index=global_index,
                    ),
                    metadata=HunkMetadata(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        function_context=func_ctx,
                        lines_added=added,
                        lines_deleted=deleted,
                        is_pure_add=deleted == 0 and added > 0,
                        is_pure_delete=added == 0 and deleted > 0,
                        summary_line=_make_summary(hunk_body),
                    ),
                    raw_header=hunk_header,
                    raw_lines=hunk_body,
                    fingerprint=fp,
                )
                hunks.append(hunk)
                global_index += 1

        fd = FileDiff(
            file_index=sec_idx,
            old_path=old_path,
            new_path=new_path,
            change_type=change_type,
            hunks=hunks,
            diff_header=diff_header,
            is_binary=is_binary,
        )
        file_diffs.append(fd)

    return file_diffs
