"""In-memory fake content store for tests and local dev."""
from __future__ import annotations

import copy


DEFAULT_CONTENT: dict = {
    "version": "2.0",
    "church": {
        "name": {"sv": "Sankt Johannes Ortodoxa Kyrka", "am": "ቅዱስ ዮሐንስ ኦርቶዶክስ ቤተ ክርስቲያን"},
        "tagline": {"sv": "Välkommen hem", "am": "እንኳን ወደ ቤትዎ ደህና መጡ"},
    },
    "upcoming": [
        {
            "title": {"sv": "Söndagsgudstjänst", "am": "የእሁድ ቅዳሴ"},
            "date": "2025-06-08",
            "time": "11:00",
            "description": {
                "sv": "Gudstjänst med nattvard. Alla välkomna.",
                "am": "ቅዳሴ ከቁርባን ጋር። ሁሉም እንኳን ደህና መጡ።",
            },
        }
    ],
    "announcements": [
        {
            "title": {"sv": "Nytt bidrag beviljat!", "am": "አዲስ ድጋፍ ተፈቀደ!"},
            "body": {
                "sv": "Vi har fått 200 000 SEK från Arvsfonden.",
                "am": "ከአርቭስፎንደን 200,000 SEK ተቀብለናል።",
            },
            "date": "2025-06-01",
        }
    ],
    "links": {
        "member": {"sv": "Bli medlem", "am": "አባል ይሁኑ", "url": "/intake"},
        "donate": {"sv": "Ge en gåva", "am": "ስጦታ ይስጡ", "url": "/donate"},
        "telegram": {
            "sv": "Följ oss på Telegram",
            "am": "በቴሌግራም ይከተሉን",
            "url": "https://t.me/kyrka_kanal",
        },
        "youth": {"sv": "Ungdomsverksamhet", "am": "የወጣቶች ፕሮግራም", "url": "/youth"},
    },
    "footer": {
        "privacy": {
            "sv": "Den här sidan använder inga kakor och spårar dig inte.",
            "am": "ይህ ገጽ ኩኪዎችን አይጠቀምም እና አይከታተልዎትም።",
        }
    },
}


class FakeContentStore:
    def __init__(self) -> None:
        self._data: dict = copy.deepcopy(DEFAULT_CONTENT)

    def load(self) -> dict:
        return copy.deepcopy(self._data)

    def save(self, content: dict) -> None:
        self._data = copy.deepcopy(content)
