"""Church registry: Zitadel-org → kyrka-scoping, plus kvittoutfärdare.

Två separata ansvar, medvetet åtskilda:

1. ``_ORG_TO_CHURCH`` — varje kyrka vars admins loggar in måste ha sitt
   Zitadel-organisations-id mappat till portal-slugen. Det driver
   ``resolve_church_id`` (RED-zon-scoping: vilken kyrkas data en admin ser).
   Varje kyrka har en egen Zitadel-org så admins är isolerade till sin egen
   församlings data.

2. ``_ISSUERS`` — endast kyrkor med komplett legal identitet (namn +
   org-nummer) får utfärda gåvokvitton. En kyrka kan vara scope:ad (admins
   fungerar) utan att ännu vara kvittoutfärdare.
"""
from __future__ import annotations

from dataclasses import dataclass


# Zitadel-org-id (claim urn:zitadel:iam:org:id) → portal-slug. I produktion
# sätter auth-adaptern actor.church_id till org-id:t; här mappas det tillbaka
# till slugen som domändatan nycklas på.
_ORG_TO_CHURCH: dict[str, str] = {
    "376720665740439161": "nacka",      # Nacka-kyrkan (Abune Tekle Haymanot)
    "376720690671258678": "stockholm",  # Hagsätra-kyrkan (Medhane Alem)
}


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
    # "stockholm" (Medhane Alem) är scope:ad för admin-inloggning via
    # _ORG_TO_CHURCH men är ännu inte kvittoutfärdare — org-numret är inte
    # bekräftat på fil. Lägg till en rad här när det är klart.
}


def get_issuer(church_id: str) -> ReceiptIssuer | None:
    return _ISSUERS.get(church_id)


def resolve_church_id(actor_church_id: str) -> str:
    """Map a Zitadel org id to its portal church slug.

    Tokens minted by the fake/test auth carry the slug directly — those pass
    through unchanged (a slug is never a key here), as does any unknown value
    (which then simply scopes to nothing).
    """
    return _ORG_TO_CHURCH.get(actor_church_id, actor_church_id)
