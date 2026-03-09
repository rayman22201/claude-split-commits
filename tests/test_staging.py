"""Tests for staging and patch assembly."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from git_hunk_tool.parser import parse_diff
from git_hunk_tool.staging import assemble_patch, stage_hunks
from git_hunk_tool.models import resolve_hunk_ids
from git_hunk_tool import git_ops


def _run(repo: Path, *args):
    return subprocess.run(
        args, cwd=str(repo), capture_output=True, text=True, check=True,
    )


def test_assemble_patch_single_hunk():
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)
    # Select just the first hunk
    hunks = resolve_hunk_ids("0", files)
    patch = assemble_patch(hunks, files)
    assert "diff --git" in patch
    assert "@@ -1,5 +1,6 @@" in patch
    # Should not contain the second hunk
    assert "void existing_func()" not in patch


def test_assemble_patch_multiple_hunks_same_file():
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)
    hunks = resolve_hunk_ids("0,1", files)
    patch = assemble_patch(hunks, files)
    # Both hunks from main.c
    assert "@@ -1,5 +1,6 @@" in patch
    assert "void existing_func()" in patch
    # No util.c
    assert "src/util.c" not in patch


def test_assemble_patch_cross_file():
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)
    hunks = resolve_hunk_ids("0,2", files)
    patch = assemble_patch(hunks, files)
    assert "src/main.c" in patch
    assert "src/util.c" in patch


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not available",
)
def test_stage_hunks_in_real_repo(repo_with_changes: Path):
    """Stage specific hunks and verify git diff --cached."""
    repo = repo_with_changes

    # Get unstaged diff
    diff_text = git_ops.get_unstaged_diff(cwd=str(repo))
    files = parse_diff(diff_text)
    assert len(files) > 0

    # Stage just the first hunk
    hunks = resolve_hunk_ids("0", files)
    stage_hunks(hunks, files, cwd=str(repo))

    # Verify something got staged
    staged = git_ops.get_staged_diff(cwd=str(repo))
    assert staged.strip() != ""

    # The staged diff should contain the first hunk's changes
    staged_files = parse_diff(staged)
    assert len(staged_files) >= 1
