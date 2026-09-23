"""Domain exceptions raised outside the request cycle.

Errors that happen *during* a request are already covered by the handlers in
``app.main``. This module is for the ones that happen before there is a request
to fail — currently only configuration, which is checked once at import.
"""

from __future__ import annotations


class ConfigurationError(Exception):
    """The environment cannot support the environment it says it is.

    Deliberately not a ``ValueError``: pydantic would fold that into a
    ``ValidationError`` alongside field-shape complaints, and a deployment
    missing its Qdrant credentials deserves to say so in its own words rather
    than as one line of a validation table.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        body = "\n".join(f"  - {p}" for p in problems)
        super().__init__(f"Configuration is not valid for this environment:\n{body}")
