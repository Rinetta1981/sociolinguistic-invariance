import hashlib
import subprocess
from pathlib import Path

import pytest

from sociolinguistic_invariance.provenance import (
    GitProvenance,
    capture_git_provenance,
    git_provenance_to_dict,
    require_clean_git_worktree,
)

VALID_COMMIT = "a" * 40
VALID_STATUS_SHA256 = "b" * 64


def _run_git(
    repo_root: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run one Git command for test setup."""

    return subprocess.run(
        [
            "git",
            *arguments,
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def _create_committed_repository(
    tmp_path: Path,
) -> Path:
    """Create a temporary Git repository with one commit."""

    repo_root = tmp_path / "repo"

    repo_root.mkdir()

    _run_git(
        repo_root,
        "init",
    )

    _run_git(
        repo_root,
        "config",
        "user.name",
        "Test User",
    )

    _run_git(
        repo_root,
        "config",
        "user.email",
        "test@example.com",
    )

    tracked_file = (
        repo_root
        / "tracked.txt"
    )

    tracked_file.write_text(
        "initial content\n",
        encoding="utf-8",
    )

    _run_git(
        repo_root,
        "add",
        "tracked.txt",
    )

    _run_git(
        repo_root,
        "commit",
        "-m",
        "Initial test commit",
    )

    return repo_root


def test_available_provenance_requires_commit() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Available Git provenance "
            "requires a commit"
        ),
    ):
        GitProvenance(
            available=True,
            commit=None,
            worktree_clean=True,
            status_entry_count=0,
            status_sha256=VALID_STATUS_SHA256,
        )


@pytest.mark.parametrize(
    "commit",
    [
        "abc",
        "g" * 40,
        "A" * 40,
    ],
)
def test_available_provenance_rejects_invalid_commit(
    commit: str,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        GitProvenance(
            available=True,
            commit=commit,
            worktree_clean=True,
            status_entry_count=0,
            status_sha256=VALID_STATUS_SHA256,
        )


def test_available_provenance_requires_worktree_state() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Available Git provenance requires "
            "worktree_clean"
        ),
    ):
        GitProvenance(
            available=True,
            commit=VALID_COMMIT,
            worktree_clean=None,
            status_entry_count=0,
            status_sha256=VALID_STATUS_SHA256,
        )


def test_available_provenance_requires_status_hash() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Available Git provenance requires "
            "status_sha256"
        ),
    ):
        GitProvenance(
            available=True,
            commit=VALID_COMMIT,
            worktree_clean=True,
            status_entry_count=0,
            status_sha256=None,
        )


@pytest.mark.parametrize(
    "status_sha256",
    [
        "abc",
        "g" * 64,
        "A" * 64,
    ],
)
def test_available_provenance_rejects_invalid_status_hash(
    status_sha256: str,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        GitProvenance(
            available=True,
            commit=VALID_COMMIT,
            worktree_clean=True,
            status_entry_count=0,
            status_sha256=status_sha256,
        )


def test_provenance_rejects_negative_status_entry_count() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "status_entry_count must be "
            "non-negative"
        ),
    ):
        GitProvenance(
            available=True,
            commit=VALID_COMMIT,
            worktree_clean=True,
            status_entry_count=-1,
            status_sha256=VALID_STATUS_SHA256,
        )


@pytest.mark.parametrize(
    ("worktree_clean", "status_entry_count"),
    [
        (True, 1),
        (False, 0),
    ],
)
def test_available_provenance_rejects_inconsistent_clean_state(
    worktree_clean: bool,
    status_entry_count: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "worktree_clean is inconsistent "
            "with status_entry_count"
        ),
    ):
        GitProvenance(
            available=True,
            commit=VALID_COMMIT,
            worktree_clean=worktree_clean,
            status_entry_count=status_entry_count,
            status_sha256=VALID_STATUS_SHA256,
        )


def test_unavailable_provenance_is_valid_without_git_fields() -> None:
    provenance = GitProvenance(
        available=False,
        commit=None,
        worktree_clean=None,
        status_entry_count=0,
        status_sha256=None,
    )

    assert provenance.available is False
    assert provenance.commit is None
    assert provenance.worktree_clean is None
    assert provenance.status_sha256 is None


def test_unavailable_provenance_rejects_commit() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Unavailable Git provenance must "
            "not contain a commit"
        ),
    ):
        GitProvenance(
            available=False,
            commit=VALID_COMMIT,
            worktree_clean=None,
            status_entry_count=0,
            status_sha256=None,
        )


def test_unavailable_provenance_rejects_worktree_state() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Unavailable Git provenance must "
            "not contain worktree_clean"
        ),
    ):
        GitProvenance(
            available=False,
            commit=None,
            worktree_clean=False,
            status_entry_count=0,
            status_sha256=None,
        )


def test_unavailable_provenance_rejects_status_entries() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Unavailable Git provenance must "
            "have status_entry_count equal to 0"
        ),
    ):
        GitProvenance(
            available=False,
            commit=None,
            worktree_clean=None,
            status_entry_count=1,
            status_sha256=None,
        )


def test_unavailable_provenance_rejects_status_hash() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Unavailable Git provenance must "
            "not contain status_sha256"
        ),
    ):
        GitProvenance(
            available=False,
            commit=None,
            worktree_clean=None,
            status_entry_count=0,
            status_sha256=VALID_STATUS_SHA256,
        )


def test_capture_clean_repository(
    tmp_path: Path,
) -> None:
    repo_root = _create_committed_repository(
        tmp_path
    )

    provenance = capture_git_provenance(
        repo_root
    )

    assert provenance.available is True
    assert provenance.commit is not None
    assert len(provenance.commit) == 40
    assert provenance.worktree_clean is True
    assert provenance.status_entry_count == 0

    expected_hash = hashlib.sha256(
        b""
    ).hexdigest()

    assert provenance.status_sha256 == expected_hash


def test_capture_dirty_repository_with_modified_file(
    tmp_path: Path,
) -> None:
    repo_root = _create_committed_repository(
        tmp_path
    )

    tracked_file = (
        repo_root
        / "tracked.txt"
    )

    tracked_file.write_text(
        "modified content\n",
        encoding="utf-8",
    )

    provenance = capture_git_provenance(
        repo_root
    )

    assert provenance.available is True
    assert provenance.worktree_clean is False
    assert provenance.status_entry_count == 1
    assert provenance.status_sha256 is not None


def test_capture_dirty_repository_with_untracked_file(
    tmp_path: Path,
) -> None:
    repo_root = _create_committed_repository(
        tmp_path
    )

    untracked_file = (
        repo_root
        / "untracked.txt"
    )

    untracked_file.write_text(
        "untracked content\n",
        encoding="utf-8",
    )

    provenance = capture_git_provenance(
        repo_root
    )

    assert provenance.available is True
    assert provenance.worktree_clean is False
    assert provenance.status_entry_count == 1


def test_capture_outside_git_repository(
    tmp_path: Path,
) -> None:
    ordinary_directory = (
        tmp_path
        / "not-a-repository"
    )

    ordinary_directory.mkdir()

    provenance = capture_git_provenance(
        ordinary_directory
    )

    assert provenance == GitProvenance(
        available=False,
        commit=None,
        worktree_clean=None,
        status_entry_count=0,
        status_sha256=None,
    )


def test_clean_repository_passes_execution_gate(
    tmp_path: Path,
) -> None:
    repo_root = _create_committed_repository(
        tmp_path
    )

    provenance = capture_git_provenance(
        repo_root
    )

    require_clean_git_worktree(
        provenance
    )


def test_dirty_repository_fails_execution_gate(
    tmp_path: Path,
) -> None:
    repo_root = _create_committed_repository(
        tmp_path
    )

    (
        repo_root
        / "untracked.txt"
    ).write_text(
        "untracked\n",
        encoding="utf-8",
    )

    provenance = capture_git_provenance(
        repo_root
    )

    with pytest.raises(
        RuntimeError,
        match="Git working tree is not clean",
    ):
        require_clean_git_worktree(
            provenance
        )


def test_unavailable_git_fails_execution_gate() -> None:
    provenance = GitProvenance(
        available=False,
        commit=None,
        worktree_clean=None,
        status_entry_count=0,
        status_sha256=None,
    )

    with pytest.raises(
        RuntimeError,
        match="Git provenance is unavailable",
    ):
        require_clean_git_worktree(
            provenance
        )


def test_git_provenance_serialization() -> None:
    provenance = GitProvenance(
        available=True,
        commit=VALID_COMMIT,
        worktree_clean=False,
        status_entry_count=2,
        status_sha256=VALID_STATUS_SHA256,
    )

    assert git_provenance_to_dict(
        provenance
    ) == {
        "available": True,
        "commit": VALID_COMMIT,
        "worktree_clean": False,
        "status_entry_count": 2,
        "status_sha256": VALID_STATUS_SHA256,
    }