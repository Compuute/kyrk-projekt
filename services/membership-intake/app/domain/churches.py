"""Receipt issuer registry.

Only churches with a complete legal identity (name + org number) may issue
gåvokvitton. Onboarding a new church to the donation flow = add a row here
(see docs/25-deploy-och-innehallsflode.md for the rest of the checklist).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiptIssuer:
    church_id: str
    name: str
    org_number: str


_ISSUERS: dict[str, ReceiptIssuer] = {
    "nacka": ReceiptIssuer(
        church_id="nacka",
        name="Abune Tekle Haymanot Etiopiska Ortodoxa Tewahedo Kyrkan",
        org_number="802492-9237",
    ),
    # "stockholm" is intentionally absent: org_number not yet on file.
}


def get_issuer(church_id: str) -> ReceiptIssuer | None:
    return _ISSUERS.get(church_id)
