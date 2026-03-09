"""CLI entry point with argparse subcommands."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from git_hunk_tool import errors
from git_hunk_tool.models import FileDiff, resolve_hunk_ids
from git_hunk_tool.parser import parse_diff
from git_hunk_tool import git_ops
from git_hunk_tool import formatter
from git_hunk_tool.staging import stage_hunks, unstage_hunks
from git_hunk_tool.dependency import compute_dependencies


def _get_diff(source: str, cwd: Optional[str] = None) -> tuple[str, str]:
    """Get diff text and source label from a source specifier."""
    if source == "unstaged":
        return git_ops.get_unstaged_diff(cwd=cwd), "unstaged"
    elif source == "staged":
        return git_ops.get_staged_diff(cwd=cwd), "staged"
    elif source.startswith("commit:"):
        ref = source[7:]
        return git_ops.get_commit_diff(ref, cwd=cwd), f"commit:{ref}"
    else:
        print(f"Error: unknown source {source!r}", file=sys.stderr)
        sys.exit(1)


def _get_files(source: str, cwd: Optional[str] = None) -> tuple[list[FileDiff], str]:
    """Parse diff from source into FileDiff list."""
    diff_text, label = _get_diff(source, cwd=cwd)
    files = parse_diff(diff_text) if diff_text.strip() else []
    return files, label


def _find_hunk(files: list[FileDiff], global_id: int):
    """Find a hunk by global index, returning (hunk, file_diff)."""
    for fd in files:
        for h in fd.hunks:
            if h.id.global_index == global_id:
                return h, fd
    return None, None


def cmd_list(args: argparse.Namespace) -> None:
    files, label = _get_files(args.source, cwd=args.cwd)

    # Filter by file pattern if specified
    if args.file:
        import fnmatch
        files = [
            fd for fd in files
            if fnmatch.fnmatch(fd.new_path or fd.old_path or "", args.file)
            or fnmatch.fnmatch(fd.old_path or fd.new_path or "", args.file)
        ]

    fmt = args.format
    if fmt == "auto":
        print(formatter.auto_format(files, label))
    elif fmt == "json":
        print(formatter.format_json(files, label))
    elif fmt == "table":
        print(formatter.format_table(files, label))


def cmd_show(args: argparse.Namespace) -> None:
    files, _ = _get_files(args.source, cwd=args.cwd)
    hunks = resolve_hunk_ids(args.hunk_id, files)
    if not hunks:
        print("No hunks matched.", file=sys.stderr)
        sys.exit(1)

    for h in hunks:
        # Find the parent FileDiff
        _, fd = _find_hunk(files, h.id.global_index)
        if fd:
            print(formatter.format_hunk_detail(h, fd))
            print()


def cmd_stage(args: argparse.Namespace) -> None:
    files, _ = _get_files("unstaged", cwd=args.cwd)
    if not files:
        print("No unstaged changes.", file=sys.stderr)
        sys.exit(1)

    hunks = resolve_hunk_ids(args.ids, files)
    if not hunks:
        print("No hunks matched.", file=sys.stderr)
        sys.exit(1)

    # Warn about dependencies
    deps = compute_dependencies(files)
    selected_ids = {h.id.global_index for h in hunks}
    for h in hunks:
        hunk_deps = deps.get(h.id.global_index, [])
        missing = [d for d in hunk_deps if d not in selected_ids]
        if missing:
            print(
                f"Warning: hunk {h.id.global_index} depends on {missing} "
                f"which are not being staged.",
                file=sys.stderr,
            )

    stage_hunks(hunks, files, cwd=args.cwd)
    print(f"Staged {len(hunks)} hunk(s).")


def cmd_unstage(args: argparse.Namespace) -> None:
    if args.all:
        git_ops.reset_index(cwd=args.cwd)
        print("Reset staging area.")
        return

    if not args.ids:
        print("Error: specify hunk IDs or --all.", file=sys.stderr)
        sys.exit(1)

    # Parse staged diff to find hunks to unstage
    files, _ = _get_files("staged", cwd=args.cwd)
    if not files:
        print("Nothing staged.", file=sys.stderr)
        sys.exit(1)

    hunks = resolve_hunk_ids(args.ids, files)
    unstage_hunks(hunks, files, cwd=args.cwd)
    print(f"Unstaged {len(hunks)} hunk(s).")


def cmd_commit(args: argparse.Namespace) -> None:
    # Optionally stage hunks first
    if args.stage:
        files, _ = _get_files("unstaged", cwd=args.cwd)
        if not files:
            print("No unstaged changes to stage.", file=sys.stderr)
            sys.exit(1)
        hunks = resolve_hunk_ids(args.stage, files)
        stage_hunks(hunks, files, cwd=args.cwd)
        print(f"Staged {len(hunks)} hunk(s).")

    sha = git_ops.commit(args.message, cwd=args.cwd)
    print(f"Committed: {sha}")


def cmd_split_prep(args: argparse.Namespace) -> None:
    ref = args.ref

    if args.stash:
        # Stash any current changes first
        status = git_ops.git_status_short(cwd=args.cwd)
        if status.strip():
            git_ops.stash(cwd=args.cwd)
            print("Stashed current changes.")

    # Mixed reset to the parent of ref, so the commit's changes become unstaged
    git_ops.mixed_reset(f"{ref}~1", cwd=args.cwd)
    print(f"Reset to {ref}~1. Changes from {ref} are now unstaged.")
    print("Use 'list' to see hunks, then 'stage' + 'commit' to re-split.")


def cmd_resolve(args: argparse.Namespace) -> None:
    files, _ = _get_files(args.source, cwd=args.cwd)
    fingerprints = [fp.strip() for fp in args.fingerprints.split(",") if fp.strip()]

    by_fp: dict[str, int] = {}
    for fd in files:
        for h in fd.hunks:
            if h.fingerprint:
                by_fp[h.fingerprint] = h.id.global_index

    mapping = {}
    for fp in fingerprints:
        if fp in by_fp:
            mapping[fp] = by_fp[fp]
        else:
            mapping[fp] = None

    print(json.dumps(mapping, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    staged_diff = git_ops.get_staged_diff(cwd=args.cwd)
    unstaged_diff = git_ops.get_unstaged_diff(cwd=args.cwd)

    staged = parse_diff(staged_diff) if staged_diff.strip() else []
    unstaged = parse_diff(unstaged_diff) if unstaged_diff.strip() else []

    fmt = args.format
    if fmt == "auto":
        if sys.stdout.isatty():
            print(formatter.format_status_table(staged, unstaged))
        else:
            print(formatter.format_status_json(staged, unstaged))
    elif fmt == "json":
        print(formatter.format_status_json(staged, unstaged))
    elif fmt == "table":
        print(formatter.format_status_table(staged, unstaged))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="git-hunk-tool",
        description="Programmatic git hunk manipulation for AI-driven commit splitting.",
    )
    parser.add_argument(
        "-C", dest="cwd", default=None,
        help="Run as if git was started in this directory.",
    )

    subs = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subs.add_parser("list", help="List all hunks with metadata.")
    p_list.add_argument(
        "--source", default="unstaged",
        help="unstaged (default), staged, or commit:<ref>",
    )
    p_list.add_argument(
        "--format", default="auto", choices=["auto", "json", "table"],
    )
    p_list.add_argument("--file", default=None, help="Filter by file glob pattern.")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subs.add_parser("show", help="Show a hunk's full diff.")
    p_show.add_argument("hunk_id", help="Hunk ID (e.g., 3 or 0:2 or 3-7)")
    p_show.add_argument("--source", default="unstaged")
    p_show.set_defaults(func=cmd_show)

    # stage
    p_stage = subs.add_parser("stage", help="Stage specific hunks.")
    p_stage.add_argument("ids", help="Comma-separated hunk IDs (e.g., 3,5,0:2,7-9)")
    p_stage.set_defaults(func=cmd_stage)

    # unstage
    p_unstage = subs.add_parser("unstage", help="Unstage hunks or reset staging area.")
    p_unstage.add_argument("--all", action="store_true", help="Reset entire staging area.")
    p_unstage.add_argument("ids", nargs="?", default=None, help="Hunk IDs to unstage.")
    p_unstage.set_defaults(func=cmd_unstage)

    # commit
    p_commit = subs.add_parser("commit", help="Commit staged changes.")
    p_commit.add_argument("-m", "--message", required=True, help="Commit message.")
    p_commit.add_argument("--stage", default=None, help="Stage these hunk IDs first.")
    p_commit.set_defaults(func=cmd_commit)

    # split-prep
    p_split = subs.add_parser("split-prep", help="Soft-reset a commit to expose hunks.")
    p_split.add_argument("ref", help="Commit ref to split (e.g., HEAD)")
    p_split.add_argument("--stash", action="store_true", help="Stash current changes first.")
    p_split.set_defaults(func=cmd_split_prep)

    # resolve
    p_resolve = subs.add_parser("resolve", help="Map fingerprints to current global IDs.")
    p_resolve.add_argument("fingerprints", help="Comma-separated fingerprints to resolve.")
    p_resolve.add_argument("--source", default="unstaged")
    p_resolve.set_defaults(func=cmd_resolve)

    # status
    p_status = subs.add_parser("status", help="Show staged/unstaged hunk state.")
    p_status.add_argument(
        "--format", default="auto", choices=["auto", "json", "table"],
    )
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)

    try:
        args.func(args)
    except errors.HunkToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
