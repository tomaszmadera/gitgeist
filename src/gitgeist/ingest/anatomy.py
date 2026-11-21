"""Anatomy scan: raw per-file facts and the internal dependency graph of a Git repository at HEAD.

The contract is ``docs/features/anatomy-representation/spec.md`` ("Which files
are scanned", "Per-file raw facts", "Dependency graph", "Errors"). Every Git
failure raises :class:`AnatomyScanError`; no file or reference is skipped
without being counted.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path

from gitgeist.schemas.anatomy import (
    AnatomyEdge,
    AnatomyFile,
    AnatomyScan,
    PhpFacts,
    PythonFacts,
    ScriptFacts,
)

GIT_TIMEOUT_SECONDS = 120
BLAME_WORKERS = 8

LANGUAGE_BY_EXTENSION = {
    ".php": "php",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
}
EXCLUDED_SEGMENTS = {"vendor", "node_modules"}
TEST_SEGMENTS = {"test", "tests", "spec", "__tests__"}
TEST_NAME_PATTERNS = ("*Test.php", "*.test.*", "*.spec.*", "test_*.py", "*_test.py")
THIRD_PARTY_SEGMENTS = {"third_party", "third-party"}
FOREIGN_MARKER_NAMES = {"composer.json", "package.json"}
# Matched case-insensitively against names that are not scanned source files.
FOREIGN_MARKER_PATTERNS = ("license*", "copying*")
# Git treats a blob with a NUL byte in its first 8000 bytes as binary.
BINARY_PROBE_BYTES = 8000


class AnatomyScanError(RuntimeError):
    """The anatomy scan cannot complete; the message names the cause."""


# --- Git -----------------------------------------------------------------


def _git_env() -> dict[str, str]:
    """The caller's environment without system and user Git config, so a scan depends only on the repository."""
    return {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}


