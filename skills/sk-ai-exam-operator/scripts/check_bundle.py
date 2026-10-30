#!/usr/bin/env python3
"""Check bundled skill entrypoints and pinned upstream bytes without modifying files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


OPERATOR = "sk-ai-exam-operator"


class BundleError(ValueError):
    """A bundle is missing, unsafe, or inconsistent with its lock file."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError(message)


def _relative(value: object, label: str) -> PurePosixPath:
    _require(isinstance(value, str) and bool(value), f"{label}: expected a relative path")
    _require("\\" not in value and ":" not in value, f"{label}: unsafe path {value!r}")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and all(part not in ("", ".", "..")
             for part in value.split("/")), f"{label}: unsafe path {value!r}")
    return path


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _file(root: Path, relative: object, label: str) -> Path:
    path = _relative(relative, label)
    _require(not _is_link(root), f"{label}: symbolic root is not allowed")
    target = root
    for part in path.parts:
        target = target / part
        _require(not _is_link(target), f"{label}: symbolic links are not allowed: {target}")
    _require(target.resolve().is_relative_to(root.resolve()), f"{label}: path escapes root")
    _require(target.is_file(), f"{label}: missing file {target}")
    return target


def _frontmatter(path: Path, expected_name: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    _require(bool(lines) and lines[0] == "---", f"{path}: missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise BundleError(f"{path}: unterminated YAML frontmatter") from exc
    fields = {}
    for line in lines[1:end]:
        match = re.fullmatch(r"(name|description):\s*(.*)", line)
        if not match:
            continue
        key, value = match.groups()
        _require(key not in fields, f"{path}: duplicate {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value.strip()
    _require(fields.get("name") == expected_name, f"{path}: name must be {expected_name!r}")
    _require(bool(fields.get("description")) and fields["description"] not in ("|", ">"),
             f"{path}: a nonempty single-line description is required")


def validate(root: Path, *, installed: bool = False) -> dict:
    """Validate a checkout root or an installed directory containing sibling skills."""
    root = Path(root).absolute()
    skills_root = root if installed else root / "skills"
    operator_root = skills_root / OPERATOR
    lock_path = _file(operator_root, "bundle-lock.json", "lock file")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise BundleError(f"invalid lock file: {exc}") from exc
    _require(isinstance(lock, dict), "lock must be an object")
    _require(type(lock.get("schema_version")) is int and lock["schema_version"] == 1,
             "unsupported schema_version")
    version = lock.get("version")
    _require(isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version) is not None,
             "invalid bundle version")
    sources = lock.get("sources")
    skills = lock.get("skills")
    _require(isinstance(sources, list) and bool(sources), "sources must be a nonempty list")
    _require(isinstance(skills, list) and bool(skills), "skills must be a nonempty list")
    source_files = {}
    all_paths = set()
    file_count = 0
    for source in sources:
        _require(isinstance(source, dict), "source must be an object")
        source_id = source.get("id")
        _require(isinstance(source_id, str) and re.fullmatch(r"[a-z0-9-]+", source_id) is not None,
                 "invalid source id")
        _require(source_id not in source_files, f"duplicate source id: {source_id}")
        _require(isinstance(source.get("repository"), str) and
                 re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source["repository"]) is not None,
                 f"{source_id}: invalid repository")
        _require(isinstance(source.get("commit"), str) and
                 re.fullmatch(r"[0-9a-f]{40}", source["commit"]) is not None,
                 f"{source_id}: commit must be a pinned 40-character SHA")
        _require(source.get("license") == "MIT", f"{source_id}: expected MIT license")
        files = source.get("files")
        _require(isinstance(files, list) and bool(files), f"{source_id}: files must be nonempty")
        paths = set()
        original_paths = set()
        has_license = False
        for item in files:
            _require(isinstance(item, dict), f"{source_id}: file must be an object")
            relative = str(_relative(item.get("path"), f"{source_id} file"))
            original = str(_relative(item.get("source_path"), f"{source_id} source_path"))
            _require(relative not in all_paths, f"duplicate source file path: {relative}")
            _require(original not in original_paths, f"{source_id}: duplicate original path: {original}")
            digest = item.get("sha256")
            _require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                     f"{source_id}: invalid sha256 for {relative}")
            actual = _file(operator_root, relative, f"{source_id} upstream")
            _require(hashlib.sha256(actual.read_bytes()).hexdigest() == digest,
                     f"hash mismatch: {relative}")
            has_license |= PurePosixPath(original).name.upper() in ("LICENSE", "LICENSE.MD", "LICENSE.TXT")
            paths.add(relative)
            original_paths.add(original)
            all_paths.add(relative)
            file_count += 1
        _require(has_license, f"{source_id}: original LICENSE is missing from manifest")
        source_files[source_id] = paths
    names = set()
    routed = 0
    for skill in skills:
        _require(isinstance(skill, dict), "skill must be an object")
        name = skill.get("name")
        _require(isinstance(name, str) and len(name) < 64 and
                 re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is not None, "invalid skill name")
        _require(name not in names, f"duplicate skill name: {name}")
        names.add(name)
        expected_path = f"skills/{name}"
        _relative(skill.get("path"), f"{name} path")
        _require(skill["path"] == expected_path, f"{name}: path must be {expected_path}")
        skill_md = _file(skills_root, f"{name}/SKILL.md", f"{name} entrypoint")
        _frontmatter(skill_md, name)
        source_id = skill.get("source_id")
        entrypoint = skill.get("entrypoint")
        if source_id is not None or entrypoint is not None:
            _require(isinstance(source_id, str) and source_id in source_files,
                     f"{name}: unknown source_id {source_id!r}")
            entrypoint = str(_relative(entrypoint, f"{name} upstream entrypoint"))
            _require(entrypoint in source_files[source_id],
                     f"{name}: entrypoint is not in source manifest: {entrypoint}")
            _file(operator_root, entrypoint, f"{name} upstream entrypoint")
            routed += 1
    _require(OPERATOR in names, f"{OPERATOR} is missing from skills")
    return {"status": "ok", "version": version, "skills": len(names),
            "routed_skills": routed, "sources": len(source_files), "source_files": file_count,
            "layout": "installed" if installed else "checkout"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    layout = parser.add_mutually_exclusive_group()
    layout.add_argument("--root", type=Path, help="Full source checkout root")
    layout.add_argument("--installed-root", type=Path, help="Directory containing installed sibling skills")
    args = parser.parse_args(argv)
    try:
        result = validate(args.installed_root or args.root or Path(__file__).resolve().parents[1],
                          installed=args.installed_root is not None)
    except (BundleError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
