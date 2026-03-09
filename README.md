# claude-split-commits

A [Claude Code](https://claude.ai/claude-code) skill and Python tool for splitting a dirty working tree or existing commit into multiple logical commits.

Uses `git-hunk-tool`, a Python library that parses unified diffs into individually addressable hunks with metadata (function context, dependencies, fingerprints), then stages selected hunks via `git apply --cached`.

## Quick Install

```bash
# Clone
git clone git@github.com:rayman22201/claude-split-commits.git
cd claude-split-commits

# Linux / macOS / Git Bash
bash install.sh

# Windows cmd
install.bat
```

The install script:
1. Detects whether `python` or `python3` is the correct Python 3 binary
2. Installs `git-hunk-tool` as a Python package (`pip install .`)
3. Copies the `/split-commits` skill to `~/.claude/commands/` with the correct python command

## Usage

In any Claude Code session inside a git repo:

```
/split-commits
```

Claude will:
1. List all hunks in your unstaged changes
2. Analyze and group them into logical commits (by function, file relationships, dependencies, change type)
3. Present the plan for your approval
4. Execute the commits using content-based fingerprints (stable across commits)

### Splitting an existing commit

The skill also supports splitting an already-committed change back into multiple commits via `split-prep`.

## git-hunk-tool CLI

The underlying tool can also be used standalone:

```bash
# List hunks as JSON
python -m git_hunk_tool list --format json

# Show a specific hunk's full diff
python -m git_hunk_tool show 3

# Stage specific hunks by ID, range, or fingerprint
python -m git_hunk_tool stage 0,2,5

# Stage + commit in one step
python -m git_hunk_tool commit --stage 0,1 -m "Add feature X"

# View staged/unstaged state
python -m git_hunk_tool status

# Resolve fingerprints to current global IDs
python -m git_hunk_tool resolve abc123def456
```

## Requirements

- Python 3.10+
- Git

## Tests

```bash
pip install pytest
pytest
```

## License

[MIT](LICENSE)