def _git(repo: Path, args: list[str], *, subject: str, stdin: bytes | None = None) -> bytes:
    """Run one git command and return stdout, raising with ``subject`` and the Git error on failure."""
    command = ["git", *args]
    try:
        result = subprocess.run(
            command,
            cwd=repo,
            input=stdin,
            env=_git_env(),
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AnatomyScanError("git is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise AnatomyScanError(
            f"git {args[0]} for {subject} ran longer than {GIT_TIMEOUT_SECONDS} s"
        ) from exc
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise AnatomyScanError(f"git {args[0]} for {subject} failed: {error}")
    return result.stdout


def _probe(repo: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run one git command whose non-zero exit the caller interprets; missing git and timeouts raise."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            env=_git_env(),
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AnatomyScanError("git is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise AnatomyScanError(f"git {args[0]} for {repo} ran longer than {GIT_TIMEOUT_SECONDS} s") from exc


def _check_repository(repo: Path) -> None:
    if not repo.is_dir():
        raise AnatomyScanError(f"{repo} is not a directory")
    top = _probe(repo, ["rev-parse", "--show-toplevel"])
    toplevel = os.fsdecode(top.stdout.strip())
    if top.returncode != 0 or not toplevel or Path(toplevel).resolve() != repo.resolve():
        raise AnatomyScanError(f"{repo} is not a Git repository root")
    head = _probe(repo, ["rev-parse", "--verify", "--quiet", "HEAD"])
    if head.returncode != 0:
        raise AnatomyScanError(f"{repo} has no commits")


@dataclass(frozen=True)
class _TreeEntry:
    path: str
    oid: str


def _head_blobs(repo: Path) -> list[_TreeEntry]:
    """Regular files and executables at HEAD; symlinks and submodules carry no source text."""
    raw = _git(repo, ["ls-tree", "-r", "-z", "--full-tree", "HEAD"], subject="HEAD")
    entries: list[_TreeEntry] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        mode, kind, oid = meta.split(b" ")
        if kind == b"blob" and mode in (b"100644", b"100755"):
            entries.append(_TreeEntry(os.fsdecode(path), oid.decode("ascii")))
    return entries


def _read_blobs(repo: Path, entries: list[_TreeEntry]) -> dict[str, bytes]:
    if not entries:
        return {}
    payload = "".join(f"{entry.oid}\n" for entry in entries).encode("ascii")
    raw = _git(repo, ["cat-file", "--batch"], subject="HEAD blobs", stdin=payload)
    contents: dict[str, bytes] = {}
    offset = 0
    for entry in entries:
        header_end = raw.index(b"\n", offset)
        header = raw[offset:header_end].split(b" ")
        if len(header) != 3 or header[1] != b"blob":
            raise AnatomyScanError(f"git cat-file for {entry.path} returned {raw[offset:header_end]!r}")
        size = int(header[2])
        start = header_end + 1
        contents[entry.path] = raw[start : start + size]
        offset = start + size + 1
    return contents


def _vendored_by_attributes(repo: Path, paths: list[str]) -> set[str]:
    """Paths that ``.gitattributes`` at HEAD marks ``linguist-vendored``."""
    if not paths:
        return set()
    stdin = b"".join(os.fsencode(path) + b"\0" for path in paths)
    raw = _git(
        repo,
        ["check-attr", "--source=HEAD", "-z", "--stdin", "linguist-vendored"],
        subject=".gitattributes",
        stdin=stdin,
    )
    fields = raw.split(b"\0")
    vendored: set[str] = set()
    for index in range(0, len(fields) - 2, 3):
        if fields[index + 2] in (b"set", b"true"):
            vendored.add(os.fsdecode(fields[index]))
    return vendored


def _change_counts(repo: Path) -> Counter[str]:
    raw = _git(
        repo,
        ["log", "--format=", "--name-only", "--no-renames", "-z", "HEAD"],
        subject="HEAD history",
    )
    return Counter(os.fsdecode(name.strip(b"\n")) for name in raw.split(b"\0") if name.strip(b"\n"))


def _blame_years(repo: Path, path: str) -> dict[int, int]:
    raw = _git(repo, ["blame", "--line-porcelain", "-w", "HEAD", "--", path], subject=path)
    years: Counter[int] = Counter()
    for line in raw.split(b"\n"):
        if line.startswith(b"author-time "):
            years[datetime.fromtimestamp(int(line[12:]), timezone.utc).year] += 1
    return dict(sorted(years.items()))


# --- File classification --------------------------------------------------


def _is_test(path: str) -> bool:
    *dirs, name = path.split("/")
    return any(d in TEST_SEGMENTS for d in dirs) or any(fnmatchcase(name, p) for p in TEST_NAME_PATTERNS)


def _foreign_roots(all_paths: list[str]) -> set[str]:
    """Directories below the root that hold their own licence or package manifest.

    ``LICENSE*`` and ``COPYING*`` match case-insensitively (``License.txt`` counts) but never a
    scanned source file, so ``app/license_check.php`` does not make ``app/`` foreign.
    """
    roots: set[str] = set()
    for path in all_paths:
        directory, _, name = path.rpartition("/")
        if not directory:
            continue
        licence = posixpath.splitext(name)[1].lower() not in LANGUAGE_BY_EXTENSION and any(
            fnmatchcase(name.lower(), pattern) for pattern in FOREIGN_MARKER_PATTERNS
        )
        if name in FOREIGN_MARKER_NAMES or licence:
            roots.add(directory)
    return roots


def _is_foreign(path: str, foreign_roots: set[str], vendored: set[str]) -> bool:
    *dirs, name = path.split("/")
    if fnmatchcase(name, "*.min.*") or any(d in THIRD_PARTY_SEGMENTS for d in dirs) or path in vendored:
        return True
    return any("/".join(dirs[:depth]) in foreign_roots for depth in range(1, len(dirs) + 1))


# --- Text ------------------------------------------------------------------


def _decode(content: bytes) -> str:
    """Return the text. Non-UTF-8 text is read byte for byte as Latin-1."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# --- PHP -----------------------------------------------------------------

_PHP_NAME = r"\\?[A-Za-z_][A-Za-z0-9_]*(?:\\[A-Za-z_][A-Za-z0-9_]*)*"
_PHP_NAMESPACE = re.compile(r"^[ \t]*namespace[ \t]+(" + _PHP_NAME + r")[ \t]*[;{]", re.MULTILINE)
_PHP_STRICT = re.compile(r"declare\s*\(\s*strict_types\s*=\s*1\s*\)")
_PHP_SUPERGLOBAL = re.compile(r"\$_(?:GET|POST|REQUEST|COOKIE|SESSION|SERVER|FILES)\b")
_PHP_GLOBAL = re.compile(r"(?<![\w$])global\s+\$")
_PHP_DEPRECATED = re.compile(
    r"(?<![\w$])(?<!->)(?<!::)(?<!function )(?:mysql_\w+|ereg\w*|split|each|create_function)\s*\("
)
# Statement or expression position: start of code, after a statement end, a block, an operator or return/else.
_PHP_INCLUDE = re.compile(
    r"(?:\A|(?<=[;{}()=,?:!&|.])|(?<=[^\w$]return)|(?<=[^\w$]else))\s*"
    r"(?<![\w$>:])(?:require|include)(?:_once)?(?![\w])"
)
_PHP_INCLUDE_LITERAL = re.compile(
    r"\s*\(?\s*(?:(?:__DIR__|dirname\s*\(\s*__FILE__\s*\))\s*\.\s*)?(['\"])([^'\"\n]+\.php)\1"
)
_PHP_CLASS_DECL = re.compile(
    r"^[ \t]*(?:(?:abstract|final|readonly)[ \t]+)*(?:class|interface|trait|enum)[ \t]+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
_PHP_USE = re.compile(r"^[ \t]*use[ \t]+(?:(function|const)[ \t]+)?([^;]+);", re.MULTILINE)
_PHP_NAME_REFS = re.compile(
    r"(?<![\w$\\])(?:new|instanceof)\s+(" + _PHP_NAME + r")"
    r"|(?<![\w$\\>])(" + _PHP_NAME + r")\s*::"
)
_PHP_HERITAGE = re.compile(
    r"(?<![\w$])(?:extends|implements)\s+(" + _PHP_NAME + r"(?:\s*,\s*" + _PHP_NAME + r")*)"
)
_PHP_SPECIAL = {"self", "static", "parent", "class"}
# <?php, <?= and the short open tag <?; an XML declaration or processing instruction (<?xml) is inline HTML.
_PHP_OPEN_TAG = re.compile(r"<\?(?:php(?![\w])|=|(?!xml))", re.IGNORECASE)
_PHP_HEREDOC = re.compile(r"<<<[ \t]*(['\"]?)([A-Za-z_]\w*)\1\r?\n")


def _php_code(text: str) -> str:
    """``text`` with inline HTML, open and close tags, comments and string contents blanked.

    Every blanked character becomes a space and newlines stay, so offsets and line numbers match
    ``text``. String delimiters stay. Superglobals inside double-quoted and heredoc strings stay,
    because PHP interpolates them (an escaped ``\\$_GET`` still counts). A close tag becomes ``;``
    because it ends a statement. ``#[`` starts an attribute, not a comment.
    """
    out = [" " if char != "\n" else "\n" for char in text]
    n = len(text)

    def keep(start: int, end: int) -> None:
        out[start:end] = text[start:end]

    def keep_superglobals(start: int, end: int) -> None:
        for found in _PHP_SUPERGLOBAL.finditer(text, start, end):
            keep(found.start(), found.end())

    i = 0
    while i < n:
        # Inline HTML up to the next open tag.
        tag = _PHP_OPEN_TAG.search(text, i)
        if tag is None:
            break
        i = tag.end()
        while i < n:
            char = text[i]
            if text.startswith("?>", i):
                out[i] = ";"
                i += 2
                break
            if char in "'\"`":
                end = i + 1
                while end < n and text[end] != char:
                    end += 2 if text[end] == "\\" else 1
                if end >= n:
                    # An unterminated string runs to the end of the file.
                    i = n
                    break
                out[i] = out[end] = char
                if char != "'":
                    keep_superglobals(i + 1, end)
                i = end + 1
            elif text.startswith("//", i) or (char == "#" and not text.startswith("#[", i)):
                while i < n and text[i] != "\n" and not text.startswith("?>", i):
                    i += 1
            elif text.startswith("/*", i):
                close = text.find("*/", i + 2)
                i = n if close < 0 else close + 2
            elif (heredoc := _PHP_HEREDOC.match(text, i)) is not None:
                closing = re.compile(r"^[ \t]*" + heredoc.group(2) + r"\b", re.MULTILINE).search(text, heredoc.end())
                end = n if closing is None else closing.end()
                if heredoc.group(1) != "'":
                    keep_superglobals(heredoc.end(), end)
                i = end
            else:
                out[i] = char
                i += 1
    return "".join(out)


@dataclass(frozen=True)
class _PhpSource:
    namespace: str
    classes: list[str]  # fully qualified names defined in the file


def _php_source(text: str) -> _PhpSource:
    match = _PHP_NAMESPACE.search(text)
    namespace = match.group(1).lstrip("\\") if match else ""
    prefix = f"{namespace}\\" if namespace else ""
    return _PhpSource(namespace, [prefix + m.group(1) for m in _PHP_CLASS_DECL.finditer(text)])


def _php_facts(text: str) -> PhpFacts:
    return PhpFacts(
        language="php",
        namespace=_PHP_NAMESPACE.search(text) is not None,
        strict_types=_PHP_STRICT.search(text) is not None,
        superglobals=len(_PHP_SUPERGLOBAL.findall(text)),
        globals=len(_PHP_GLOBAL.findall(text)),
        deprecated_calls=len(_PHP_DEPRECATED.findall(text)),
        includes=len(_PHP_INCLUDE.findall(text)),
    )


class _PhpIndex:
    def __init__(self, sources: dict[str, _PhpSource], php_paths: list[str]) -> None:
        self.by_fqcn: dict[str, list[str]] = {}
        self.by_short: dict[str, list[str]] = {}
        for path in sorted(sources):
            for fqcn in sources[path].classes:
                self.by_fqcn.setdefault(fqcn.lower(), []).append(path)
                self.by_short.setdefault(fqcn.rsplit("\\", 1)[-1].lower(), []).append(path)
        self.php_paths = php_paths

    def class_file(self, fqcn: str) -> str | None:
        found = self.by_fqcn.get(fqcn.lower(), [])
        return found[0] if len(found) == 1 else None

    def short_file(self, short: str) -> str | None:
        found = self.by_short.get(short.lower(), [])
        return found[0] if len(found) == 1 else None

    def include_file(self, literal: str) -> str | None:
        """The scanned PHP file sharing the longest path suffix with ``literal``; None when absent or tied."""
        wanted = [part for part in literal.split("/") if part not in ("", ".", "..")]
        best_length = 0
        best: list[str] = []
        for path in self.php_paths:
            parts = path.split("/")
            length = 0
            while length < min(len(parts), len(wanted)) and parts[-1 - length] == wanted[-1 - length]:
                length += 1
            if length == 0:
                continue
            if length > best_length:
                best_length, best = length, [path]
            elif length == best_length:
                best.append(path)
        return best[0] if len(best) == 1 else None


def _php_imports(text: str, end: int) -> tuple[dict[str, str], list[str]]:
    """Class imports before ``end`` as alias -> FQCN, plus the imported names that are functions or constants."""
    aliases: dict[str, str] = {}
    other: list[str] = []
    for match in _PHP_USE.finditer(text, 0, end):
        kind, body = match.group(1), match.group(2)
        if "{" in body:
            head, _, rest = body.partition("{")
            items = [head.strip().rstrip("\\") + "\\" + item.strip() for item in rest.rstrip("} \t\n").split(",")]
        else:
            items = [item.strip() for item in body.split(",")]
        for item in items:
            if not item or item.endswith("\\"):
                continue
            parts = re.split(r"\s+as\s+", item, maxsplit=1)
            name = parts[0].strip().lstrip("\\")
            alias = parts[1].strip() if len(parts) == 2 else name.rsplit("\\", 1)[-1]
            if kind:
                other.append(name)
            else:
                aliases[alias.lower()] = name
    return aliases, other


def _php_references(text: str, code: str, index: _PhpIndex) -> tuple[list[str], int]:
    """References in ``code`` (see :func:`_php_code`); include literals are read from ``text`` at the same offset."""
    source = _php_source(code)
    first_class = _PHP_CLASS_DECL.search(code)
    body_start = first_class.start() if first_class else len(code)
    aliases, function_imports = _php_imports(code, body_start)
    targets: list[str] = []
    unresolved = len(function_imports)

    for fqcn in aliases.values():
        target = index.class_file(fqcn)
        if target is None:
            unresolved += 1
        else:
            targets.append(target)

    def resolve(name: str) -> str | None:
        if name.startswith("\\"):
            # Fully qualified: no short-name fallback.
            return index.class_file(name[1:])
        else:
            head, sep, rest = name.partition("\\")
            if head.lower() in aliases:
                fqcn = aliases[head.lower()] + sep + rest
            else:
                fqcn = f"{source.namespace}\\{name}" if source.namespace else name
        return index.class_file(fqcn) or index.short_file(fqcn.rsplit("\\", 1)[-1])

    names: list[str] = []
    for match in _PHP_NAME_REFS.finditer(code):
        names.append(match.group(1) or match.group(2))
    for match in _PHP_HERITAGE.finditer(code):
        names.extend(name.strip() for name in match.group(1).split(","))
    # Trait uses inside a class body are class references too.
    for match in _PHP_USE.finditer(code, body_start):
        if match.group(1) is None:
            names.extend(name.strip() for name in match.group(2).split("{")[0].split(","))
    for name in names:
        if name.lower() in _PHP_SPECIAL:
            continue
        target = resolve(name)
        if target is None:
            unresolved += 1
        else:
            targets.append(target)

    for match in _PHP_INCLUDE.finditer(code):
        literal = _PHP_INCLUDE_LITERAL.match(text, match.end())
        target = index.include_file(literal.group(2)) if literal else None
        if target is None:
            unresolved += 1
        else:
            targets.append(target)
    return targets, unresolved


# --- TypeScript / JavaScript --------------------------------------------------

_TS_LOOSE = re.compile(r":\s*any\b|\bas\s+any\b|@ts-ignore|@ts-nocheck")
_JS_SPECIFIERS = re.compile(
    r"(?<![\w$.])(?:import|export)\s+(?:type\s+)?[\w$*{}\s,]*?\bfrom\s*(['\"])([^'\"\n]+)\1"
    r"|(?<![\w$.])import\s*(['\"])([^'\"\n]+)\3"
    r"|(?<![\w$.])(?:import|require)\s*\(\s*(['\"])([^'\"\n]+)\5\s*\)"
    # Any other import(...) or require(...) argument, template literals included, is a dynamic path.
    r"|(?<![\w$.])(?:import|require)\s*\("
)
# A slash after one of these characters, or at the start of the file, starts a regex literal; elsewhere it
# divides. Keywords that precede an expression (return, typeof and similar) also start a regex literal.
_JS_REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")
_JS_REGEX_KEYWORD = re.compile(
    r"(?<![\w$])(?:return|typeof|instanceof|in|of|new|delete|void|throw|case|do|else|yield|await)\Z"
)
_JS_SUFFIXES = ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js")


def _strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments outside strings, then trailing commas."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        char = text[i]
        if char == '"':
            end = i + 1
            while end < n and text[end] != '"':
                end += 2 if text[end] == "\\" else 1
            out.append(text[i : end + 1])
            i = end + 1
        elif text.startswith("//", i):
            newline = text.find("\n", i)
            i = n if newline < 0 else newline
        elif text.startswith("/*", i):
            close = text.find("*/", i + 2)
            i = n if close < 0 else close + 2
        else:
            out.append(char)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def _js_code(text: str) -> str:
    """``text`` with comments, string, template and regex literal contents blanked.

    Every blanked character becomes a space and newlines stay, so offsets match ``text``. Delimiters
    stay, so a specifier literal is read from ``text`` at the offsets of its blanked contents. Template
    ``${...}`` expressions stay as code, nested templates included. A slash starts a regex literal by
    the previous significant character or keyword (``_JS_REGEX_AFTER``, ``_JS_REGEX_KEYWORD``); this
    heuristic misreads only rare cases such as a regex after ``)`` in ``if (x) /re/.test(y)``.
    """
    out = [" " if char != "\n" else "\n" for char in text]
    n = len(text)
    # One entry per open template expression: the brace depth inside that ``${...}``.
    templates: list[int] = []
    i = 0
    last = ""  # previous significant code character, "" at the start

    def scan_template(start: int) -> int:
        """Blank template text from ``start`` up to the closing backtick or a ``${``; return the next index."""
        j = start
        while j < n:
            if text[j] == "\\":
                j += 2
            elif text[j] == "`":
                out[j] = "`"
                return j + 1
            elif text.startswith("${", j):
                out[j : j + 2] = "${"
                templates.append(0)
                return j + 2
            else:
                j += 1
        return n

    while i < n:
        char = text[i]
        if char in " \t\r\n":
            i += 1
            continue
        if text.startswith("//", i):
            newline = text.find("\n", i)
            i = n if newline < 0 else newline
            continue
        if text.startswith("/*", i):
            close = text.find("*/", i + 2)
            i = n if close < 0 else close + 2
            continue
        if char in "'\"":
            end = i + 1
            while end < n and text[end] != char and text[end] != "\n":
                end += 2 if text[end] == "\\" else 1
            out[i] = char
            if end < n and text[end] == char:
                out[end] = char
            i = end + 1
            last = char
            continue
        if char == "`":
            out[i] = "`"
            i = scan_template(i + 1)
            last = "`"
            continue
        if char == "/" and (
            last in _JS_REGEX_AFTER or last == "" or _JS_REGEX_KEYWORD.search("".join(out[max(0, i - 12) : i]).rstrip())
        ):
            end, in_class = i + 1, False
            while end < n and text[end] != "\n":
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == "[":
                    in_class = True
                elif text[end] == "]":
                    in_class = False
                elif text[end] == "/" and not in_class:
                    break
                end += 1
            out[i] = "/"
            if end < n and text[end] == "/":
                out[end] = "/"
            i = end + 1
            last = "x"  # a regex literal is an operand, so a following slash divides
            continue
        if templates:
            if char == "{":
                templates[-1] += 1
            elif char == "}":
                if templates[-1] == 0:
                    templates.pop()
                    out[i] = "}"
                    i = scan_template(i + 1)
                    last = "`"
                    continue
                templates[-1] -= 1
        out[i] = char
        last = char
        i += 1
    return "".join(out)


@dataclass(frozen=True)
class _TsConfig:
    strict: bool
    base: str  # repository-relative directory that paths targets are relative to, "" for the root
    paths: dict[str, list[str]]


def _ts_config(content: bytes | None) -> _TsConfig:
    if content is None:
        return _TsConfig(strict=False, base="", paths={})
    try:
        data = json.loads(_strip_jsonc(content.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnatomyScanError(f"tsconfig.json cannot be parsed: {exc}") from exc
    options = data.get("compilerOptions") or {}
    base = posixpath.normpath(options.get("baseUrl", "."))
    return _TsConfig(
        strict=options.get("strict") is True,
        base="" if base == "." else base,
        paths={str(k): [str(t) for t in v] for k, v in (options.get("paths") or {}).items()},
    )


def _script_facts(path: str, text: str, config: _TsConfig) -> ScriptFacts:
    language = LANGUAGE_BY_EXTENSION[posixpath.splitext(path)[1].lower()]
    return ScriptFacts(
        language=language,
        typed=language == "typescript" and config.strict,
        loose_marks=len(_TS_LOOSE.findall(text)),
    )


def _resolve_script(stem: str, scanned: set[str]) -> str | None:
    stem = posixpath.normpath(stem)
    if stem.startswith("../") or stem == "..":
        return None
    for suffix in _JS_SUFFIXES:
        if stem + suffix in scanned:
            return stem + suffix
    return None


def _alias_stems(specifier: str, config: _TsConfig) -> list[str] | None:
    for pattern, targets in config.paths.items():
        if "*" in pattern:
            head, _, tail = pattern.partition("*")
            if specifier.startswith(head) and specifier.endswith(tail) and len(specifier) >= len(head + tail):
                star = specifier[len(head) : len(specifier) - len(tail)]
                return [posixpath.join(config.base, t.replace("*", star, 1)) for t in targets]
        elif specifier == pattern:
            return [posixpath.join(config.base, t) for t in targets]
    return None


def _script_references(path: str, text: str, config: _TsConfig, scanned: set[str]) -> tuple[list[str], int]:
    targets: list[str] = []
    unresolved = 0
    directory = posixpath.dirname(path)
    # Match on the code view so comments and strings are not references; read specifiers from ``text``.
    for match in _JS_SPECIFIERS.finditer(_js_code(text)):
        group = next((g for g in (2, 4, 6) if match.group(g) is not None), None)
        specifier = text[match.start(group) : match.end(group)] if group else None
        if specifier is None:
            unresolved += 1
            continue
        if specifier.startswith(("./", "../")) or specifier in (".", ".."):
            stems = [posixpath.join(directory, specifier)]
        else:
            stems = _alias_stems(specifier, config) or []
        target = next((t for t in (_resolve_script(s, scanned) for s in stems) if t), None)
        if target is None:
            unresolved += 1
        else:
            targets.append(target)
    return targets, unresolved


# --- Python -------------------------------------------------------------------

_PY_DEF = re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+\w+[ \t]*\(", re.MULTILINE)
_PY_RETURNS = re.compile(r"\s*->")
_PY_IMPORT = re.compile(r"^[ \t]*import[ \t]+([\w. \t,]+)", re.MULTILINE)
_PY_FROM = re.compile(
    r"^[ \t]*from[ \t]+(\.*[\w.]*)[ \t]+import[ \t]+(\([^)]*\)|[^\n#;]*(?:\\\n[^\n#;]*)*)", re.MULTILINE
)
_PY_ROOTS = ("", "src")


def _python_facts(text: str) -> PythonFacts:
    functions = annotated = 0
    for match in _PY_DEF.finditer(text):
        functions += 1
        depth, i = 1, match.end()
        while i < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        if _PY_RETURNS.match(text, i):
            annotated += 1
    return PythonFacts(language="python", functions=functions, annotated_functions=annotated)


def _python_module(base: str, dotted: str, scanned: set[str]) -> str | None:
    stem = posixpath.join(base, *dotted.split(".")) if dotted else base
    for candidate in (f"{stem}.py", posixpath.join(stem, "__init__.py")):
        if candidate in scanned:
            return candidate
    return None


def _python_bases(path: str, dots: int) -> tuple[str, ...]:
    if dots == 0:
        return _PY_ROOTS
    package = posixpath.dirname(path)
    for _ in range(dots - 1):
        package = posixpath.dirname(package)
    return (package,)


def _python_references(path: str, text: str, scanned: set[str]) -> tuple[list[str], int]:
    targets: list[str] = []
    unresolved = 0

    def find(bases: tuple[str, ...], dotted: str) -> str | None:
        return next((t for t in (_python_module(b, dotted, scanned) for b in bases) if t), None)

    for match in _PY_IMPORT.finditer(text):
        for item in match.group(1).split(","):
            module = item.strip().split()[0] if item.strip() else ""
            if not module:
                continue
            target = find(_PY_ROOTS, module)
            if target is None:
                unresolved += 1
            else:
                targets.append(target)

    for match in _PY_FROM.finditer(text):
        spec = match.group(1)
        module = spec.lstrip(".")
        bases = _python_bases(path, len(spec) - len(module))
        imported = match.group(2).replace("\\\n", " ").strip("()\\ \t\n")
        names = [name.strip().split()[0] for name in imported.split(",") if name.strip()]
        rest = False
        for name in names:
            submodule = None if name == "*" else find(bases, f"{module}.{name}" if module else name)
            if submodule is None:
                rest = True
            else:
                targets.append(submodule)
        if rest or not names:
            target = find(bases, module)
            if target is None:
                unresolved += 1
            else:
                targets.append(target)
    return targets, unresolved


# --- Scan -----------------------------------------------------------------


def scan_anatomy(repo_path: Path) -> AnatomyScan:
    """Scan ``repo_path`` at HEAD and return per-file raw facts and the internal dependency graph."""
    repo = Path(repo_path)
    _check_repository(repo)
    entries = _head_blobs(repo)
    all_paths = [entry.path for entry in entries]
    candidates = [
        entry
        for entry in entries
        if posixpath.splitext(entry.path)[1].lower() in LANGUAGE_BY_EXTENSION
        and not any(segment in EXCLUDED_SEGMENTS for segment in entry.path.split("/")[:-1])
    ]
    for entry in candidates:
        try:
            entry.path.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise AnatomyScanError(f"path is not valid UTF-8: {os.fsencode(entry.path)!r}") from exc
    tsconfig_entry = [entry for entry in entries if entry.path == "tsconfig.json"]
    blobs = _read_blobs(repo, candidates + tsconfig_entry)
    config = _ts_config(blobs.get("tsconfig.json") if tsconfig_entry else None)

    paths = sorted(entry.path for entry in candidates)
    scanned = set(paths)
    foreign_roots = _foreign_roots(all_paths)
    vendored = _vendored_by_attributes(repo, paths)
    changes = _change_counts(repo)

    texts: dict[str, str] = {}
    unblamed: set[str] = set()
    for path in paths:
        content = blobs[path]
        if b"\0" in content[:BINARY_PROBE_BYTES]:
            unblamed.add(path)
        else:
            texts[path] = _decode(content)

    blamed = [path for path in paths if path not in unblamed]
    with ThreadPoolExecutor(max_workers=BLAME_WORKERS) as pool:
        years = dict(zip(blamed, pool.map(lambda p: _blame_years(repo, p), blamed)))

    php_paths = [p for p in paths if LANGUAGE_BY_EXTENSION[posixpath.splitext(p)[1].lower()] == "php"]
    php_code = {p: _php_code(texts[p]) for p in php_paths if p in texts}
    php_index = _PhpIndex({p: _php_source(code) for p, code in php_code.items()}, php_paths)

    files: list[AnatomyFile] = []
    weights: Counter[tuple[str, str]] = Counter()
    unresolved_total = 0
    for path in paths:
        language = LANGUAGE_BY_EXTENSION[posixpath.splitext(path)[1].lower()]
        text = texts.get(path)
        if language == "php":
            code = php_code.get(path, "")
            facts = _php_facts(code)
            targets, unresolved = _php_references(text, code, php_index) if text is not None else ([], 0)
        elif language == "python":
            facts = _python_facts(text or "")
            targets, unresolved = _python_references(path, text, scanned) if text is not None else ([], 0)
        else:
            facts = _script_facts(path, text or "", config)
            targets, unresolved = _script_references(path, text, config, scanned) if text is not None else ([], 0)
        unresolved_total += unresolved
        for target in targets:
            if target != path:
                weights[(min(path, target), max(path, target))] += 1
        files.append(
            AnatomyFile(
                path=path,
                lines=blobs[path].count(b"\n") + 1,
                test=_is_test(path),
                foreign=_is_foreign(path, foreign_roots, vendored),
                changes=changes.get(path, 0),
                line_years=years.get(path, {}),
                unblamed=path in unblamed,
                facts=facts,
            )
        )

    return AnatomyScan(
        files=files,
        edges=[AnatomyEdge(source=s, target=t, weight=w) for (s, t), w in sorted(weights.items())],
        unresolved_references=unresolved_total,
        unblamed=len(unblamed),
    )
