"""Port for generating grant application drafts.

A draft is a dict of section name -> prose, in the grant's language. In
test/memory mode a deterministic template generator is used; in production
a Claude-backed adapter writes funder-tuned prose and falls back to the
template on any failure (so /generate never 500s and never blocks the board).
"""
from __future__ import annotations

from typing import Protocol

from app.ports.grant_tracker import GrantApplication


class GrantDraftGeneratorPort(Protocol):
    def generate(
        self,
        grant: dict,
        application: GrantApplication | None,
        kpi_data: dict | None,
        lang: str,
    ) -> dict: ...
