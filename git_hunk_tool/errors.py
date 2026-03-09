"""Exception hierarchy for git-hunk-tool."""


class HunkToolError(Exception):
    """Base exception for all git-hunk-tool errors."""


class GitError(HunkToolError):
    """A git subprocess command failed."""

    def __init__(self, cmd: str, returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"git command failed (rc={returncode}): {cmd}\n{stderr}")


class ParseError(HunkToolError):
    """Failed to parse a unified diff."""


class HunkNotFoundError(HunkToolError):
    """Referenced hunk ID does not exist."""

    def __init__(self, hunk_id: str):
        self.hunk_id = hunk_id
        super().__init__(f"Hunk not found: {hunk_id}")


class StagingError(HunkToolError):
    """Failed to stage one or more hunks."""


class InvalidHunkIdError(HunkToolError):
    """Hunk ID string could not be parsed."""

    def __init__(self, raw: str):
        self.raw = raw
        super().__init__(f"Invalid hunk ID: {raw!r}")
