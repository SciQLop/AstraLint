"""Expand CLI input paths against include/exclude glob patterns."""

from collections.abc import Iterable
from pathlib import Path, PurePath


def _matches_any(path: Path, patterns: Iterable[str]) -> bool:
    return any(PurePath(path).match(pat) or _full_match(path, pat) for pat in patterns)


def _full_match(path: Path, pattern: str) -> bool:
    # Path.match doesn't support '**' across directories; use full_match (3.13+).
    fm = getattr(path, "full_match", None)
    return bool(fm(pattern)) if fm else False


def _expand_one(root: Path, include: list[str], exclude: list[str]) -> list[Path]:
    matches: set[Path] = set()
    for pattern in include:
        matches.update(p for p in root.glob(pattern) if p.is_file())
    if exclude:
        matches = {p for p in matches if not _matches_any(p, exclude)}
    return sorted(matches)


def expand_lint_paths(paths: Iterable[Path], include: list[str], exclude: list[str]) -> list[Path]:
    """Expand each input path: files pass through; directories are globbed.

    Files passed directly bypass the include filter (the user explicitly chose them)
    but are still dropped if they match an exclude pattern.
    """
    expanded: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        if path.is_file():
            if exclude and _matches_any(path, exclude):
                continue
            if path not in seen:
                expanded.append(path)
                seen.add(path)
        else:
            for p in _expand_one(path, include, exclude):
                if p not in seen:
                    expanded.append(p)
                    seen.add(p)
    return expanded
