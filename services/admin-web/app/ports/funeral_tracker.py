"""Port for tracking funeral and repatriation cases per church."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


FUNERAL_STATUSES = (
    "registered",      # case opened
    "documents",       # collecting documents
    "logistics",       # kista, transport, kylrum
    "ceremony",        # planning ceremony
    "completed",       # begravning genomförd
    "repatriation",    # hemtransport pågår (only if repatriation=True)
    "delivered",       # kropp mottagen i hemland
    "closed",          # allt klart, sorg-kalender aktiverad
)

CHECKLIST_ITEMS_SWEDEN = [
    ("doc_death_cert", "Dödsbevis mottaget"),
    ("doc_death_report", "Dödsanmälan till Skatteverket"),
    ("doc_burial_permit", "Gravsättningsintyg mottaget"),
    ("doc_funeral_program", "Begravningsprogram (am+sv+en)"),
    ("log_cold_storage", "Kylförvaring ordnad"),
    ("log_coffin", "Kista beställd"),
    ("log_ritual_washing", "Rituell tvagning (ንጽሕና) planerad"),
    ("log_flowers", "Blommor beställda"),
    ("log_transport_to_church", "Transport till kyrkan ordnad"),
    ("log_grave_confirmed", "Gravplats bekräftad"),
    ("cer_date_set", "Datum + tid bestämt med präst"),
    ("cer_vigil", "ሐዘን (vigil) planerad"),
    ("cer_kolliva", "Kolliva förberedd"),
    ("cer_choir", "Körmedlemmar notifierade"),
    ("cer_memorial_page", "Minnessida publicerad"),
    ("cer_telegram_broadcast", "Telegram-broadcast till församlingen"),
    ("aft_certificate", "Begravningsbevis utfärdat"),
    ("aft_invoice", "Faktura/kvitto till familjen"),
    ("aft_grief_calendar", "Sorg-kalender aktiverad"),
    ("aft_feedback", "Feedback från familjen"),
]

CHECKLIST_ITEMS_REPATRIATION = [
    ("rep_health_cert", "Intyg om icke-smittsam sjukdom (läkare)"),
    ("rep_embalming", "Balsamering genomförd + intyg (IATA-compliant)"),
    ("rep_zinc_coffin", "Zinkkista (IATA) svetsad/lödd"),
    ("rep_funeral_director_cert", "Begravningsentreprenörens intyg (kistinnehåll)"),
    ("rep_passersedel", "Passersedel utfärdad (Skatteverket)"),
    ("rep_embassy_permit", "Ambassad-tillstånd (Etiopien/Eritrea)"),
    ("rep_flight_booked", "Flygfrakt bokad (Ethiopian Airlines HUM, min 3 dagar)"),
    ("rep_air_waybill", "Air Waybill ifylld"),
    ("rep_receiver_confirmed", "Mottagare i hemland bekräftad"),
    ("rep_cargo_delivered", "Levererad till Arlanda Cargo Terminal"),
    ("rep_arrival_confirmed", "Ankomst bekräftad i Addis/Asmara"),
    ("rep_passersedel_returned", "Passersedel-kopia returnerad till Skatteverket (inom 2v)"),
]

MEMORIAL_DAYS = [
    (3, "ሳልስት", "Salist"),
    (7, "ሰባት", "Sebat"),
    (12, "አስራ ሁለት", "Asra Hulet"),
    (40, "አርባ", "Arba"),
    (180, "ስድስት ወር", "6 månader"),
    (365, "ዓመት", "1 år"),
]


@dataclass
class FuneralCase:
    case_id: str
    church_id: str
    status: str = "registered"
    created_at: datetime | None = None

    # Deceased info (no personnummer — YELLOW zone only)
    deceased_name: str = ""
    deceased_name_am: str = ""
    date_of_death: str = ""
    date_of_birth: str = ""
    contact_person: str = ""
    contact_phone: str = ""

    # Service options
    package: str = "standard"  # enkel | standard | komplett
    repatriation: bool = False
    repatriation_destination: str = ""  # "ethiopia" | "eritrea" | other
    ceremony_date: str = ""
    ceremony_time: str = ""
    burial_location: str = ""

    # Eder
    eder_name: str = ""
    eder_contribution: float = 0.0

    # Financials
    package_price: float = 0.0
    repatriation_price: float = 0.0
    total_price: float = 0.0
    paid: bool = False

    # Checklist (stored as JSON-serializable dict)
    checklist: dict[str, bool] = field(default_factory=dict)

    # Memorial
    memorial_page_url: str = ""
    memorial_text_sv: str = ""
    memorial_text_am: str = ""
    memorial_photo_url: str = ""

    # Grief calendar
    grief_calendar_active: bool = False
    next_memorial_date: str = ""
    next_memorial_name: str = ""

    notes: str = ""


PACKAGE_PRICES = {
    "enkel": 19_000,
    "standard": 28_000,
    "komplett": 35_000,
}

REPATRIATION_BASE_PRICE = 65_000


def calculate_price(package: str, repatriation: bool) -> tuple[float, float, float]:
    pkg = PACKAGE_PRICES.get(package, PACKAGE_PRICES["standard"])
    rep = REPATRIATION_BASE_PRICE if repatriation else 0
    return pkg, rep, pkg + rep


def build_checklist(repatriation: bool) -> dict[str, bool]:
    items = {key: False for key, _ in CHECKLIST_ITEMS_SWEDEN}
    if repatriation:
        items.update({key: False for key, _ in CHECKLIST_ITEMS_REPATRIATION})
    return items


def checklist_progress(checklist: dict[str, bool]) -> tuple[int, int]:
    total = len(checklist)
    done = sum(1 for v in checklist.values() if v)
    return done, total


class FuneralTrackerPort(Protocol):
    def list_cases(self, church_id: str) -> list[FuneralCase]: ...

    def get_case(self, church_id: str, case_id: str) -> FuneralCase | None: ...

    def save_case(self, case: FuneralCase) -> None: ...

    def delete_case(self, church_id: str, case_id: str) -> None: ...
