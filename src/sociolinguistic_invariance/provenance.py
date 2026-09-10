import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitProvenance:
    """Git state associated with an evaluation execution."""

    available: bool
    commit: str | None
    worktree_clean: bool | None
    status_entry_count: int
    status_sha256: str | None

    def __post_init__(self) -> None:
        """Validate provenance consistency."""

        if self.status_entry_count < 0:
            raise ValueError(
                "status_entry_count must be non-negative."
            )

        if self.available:
            if self.commit is None:
                raise ValueError(
                    "Available Git provenance requires a commit."
                )

            _validate_git_object_id(
                self.commit
            )

            if self.worktree_clean is None:
                raise ValueError(
                    "Available Git provenance requires "
                    "worktree_clean."
                )

            if self.status_sha256 is None:
                raise ValueError(
                    "Available Git provenance requires "
                    "status_sha256."
                )

            _validate_sha256(
                self.status_sha256
            )

            expected_clean = (
                self.status_entry_count == 0
            )

            if self.worktree_clean is not expected_clean:
                raise ValueError(
                    "worktree_clean is inconsistent with "
                    "status_entry_count."
                )

        else:
            if self.commit is not None:
                raise ValueError(
                    "Unavailable Git provenance must not "
                    "contain a commit."
                )

            if self.worktree_clean is not None:
                raise ValueError(
                    "Unavailable Git provenance must not "
                    "contain worktree_clean."
                )

            if self.status_entry_count != 0:
                raise ValueError(
                    "Unavailable Git provenance must have "
                    "status_entry_count equal to 0."
                )

            if self.status_sha256 is not None:
                raise ValueError(
                    "Unavailable Git provenance must not "
                    "contain status_sha256."
                )


def _validate_git_object_id(
    value: str,
) -> None:
    """Validate a full Git SHA-1 or SHA-256 object identifier."""

    if len(value) not in {
        40,
        64,
    }:
        raise ValueError(
            "Git commit must contain 40 or 64 "
            "hexadecimal characters."
        )

    if any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(
            "Git commit must be lowercase hexadecimal."
        )


def _validate_sha256(
    value: str,
) -> None:
    """Validate a lowercase SHA-256 hexadecimal digest."""

    if len(value) != 64:
        raise ValueError(
            "status_sha256 must contain exactly "
            "64 hexadecimal characters."
        )

    if any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(
            "status_sha256 must be lowercase hexadecimal."
        )


def _sha256_text(
    value: str,
) -> str:
    """Hash exact UTF-8 text."""

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def _run_git(
    repo_root: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run one read-only Git command."""

    return subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def capture_git_provenance(
    repo_root: Path,
) -> GitProvenance:
    """Capture commit identity and working-tree state."""

    commit_result = _run_git(
        repo_root,
        "rev-parse",
        "HEAD",
    )

    status_result = _run_git(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )

    if (
        commit_result.returncode != 0
        or status_result.returncode != 0
    ):
        return GitProvenance(
            available=False,
            commit=None,
            worktree_clean=None,
            status_entry_count=0,
            status_sha256=None,
        )

    commit = commit_result.stdout.strip()

    status_text = status_result.stdout

    status_entries = tuple(
        line
        for line in status_text.splitlines()
        if line
    )

    return GitProvenance(
        available=True,
        commit=commit,
        worktree_clean=(
            len(status_entries) == 0
        ),
        status_entry_count=len(
            status_entries
        ),
        status_sha256=_sha256_text(
            status_text
        ),
    )


def require_clean_git_worktree(
    provenance: GitProvenance,
) -> None:
    """Reject execution without reproducible clean Git provenance."""

    if not provenance.available:
        raise RuntimeError(
            "Git provenance is unavailable. "
            "A reproducible evaluation requires "
            "an identifiable Git repository."
        )

    if not provenance.worktree_clean:
        raise RuntimeError(
            "Git working tree is not clean. "
            "Commit or otherwise resolve local changes "
            "before a reproducible evaluation."
        )


def git_provenance_to_dict(
    provenance: GitProvenance,
) -> dict[str, object]:
    """Serialize Git provenance without exposing file paths."""

    return {
        "available": provenance.available,
        "commit": provenance.commit,
        "worktree_clean": provenance.worktree_clean,
        "status_entry_count": (
            provenance.status_entry_count
        ),
        "status_sha256": provenance.status_sha256,
    }