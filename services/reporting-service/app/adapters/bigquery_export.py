"""BigQuery export adapter.

Streams report payloads into a BigQuery table for analytics. YELLOW
data only — every payload has already passed `pii_guard.assert_no_pii`
before reaching this adapter.

IAM: the service account needs `roles/bigquery.dataEditor` on the
specific dataset (not project-wide). No view, no admin, no delete.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import Report

if TYPE_CHECKING:
    from google.cloud.bigquery import Client  # pragma: no cover


class BigQueryExport:
    def __init__(
        self,
        project_id: str,
        dataset_id: str,
        table_id: str = "reports",
        client: "Client | None" = None,
    ) -> None:
        self._project_id = project_id
        self._dataset_id = dataset_id
        self._table_id = table_id
        self._client = client

    def _ensure_client(self):
        if self._client is None:
            from google.cloud import bigquery  # pragma: no cover

            self._client = bigquery.Client(project=self._project_id)
        return self._client

    def _table_ref(self) -> str:
        return f"{self._project_id}.{self._dataset_id}.{self._table_id}"

    def publish(self, report: Report) -> None:
        client = self._ensure_client()
        row = {
            "report_id": report.report_id,
            "church_id": report.church_id,
            "kind": report.kind.value,
            "period": report.period,
            "created_at": report.created_at.isoformat(),
            # Store payload as JSON string to keep BQ schema simple. Schema
            # evolution per kind happens in downstream views.
            "payload_json": _to_json(report.payload),
        }
        errors = client.insert_rows_json(self._table_ref(), [row])
        if errors:
            # Generic error — never echo the row contents.
            raise RuntimeError("bigquery insert failed")


def _to_json(payload) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
