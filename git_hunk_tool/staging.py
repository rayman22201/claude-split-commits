"""Patch assembly and staging via git apply --cached."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from git_hunk_tool.models import FileDiff, Hunk
from git_hunk_tool.git_ops import apply_patch_to_index, apply_patch_to_index_safe
from git_hunk_tool.errors import StagingError, GitError


def assemble_patch(hunks: list[Hunk], all_files: list[FileDiff]) -> str:
    """Build a valid unified diff patch from selected hunks.

    Groups hunks by file and reconstructs each file's diff header + selected hunks.
    """
    # Group hunks by file_index, preserving order
    by_file: dict[int, list[Hunk]] = defaultdict(list)
    for h in hunks:
        by_file[h.id.file_index].append(h)

    # Build file index lookup
    file_lookup = {fd.file_index: fd for fd in all_files}

    patches: list[str] = []
    for fi in sorted(by_file.keys()):
        fd = file_lookup[fi]
        file_hunks = by_file[fi]
        # Sort by hunk_index to maintain order
        file_hunks.sort(key=lambda h: h.id.hunk_index)

        # File header
        parts = [fd.diff_header]
        # Each hunk
        for h in file_hunks:
            parts.append(h.raw_header)
            parts.extend(h.raw_lines)

        patches.append("\n".join(parts))

    return "\n".join(patches) + "\n"


def stage_hunks(
    hunks: list[Hunk],
    all_files: list[FileDiff],
    cwd: Optional[str] = None,
) -> None:
    """Stage the given hunks to the git index.

    First tries to apply all hunks at once. On failure, falls back to
    per-hunk application to identify which hunk(s) failed.
    """
    if not hunks:
        return

    patch = assemble_patch(hunks, all_files)

    try:
        apply_patch_to_index(patch, cwd=cwd)
        return
    except GitError:
        pass

    # Fallback: try each hunk individually
    failed: list[str] = []
    for h in hunks:
        single_patch = assemble_patch([h], all_files)
        try:
            apply_patch_to_index(single_patch, cwd=cwd)
        except GitError as e:
            failed.append(f"Hunk {h.id} (global {h.id.global_index}): {e.stderr}")

    if failed:
        raise StagingError(
            "Failed to stage the following hunks:\n" + "\n".join(failed)
        )


def unstage_hunks(
    hunks: list[Hunk],
    all_files: list[FileDiff],
    cwd: Optional[str] = None,
) -> None:
    """Unstage specific hunks from the index by reverse-applying."""
    if not hunks:
        return

    from git_hunk_tool.git_ops import reverse_apply_from_index

    patch = assemble_patch(hunks, all_files)

    try:
        reverse_apply_from_index(patch, cwd=cwd)
    except GitError as e:
        raise StagingError(f"Failed to unstage hunks: {e.stderr}")
