"""Tests for include/exclude pattern expansion when linting a directory."""

from pathlib import Path

import pytest

from astralint.config.paths import expand_lint_paths


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "data" / "good").mkdir(parents=True)
    (tmp_path / "data" / "bad").mkdir(parents=True)
    (tmp_path / "test_data").mkdir()
    (tmp_path / "data" / "good" / "a.cdf").touch()
    (tmp_path / "data" / "good" / "b.cdf").touch()
    (tmp_path / "data" / "bad" / "c.cdf").touch()
    (tmp_path / "data" / "good" / "skip.txt").touch()
    (tmp_path / "test_data" / "x.cdf").touch()
    return tmp_path


class TestExpandLintPaths:
    def test_file_path_passes_through(self, tree):
        target = tree / "data" / "good" / "a.cdf"
        out = expand_lint_paths([target], include=["**/*.cdf"], exclude=[])
        assert out == [target]

    def test_directory_expanded_via_include(self, tree):
        out = expand_lint_paths([tree], include=["**/*.cdf"], exclude=[])
        names = sorted(p.name for p in out)
        assert names == ["a.cdf", "b.cdf", "c.cdf", "x.cdf"]

    def test_exclude_drops_matching_files(self, tree):
        out = expand_lint_paths(
            [tree], include=["**/*.cdf"], exclude=["**/test_data/**", "**/bad/**"]
        )
        names = sorted(p.name for p in out)
        assert names == ["a.cdf", "b.cdf"]

    def test_multiple_includes_combine(self, tree):
        (tree / "data" / "good" / "extra.fits").touch()
        out = expand_lint_paths([tree], include=["**/*.cdf", "**/*.fits"], exclude=[])
        suffixes = sorted({p.suffix for p in out})
        assert suffixes == [".cdf", ".fits"]

    def test_results_are_deduplicated(self, tree):
        out = expand_lint_paths([tree], include=["**/*.cdf", "data/**/*.cdf"], exclude=[])
        assert len(out) == len(set(out))

    def test_results_are_sorted(self, tree):
        out = expand_lint_paths([tree], include=["**/*.cdf"], exclude=[])
        assert out == sorted(out)

    def test_directory_with_no_matches_returns_empty(self, tmp_path):
        (tmp_path / "empty").mkdir()
        out = expand_lint_paths([tmp_path / "empty"], include=["**/*.cdf"], exclude=[])
        assert out == []

    def test_missing_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            expand_lint_paths([tmp_path / "does_not_exist"], include=["**/*.cdf"], exclude=[])
