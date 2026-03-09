"""Tests for the unified diff parser."""
from __future__ import annotations

import textwrap

import pytest

from git_hunk_tool.parser import parse_diff
from git_hunk_tool.models import ChangeType


def test_parse_sample_diff():
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)

    assert len(files) == 2

    # First file: src/main.c
    f0 = files[0]
    assert f0.old_path == "src/main.c"
    assert f0.new_path == "src/main.c"
    assert f0.change_type == ChangeType.MODIFIED
    assert len(f0.hunks) == 2

    h0 = f0.hunks[0]
    assert h0.id.global_index == 0
    assert h0.id.file_index == 0
    assert h0.id.hunk_index == 0
    assert h0.metadata.old_start == 1
    assert h0.metadata.old_count == 5
    assert h0.metadata.new_start == 1
    assert h0.metadata.new_count == 6

    h1 = f0.hunks[1]
    assert h1.id.global_index == 1
    assert h1.id.file_index == 0
    assert h1.id.hunk_index == 1
    assert "existing_func" in h1.metadata.function_context

    # Second file: src/util.c
    f1 = files[1]
    assert f1.old_path == "src/util.c"
    assert len(f1.hunks) == 1
    h2 = f1.hunks[0]
    assert h2.id.global_index == 2
    assert h2.metadata.lines_added == 1
    assert h2.metadata.lines_deleted == 1


def test_parse_new_file():
    diff = textwrap.dedent("""\
        diff --git a/new.txt b/new.txt
        new file mode 100644
        index 0000000..abc1234
        --- /dev/null
        +++ b/new.txt
        @@ -0,0 +1,3 @@
        +line 1
        +line 2
        +line 3
    """)
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].change_type == ChangeType.ADDED
    assert files[0].old_path is None
    assert files[0].new_path == "new.txt"
    assert files[0].hunks[0].metadata.is_pure_add is True


def test_parse_deleted_file():
    diff = textwrap.dedent("""\
        diff --git a/old.txt b/old.txt
        deleted file mode 100644
        index abc1234..0000000
        --- a/old.txt
        +++ /dev/null
        @@ -1,3 +0,0 @@
        -line 1
        -line 2
        -line 3
    """)
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].change_type == ChangeType.DELETED
    assert files[0].hunks[0].metadata.is_pure_delete is True


def test_parse_renamed_file():
    diff = textwrap.dedent("""\
        diff --git a/old_name.c b/new_name.c
        similarity index 95%
        rename from old_name.c
        rename to new_name.c
        index abc1234..def5678 100644
        --- a/old_name.c
        +++ b/new_name.c
        @@ -1,3 +1,3 @@
         int foo() {
        -    return 1;
        +    return 2;
         }
    """)
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].change_type == ChangeType.RENAMED
    assert files[0].old_path == "old_name.c"
    assert files[0].new_path == "new_name.c"


def test_parse_binary_file():
    diff = textwrap.dedent("""\
        diff --git a/image.png b/image.png
        index abc1234..def5678 100644
        Binary files a/image.png and b/image.png differ
    """)
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].change_type == ChangeType.BINARY
    assert files[0].is_binary is True
    assert len(files[0].hunks) == 0


def test_parse_no_newline_at_eof():
    diff = textwrap.dedent("""\
        diff --git a/file.txt b/file.txt
        index abc1234..def5678 100644
        --- a/file.txt
        +++ b/file.txt
        @@ -1,3 +1,3 @@
         line 1
        -line 2
        +line 2 modified
         line 3
        \\ No newline at end of file
    """)
    files = parse_diff(diff)
    assert len(files) == 1
    h = files[0].hunks[0]
    assert any("\\ No newline" in l for l in h.raw_lines)


def test_parse_empty_diff():
    files = parse_diff("")
    assert files == []


def test_parse_multiple_files_global_ids():
    """Global IDs are sequential across files."""
    from tests.conftest import SAMPLE_DIFF
    files = parse_diff(SAMPLE_DIFF)
    all_global = []
    for fd in files:
        for h in fd.hunks:
            all_global.append(h.id.global_index)
    assert all_global == [0, 1, 2]
