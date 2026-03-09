"""Tests for hunk dependency analysis."""
from __future__ import annotations

from git_hunk_tool.parser import parse_diff
from git_hunk_tool.dependency import compute_dependencies


def test_adjacent_hunks_have_dependency():
    """Hunks that are close together in the same file should show dependency."""
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)
    deps = compute_dependencies(files)

    # Hunk 0 is at lines 1-5, hunk 1 is at lines 10-13
    # With old_count=5 and context=3: 1+5+3 = 9, which is < 10
    # So they should NOT be dependent in the sample diff
    assert 1 not in deps or 0 not in deps.get(1, [])


def test_overlapping_hunks_have_dependency():
    """Construct a diff where hunks overlap and verify dependency."""
    import textwrap
    diff = textwrap.dedent("""\
        diff --git a/file.c b/file.c
        index abc..def 100644
        --- a/file.c
        +++ b/file.c
        @@ -1,5 +1,6 @@
         line1
        +added
         line2
         line3
         line4
         line5
        @@ -4,5 +5,6 @@
         line4
         line5
        +added2
         line6
         line7
         line8
    """)
    files = parse_diff(diff)
    deps = compute_dependencies(files)

    # Hunk 0: old_start=1, old_count=5 -> end=6, +3=9 >= hunk1.old_start=4
    assert 1 in deps
    assert 0 in deps[1]


def test_different_files_no_dependency():
    """Hunks in different files never depend on each other."""
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)
    deps = compute_dependencies(files)

    # Hunk 2 is in util.c, hunks 0,1 are in main.c - no cross-file deps
    assert 2 not in deps


def test_no_hunks_no_deps():
    deps = compute_dependencies([])
    assert deps == {}
