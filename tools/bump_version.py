#!/usr/bin/env python3
"""Keep the app version consistent across the project.

Usage:
    python tools/bump_version.py 3.0.0
    python tools/bump_version.py --bump-patch
    python tools/bump_version.py --check
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_PY = ROOT / "version.py"
VERSION_INFO = ROOT / "version_info.txt"
DOCS_JS = ROOT / "docs" / "script.js"
DOCS_HTML = ROOT / "docs" / "index.html"

APP_VERSION_RE = re.compile(r'(APP_VERSION\s*=\s*")([^"]+)(")')
FILEVERS_RE = re.compile(r"(filevers=)\((\d+(?:,\s*\d+)+)\)")
PRODVERS_RE = re.compile(r"(prodvers=)\((\d+(?:,\s*\d+)+)\)")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    match = APP_VERSION_RE.search(VERSION_PY.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"APP_VERSION not found in {VERSION_PY}")
    return match.group(2)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _version_tuple(version: str) -> tuple[str, ...]:
    parts = [int(part) for part in version.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(str(part) for part in parts)


def next_patch(version: str) -> str:
    if not SEMVER_RE.match(version):
        raise SystemExit(f"Invalid version '{version}', expected MAJOR.MINOR.PATCH")
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def bump(new_version: str) -> int:
    if not SEMVER_RE.match(new_version):
        raise SystemExit(f"Invalid version '{new_version}', expected MAJOR.MINOR.PATCH")

    old_version = read_version()
    if old_version == new_version:
        print(f"Version is already {new_version}")
        return 0

    py_text = VERSION_PY.read_text(encoding="utf-8")
    _write(VERSION_PY, APP_VERSION_RE.sub(rf'\g<1>{new_version}\g<3>', py_text, count=1))

    info_text = VERSION_INFO.read_text(encoding="utf-8")
    parts = ", ".join(_version_tuple(new_version))
    info_text = FILEVERS_RE.sub(rf"\g<1>({parts})", info_text)
    info_text = PRODVERS_RE.sub(rf"\g<1>({parts})", info_text)
    info_text = info_text.replace(old_version, new_version)
    _write(VERSION_INFO, info_text)

    js_text = DOCS_JS.read_text(encoding="utf-8")
    _write(DOCS_JS, js_text.replace(f"'{old_version}'", f"'{new_version}'"))

    html_text = DOCS_HTML.read_text(encoding="utf-8")
    _write(DOCS_HTML, html_text.replace(f">{old_version}<", f">{new_version}<"))

    for path in (VERSION_PY, VERSION_INFO, DOCS_JS, DOCS_HTML):
        print(f"updated {path.relative_to(ROOT)}")
    print(f"{old_version} -> {new_version}")
    return 0


def check() -> int:
    version = read_version()
    parts = ", ".join(_version_tuple(version))
    problems: list[str] = []

    info_text = VERSION_INFO.read_text(encoding="utf-8")
    if f"filevers=({parts})" not in info_text:
        problems.append(f"{VERSION_INFO.name}: filevers does not match {version}")
    if f"prodvers=({parts})" not in info_text:
        problems.append(f"{VERSION_INFO.name}: prodvers does not match {version}")
    if f"'{version}'" not in info_text:
        problems.append(f"{VERSION_INFO.name}: version strings do not match {version}")

    if f"var APP_VERSION = '{version}';" not in DOCS_JS.read_text(encoding="utf-8"):
        problems.append(f"{DOCS_JS.relative_to(ROOT)}: APP_VERSION does not match {version}")

    if f'id="app-version">{version}<' not in DOCS_HTML.read_text(encoding="utf-8"):
        problems.append(f"{DOCS_HTML.relative_to(ROOT)}: footer version does not match {version}")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1
    print(f"Version {version} is consistent everywhere")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    if argv[1] == "--check":
        return check()
    if argv[1] in ("--bump-patch", "-p"):
        return bump(next_patch(read_version()))
    return bump(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
