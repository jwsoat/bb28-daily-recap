"""Shared data types for the BB28 daily recap pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RawPost:
    source: str
    text: str
    published_at: datetime


@dataclass(frozen=True)
class SourceResult:
    source: str
    posts: list[RawPost]
    found_any: bool


@dataclass(frozen=True)
class Fact:
    fact_type: str  # "status" | "have_not"
    housemate: str = ""
    status: str = ""  # only set when fact_type == "status" (includes "Jury")
    value: bool | None = None  # only set when fact_type == "have_not"
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HAServiceCall:
    domain: str
    service: str
    data: dict


@dataclass(frozen=True)
class PushResult:
    call: HAServiceCall
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class EmailContent:
    subject: str
    body: str
