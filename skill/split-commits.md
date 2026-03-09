# Split Commits

Split a dirty working tree or existing commit into multiple logical commits using git-hunk-tool.

## Workflow A: Split Unstaged Changes

1. **List all hunks** to understand the changes:
   ```
   {{PYTHON}} -m git_hunk_tool list --format json
   ```

2. **Analyze hunks** and group them into logical commits based on:
   - Function context (which function each hunk modifies)
   - File relationships (header + implementation pairings)
   - Dependency chains (dependent hunks must go together or in order)
   - Change type (whitespace-only, tests, feature code, bugfixes)

3. **Present grouping plan** to the user for approval. For each proposed commit:
   - List the hunk **fingerprints** (the `fingerprint` field from JSON output)
   - Describe the commit message
   - Note any dependencies
   - Fingerprints are stable across commits — unlike global IDs, they don't shift when earlier hunks are committed

4. **Execute** the plan after user approval:
   ```
   # For each group in sequence:
   {{PYTHON}} -m git_hunk_tool commit --stage <fingerprint1>,<fingerprint2> -m "<message>"
   ```

5. **Verify** with `git log --oneline` that commits look correct.

## Workflow B: Split an Existing Commit

1. **Prepare** by soft-resetting the target commit:
   ```
   {{PYTHON}} -m git_hunk_tool split-prep HEAD --stash
   ```

2. Then follow Workflow A steps 1-5 to re-commit the changes in logical groups.

3. If changes were stashed, pop them after:
   ```
   git stash pop
   ```

## Tips

- Use `show <id>` to inspect individual hunks when the summary isn't clear enough.
- Use `status --format json` between stage+commit operations to verify state.
- Hunks with `depends_on` entries should be staged together with their dependencies, or the dependency staged first.
- Pure additions (`is_pure_add: true`) are safest to stage independently.
- Binary files are all-or-nothing.
- Use `resolve <fingerprints>` to map fingerprints to current global IDs (useful for debugging).
