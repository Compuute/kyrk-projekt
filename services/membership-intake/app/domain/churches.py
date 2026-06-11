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
    # The Zitadel organization id whose admins act for this church. In
    # production the auth adapter sets actor.church_id to this value
    # (urn:zitadel:iam:org:id) — resolve_church_id maps it back to the slug.
    zitadel_org_id: str = ""


_ISSUERS: dict[str, ReceiptIssuer] = {
    "nacka": ReceiptIssuer(
        church_id="nacka",
        name="Abune Tekle Haymanot Etiopiska Ortodoxa Tewahedo Kyrkan",
        org_number="802492-9237",
        # "EOTK Sverige" — currently the single shared organization. When more
        # churches get their own kassörer they need their own Zitadel orgs,
        # otherwise their admins would act for nacka too.
        zitadel_org_id="376713621675248694",
    ),
    # "stockholm" is intentionally absent: org_number not yet on file.
}


def get_issuer(church_id: str) -> ReceiptIssuer | None:
    return _ISSUERS.get(church_id)


def resolve_church_id(actor_church_id: str) -> str:
    """Map a Zitadel org id to its portal church slug.

    Tokens minted by the fake/test auth carry the slug directly — those pass
    through unchanged, as does any unknown value (which then simply scopes to
    nothing).
    """
    for issuer in _ISSUERS.values():
        if issuer.zitadel_org_id and issuer.zitadel_org_id == actor_church_id:
            return issuer.church_id
    return actor_church_id
