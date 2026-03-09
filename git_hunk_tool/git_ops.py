"""Git subprocess wrappers."""
from __future__ import annotations

import subprocess
from typing import Optional

from git_hunk_tool.errors import GitError


def _run(args: list[str], cwd: Optional[str] = None, stdin: Optional[str] = None) -> str:
    """Run a git command and return stdout. Raises GitError on failure.

    Uses binary mode for stdin to avoid Windows text-mode \\r\\n conversion
    which corrupts patch data fed to git apply.
    """
    cmd_str = " ".join(args)
    stdin_bytes = stdin.encode("utf-8") if stdin is not None else None
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            cwd=cwd,
            input=stdin_bytes,
        )
    except FileNotFoundError:
        raise GitError(cmd_str, -1, "git executable not found")

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(cmd_str, result.returncode, stderr)

    return result.stdout.decode("utf-8", errors="replace")


def get_unstaged_diff(cwd: Optional[str] = None) -> str:
    """Get the full unstaged diff (working tree vs index)."""
    return _run(["git", "diff", "--no-color", "-U3"], cwd=cwd)


def get_staged_diff(cwd: Optional[str] = None) -> str:
    """Get the full staged diff (index vs HEAD)."""
    return _run(["git", "diff", "--cached", "--no-color", "-U3"], cwd=cwd)


def get_commit_diff(ref: str, cwd: Optional[str] = None) -> str:
    """Get the diff introduced by a specific commit."""
    return _run(["git", "diff", "--no-color", "-U3", f"{ref}~1", ref], cwd=cwd)


def apply_patch_to_index(patch: str, cwd: Optional[str] = None) -> None:
    """Apply a patch to the index (staging area) without touching the working tree."""
    _run(
        ["git", "apply", "--cached", "--unidiff-zero", "-"],
        cwd=cwd,
        stdin=patch,
    )


def apply_patch_to_index_safe(patch: str, cwd: Optional[str] = None) -> None:
    """Apply a patch to the index. Does NOT use --unidiff-zero (stricter)."""
    _run(
        ["git", "apply", "--cached", "-"],
        cwd=cwd,
        stdin=patch,
    )


def reset_index(cwd: Optional[str] = None) -> None:
    """Reset the entire staging area (git reset)."""
    _run(["git", "reset"], cwd=cwd)


def reset_index_file(path: str, cwd: Optional[str] = None) -> None:
    """Reset a specific file in the staging area."""
    _run(["git", "reset", "--", path], cwd=cwd)


def commit(message: str, cwd: Optional[str] = None) -> str:
    """Create a commit with the given message. Returns the commit hash."""
    _run(["git", "commit", "-m", message], cwd=cwd)
    return _run(["git", "rev-parse", "HEAD"], cwd=cwd).strip()


def soft_reset(ref: str, cwd: Optional[str] = None) -> None:
    """Soft-reset to the given ref (keeps changes staged)."""
    _run(["git", "reset", "--soft", ref], cwd=cwd)


def mixed_reset(ref: str, cwd: Optional[str] = None) -> None:
    """Mixed-reset to the given ref (unstages changes but keeps working tree)."""
    _run(["git", "reset", "--mixed", ref], cwd=cwd)


def stash(cwd: Optional[str] = None) -> None:
    """Stash current changes."""
    _run(["git", "stash"], cwd=cwd)


def stash_pop(cwd: Optional[str] = None) -> None:
    """Pop the top stash entry."""
    _run(["git", "stash", "pop"], cwd=cwd)


def git_status_short(cwd: Optional[str] = None) -> str:
    """Get short status output."""
    return _run(["git", "status", "--short"], cwd=cwd)


def git_log_oneline(n: int = 10, cwd: Optional[str] = None) -> str:
    """Get recent log in oneline format."""
    return _run(["git", "log", f"--oneline", f"-{n}"], cwd=cwd)


def reverse_apply_from_index(patch: str, cwd: Optional[str] = None) -> None:
    """Reverse-apply a patch from the index (unstage specific hunks)."""
    _run(
        ["git", "apply", "--cached", "--reverse", "-"],
        cwd=cwd,
        stdin=patch,
    )
