"""Fixtures for git-hunk-tool tests."""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path):
    """Create a temporary git repo with an initial commit.

    Returns the repo path. The repo has:
      - git init
      - An initial commit with a README
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args, **kwargs):
        return subprocess.run(
            args, cwd=str(repo), capture_output=True, text=True,
            check=True, **kwargs,
        )

    run("git", "init")
    run("git", "config", "user.email", "test@test.com")
    run("git", "config", "user.name", "Test")

    readme = repo / "README.md"
    readme.write_text("# Test Repo\n")
    run("git", "add", "README.md")
    run("git", "commit", "-m", "Initial commit")

    return repo


@pytest.fixture
def repo_with_changes(tmp_git_repo: Path):
    """A git repo with multiple unstaged changes across files.

    Creates:
      - src/main.c  (modified: adds printf + new function)
      - src/util.c  (modified: changes return value)
      - src/new.c   (new file)
    """
    repo = tmp_git_repo

    def run(*args, **kwargs):
        return subprocess.run(
            args, cwd=str(repo), capture_output=True, text=True,
            check=True, **kwargs,
        )

    # Create initial source files
    src = repo / "src"
    src.mkdir()

    main_c = src / "main.c"
    main_c.write_text(textwrap.dedent("""\
        #include <stdio.h>

        int main() {
            printf("hello\\n");
            return 0;
        }

        void existing_func() {
            int x = 1;
            int y = 2;
            printf("%d\\n", x + y);
        }
    """))

    util_c = src / "util.c"
    util_c.write_text(textwrap.dedent("""\
        int add(int a, int b) {
            return a + b;
        }

        int subtract(int a, int b) {
            return a - b;
        }
    """))

    run("git", "add", "src/main.c", "src/util.c")
    run("git", "commit", "-m", "Add source files")

    # Now make changes (unstaged)
    main_c.write_text(textwrap.dedent("""\
        #include <stdio.h>
        #include <stdlib.h>

        int main() {
            printf("hello world\\n");
            printf("goodbye\\n");
            return 0;
        }

        void existing_func() {
            int x = 1;
            int y = 2;
            int z = 3;
            printf("%d\\n", x + y + z);
        }

        void new_func() {
            printf("new\\n");
        }
    """))

    util_c.write_text(textwrap.dedent("""\
        int add(int a, int b) {
            return a + b + 0;
        }

        int subtract(int a, int b) {
            return a - b;
        }
    """))

    new_c = src / "new.c"
    new_c.write_text(textwrap.dedent("""\
        void brand_new() {
            // brand new file
        }
    """))
    run("git", "add", "src/new.c")

    return repo


SAMPLE_DIFF = textwrap.dedent("""\
    diff --git a/src/main.c b/src/main.c
    index abc1234..def5678 100644
    --- a/src/main.c
    +++ b/src/main.c
    @@ -1,5 +1,6 @@
     #include <stdio.h>
    +#include <stdlib.h>

     int main() {
    -    printf("hello\\n");
    +    printf("hello world\\n");
         return 0;
    @@ -10,4 +11,8 @@ void existing_func() {
         int x = 1;
         int y = 2;
    +    int z = 3;
    -    printf("%d\\n", x + y);
    +    printf("%d\\n", x + y + z);
     }
    +
    +void new_func() {
    +    printf("new\\n");
    +}
    diff --git a/src/util.c b/src/util.c
    index 1111111..2222222 100644
    --- a/src/util.c
    +++ b/src/util.c
    @@ -1,3 +1,3 @@
     int add(int a, int b) {
    -    return a + b;
    +    return a + b + 0;
     }
""")
