"""Pydantic v2 schema of the anatomy scan: raw per-file facts and the internal dependency graph.

See ``docs/features/anatomy-representation/spec.md``. Every field is a measured
count or flag; nothing here is a score.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PhpFacts(BaseModel):
    """Raw PHP facts, counted as measured and never combined."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    language: Literal["php"]
    namespace: bool
    strict_types: bool
    superglobals: int = Field(ge=0)
    globals: int = Field(ge=0, description="Count of `global $` statements")
    deprecated_calls: int = Field(ge=0, description="Calls to functions removed from PHP")
    includes: int = Field(ge=0, description="Count of require/include forms")


class ScriptFacts(BaseModel):
    """Raw TypeScript or JavaScript facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    language: Literal["typescript", "javascript"]
    typed: bool = Field(description=".ts/.tsx and the root tsconfig.json has compilerOptions.strict true")
    loose_marks: int = Field(ge=0, description="Count of `: any`, `as any`, `@ts-ignore`, `@ts-nocheck`")


class PythonFacts(BaseModel):
    """Raw Python facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    language: Literal["python"]
    functions: int = Field(ge=0, description="Count of `def`")
    annotated_functions: int = Field(ge=0, description="Count of `def` with a `->` return annotation")

    @model_validator(mode="after")
    def annotated_within_total(self) -> "PythonFacts":
        if self.annotated_functions > self.functions:
            raise ValueError("annotated_functions cannot exceed functions")
        return self


LanguageFacts = Annotated[PhpFacts | ScriptFacts | PythonFacts, Field(discriminator="language")]


class AnatomyFile(BaseModel):
    """One scanned file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(description="Repository-relative POSIX path at HEAD")
    lines: int = Field(ge=1, description="Newline count plus one")
    test: bool
    foreign: bool
    changes: int = Field(ge=0, description="Commits reachable from HEAD that touch the path")
    line_years: dict[int, int] = Field(description="Blamed lines per author year (UTC), ascending years")
    unblamed: bool = Field(description="Binary (NUL byte in the first 8000 bytes): not blamed, line_years is empty")
    facts: LanguageFacts

    @model_validator(mode="after")
    def unblamed_has_no_years(self) -> "AnatomyFile":
        if self.unblamed and self.line_years:
            raise ValueError("an unblamed file has no line_years")
        return self


class AnatomyEdge(BaseModel):
    """An undirected internal dependency; weight is the number of references in both directions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str
    weight: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered_endpoints(self) -> "AnatomyEdge":
        if not self.source < self.target:
            raise ValueError("source must sort before target; self edges are not allowed")
        return self


class AnatomyScan(BaseModel):
    """Raw structure of one repository at HEAD, the input of the anatomy layout."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    files: list[AnatomyFile] = Field(description="Scanned files sorted by path")
    edges: list[AnatomyEdge] = Field(description="Internal edges sorted by (source, target)")
    unresolved_references: int = Field(ge=0, description="References dropped as external or dynamic")
    unblamed: int = Field(ge=0, description="Count of files with unblamed set")

    @model_validator(mode="after")
    def consistent(self) -> "AnatomyScan":
        paths = [f.path for f in self.files]
        if paths != sorted(set(paths)):
            raise ValueError("files must be unique and sorted by path")
        known = set(paths)
        keys = [(e.source, e.target) for e in self.edges]
        if keys != sorted(set(keys)):
            raise ValueError("edges must be unique and sorted by (source, target)")
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ValueError(f"edge {edge.source} - {edge.target} names a file that was not scanned")
        if self.unblamed != sum(1 for f in self.files if f.unblamed):
            raise ValueError("unblamed must equal the number of unblamed files")
        return self
