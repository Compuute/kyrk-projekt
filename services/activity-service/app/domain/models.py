from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from uuid import uuid4


class ActivityType(str, Enum):
    YOUTH_TECH = "youth_tech"
    CODING = "coding"
    SUNDAY_SCHOOL = "sunday_school"
    LEADERSHIP = "leadership"
    DEBATE = "debate"
    COMMUNITY_HUB = "community_hub"
    OTHER = "other"


class Role(str, Enum):
    ADMIN = "admin"
    PASTOR = "pastor"
    SECRETARY = "secretary"
    VIEWER = "viewer"


AGE_BANDS = ("0-6", "7-12", "13-17", "18-25", "26+")


def _new_id() -> str:
    return str(uuid4())


@dataclass
class Activity:
    church_id: str
    activity_type: ActivityType
    date: date
    location: str
    funding_tag: str
    participants_total: int
    age_band_counts: dict[str, int]
    activity_id: str = field(default_factory=_new_id)


@dataclass
class Actor:
    user_id: str
    church_id: str
    role: Role
