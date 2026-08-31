"""The rule that keeps the two services independent.

Django must never import ai_service. The dependency runs one way — Django puts
a message on Redis and a worker in the other image picks it up — and the moment
an import crosses that line, deploying the two separately stops working and
Django acquires a two-gigabyte ML dependency to enqueue a job.

An architecture rule that is only written down is a rule that erodes, so it is
checked here instead.
"""

from __future__ import annotations

import ast
import pathlib

from django.test import SimpleTestCase

BACKEND = pathlib.Path(__file__).resolve().parents[3]
FORBIDDEN_ROOTS = {"ai_service", "app"}


def _python_files():
    for path in (BACKEND / "apps").rglob("*.py"):
        if "migrations" in path.parts or "__pycache__" in path.parts:
            continue
        yield path
    for name in ("settings.py", "urls.py", "asgi.py", "wsgi.py"):
        candidate = BACKEND / "zion" / name
        if candidate.exists():
            yield candidate


def _imported_roots(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


class ServiceBoundaryTests(SimpleTestCase):
    def test_django_never_imports_the_ai_service(self):
        offenders = []
        for path in _python_files():
            crossing = _imported_roots(path) & FORBIDDEN_ROOTS
            if crossing:
                offenders.append(f"{path.relative_to(BACKEND)} imports {', '.join(crossing)}")

        self.assertEqual(
            offenders,
            [],
            "Django imported ai_service. The two services communicate through "
            "Redis, and the only thing they share is the task name and payload "
            "shape in apps/knowledge/dispatch.py:\n  " + "\n  ".join(offenders),
        )

    def test_the_task_names_are_declared_in_exactly_one_place(self):
        from apps.knowledge import dispatch

        names = {dispatch.TASK_INGEST, dispatch.TASK_REINDEX, dispatch.TASK_DELETE}
        self.assertEqual(len(names), 3)
        for name in names:
            self.assertTrue(name.startswith("ai_service."), name)

    def test_the_payload_is_json_safe_and_carries_no_bytes(self):
        # Whatever ends up in this dict crosses a process boundary as JSON. A
        # model instance or a file handle in here would fail at send time, in
        # production, inside an on_commit callback — the worst place to find it.
        import json
        import uuid

        from apps.knowledge import dispatch
        from apps.knowledge.models import Document, DocumentVersion, KnowledgeBase

        base = KnowledgeBase(id=uuid.uuid4(), name="B", slug="b")
        document = Document(id=uuid.uuid4(), knowledge_base=base, name="D")
        version = DocumentVersion(
            id=uuid.uuid4(),
            document=document,
            version_number=1,
            content_hash="a" * 64,
            embedding_model="m",
            embedding_model_version="v1",
        )
        version.file.name = "knowledge/x/v1.pdf"

        payload = dispatch.build_payload(version, job_id=str(uuid.uuid4()))
        json.dumps(payload)  # raises if anything is not serialisable

        self.assertEqual(
            set(payload),
            {
                # Carried so one upload can be traced across both services.
                "request_id",
                "job_id",
                "operation",
                "document_id",
                "document_version_id",
                "knowledge_base_id",
                "file_reference",
                "content_hash",
                "embedding_model",
                "embedding_model_version",
            },
        )
