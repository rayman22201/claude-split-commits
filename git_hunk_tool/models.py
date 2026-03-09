"""Data models for git-hunk-tool."""
from __future__ import annotations

import enum
import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional

from git_hunk_tool.errors import InvalidHunkIdError


class ChangeType(enum.Enum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"
    BINARY = "binary"


@dataclass
class HunkId:
    """Identifies a hunk by file_index:hunk_index and a global sequential index."""
    file_index: int
    hunk_index: int
    global_index: int

    def __str__(self) -> str:
        return f"{self.file_index}:{self.hunk_index}"

    @property
    def short(self) -> str:
        return str(self.global_index)


@dataclass
class HunkMetadata:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    function_context: str
    lines_added: int
    lines_deleted: int
    is_pure_add: bool
    is_pure_delete: bool
    summary_line: str


def compute_fingerprint(file_path: str, raw_lines: list[str]) -> str:
    """Compute a stable content-based fingerprint for a hunk.

    Uses SHA-256 of file path + diff lines, truncated to 12 hex chars.
    """
    h = hashlib.sha256()
    h.update(file_path.encode("utf-8", errors="replace"))
    h.update(b"\x00")
    for line in raw_lines:
        h.update(line.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return h.hexdigest()[:12]


@dataclass
class Hunk:
    id: HunkId
    metadata: HunkMetadata
    raw_header: str
    raw_lines: list[str]
    fingerprint: str = ""


@dataclass
class FileDiff:
    file_index: int
    old_path: Optional[str]
    new_path: Optional[str]
    change_type: ChangeType
    hunks: list[Hunk]
    diff_header: str  # Everything before first @@
    is_binary: bool = False


_FINGERPRINT_RE = re.compile(r"[0-9a-f]{12}")


def parse_hunk_ids(spec: str) -> list[tuple[str, int | tuple[int, int] | str]]:
    """Parse a comma-separated hunk ID spec into a list of selectors.

    Returns list of:
      ("global", int)           - global index
      ("file_hunk", (fi, hi))   - file:hunk index
      ("range", (start, end))   - inclusive range of global indices
      ("fingerprint", str)      - content-based fingerprint (12 hex chars)
    """
    results = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if _FINGERPRINT_RE.fullmatch(part):
            results.append(("fingerprint", part))
        elif ":" in part:
            m = re.fullmatch(r"(\d+):(\d+)", part)
            if not m:
                raise InvalidHunkIdError(part)
            results.append(("file_hunk", (int(m.group(1)), int(m.group(2)))))
        elif "-" in part:
            m = re.fullmatch(r"(\d+)-(\d+)", part)
            if not m:
                raise InvalidHunkIdError(part)
            results.append(("range", (int(m.group(1)), int(m.group(2)))))
        else:
            m = re.fullmatch(r"(\d+)", part)
            if not m:
                raise InvalidHunkIdError(part)
            results.append(("global", int(m.group(1))))
    return results


def resolve_hunk_ids(spec: str, all_files: list[FileDiff]) -> list[Hunk]:
    """Resolve a hunk ID spec string to a list of Hunk objects."""
    # Build lookup tables
    by_global: dict[int, Hunk] = {}
    by_file_hunk: dict[tuple[int, int], Hunk] = {}
    by_fingerprint: dict[str, Hunk] = {}
    for fd in all_files:
        for h in fd.hunks:
            by_global[h.id.global_index] = h
            by_file_hunk[(h.id.file_index, h.id.hunk_index)] = h
            if h.fingerprint:
                by_fingerprint[h.fingerprint] = h

    selectors = parse_hunk_ids(spec)
    result: list[Hunk] = []
    seen: set[int] = set()

    for kind, val in selectors:
        if kind == "global":
            if val not in by_global:
                from git_hunk_tool.errors import HunkNotFoundError
                raise HunkNotFoundError(str(val))
            if val not in seen:
                seen.add(val)
                result.append(by_global[val])
        elif kind == "file_hunk":
            if val not in by_file_hunk:
                from git_hunk_tool.errors import HunkNotFoundError
                raise HunkNotFoundError(f"{val[0]}:{val[1]}")
            h = by_file_hunk[val]
            if h.id.global_index not in seen:
                seen.add(h.id.global_index)
                result.append(h)
        elif kind == "range":
            start, end = val
            for gi in range(start, end + 1):
                if gi not in by_global:
                    from git_hunk_tool.errors import HunkNotFoundError
                    raise HunkNotFoundError(str(gi))
                if gi not in seen:
                    seen.add(gi)
                    result.append(by_global[gi])
        elif kind == "fingerprint":
            if val not in by_fingerprint:
                from git_hunk_tool.errors import HunkNotFoundError
                raise HunkNotFoundError(val)
            h = by_fingerprint[val]
            if h.id.global_index not in seen:
                seen.add(h.id.global_index)
                result.append(h)

    return result
