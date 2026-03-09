"""Hunk dependency analysis.

Hunks in the same file can depend on each other when context lines overlap.
If hunk A precedes hunk B in the same file, and A's range extends close enough
to B's start, then B depends on A.
"""
from __future__ import annotations

from git_hunk_tool.models import FileDiff, Hunk

# Number of context lines git uses (default -U3)
_CONTEXT_LINES = 3


def compute_dependencies(files: list[FileDiff]) -> dict[int, list[int]]:
    """Compute hunk dependencies across all files.

    Returns a dict mapping global_index -> list of global_indices it depends on.
    Only intra-file dependencies are computed.
    """
    deps: dict[int, list[int]] = {}

    for fd in files:
        hunks = fd.hunks
        for i, hunk_b in enumerate(hunks):
            dep_list: list[int] = []
            for j in range(i):
                hunk_a = hunks[j]
                # If A's old range + context overlaps with B's old start
                a_end = hunk_a.metadata.old_start + hunk_a.metadata.old_count
                b_start = hunk_b.metadata.old_start
                if a_end + _CONTEXT_LINES >= b_start:
                    dep_list.append(hunk_a.id.global_index)
            if dep_list:
                deps[hunk_b.id.global_index] = dep_list

    return deps
