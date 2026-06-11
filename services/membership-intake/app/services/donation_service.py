"""Donation receipt use cases. No framework imports.

Flow: a donor registers a reported gift (public). A kassör verifies it
against the bank statement (admin) — only then is the receipt emailed and
the donor address redacted. The site never observes the actual payment, so
nothing is ever sent on registration alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.churches import get_issuer, resolve_church_id
from app.domain.errors import (
    ChurchNotConfigured,
    ConsentMissing,
    DonationAlreadyProcessed,
    DonationNotFound,
    NotAuthorized,
    RateLimited,
)
from app.domain.models import Actor, DonationRecord, DonationStatus, Role
from app.ports.donation_repository import DonationRepository
from app.ports.email_sender import DonationReceipt, EmailSenderPort
from app.ports.rate_limiter import RateLimiterPort


_ADMIN_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.EDITOR}


@dataclass(frozen=True)
class DonationPayload:
    church_id: str
    amount_sek: int
    method: str
    email: str
    gdpr_consent: bool


@dataclass(frozen=True)
class VerificationResult:
    donation_id: str
    status: str
    receipt_number: str


class DonationService:
    def __init__(
        self,
        repo: DonationRepository,
        email_sender: EmailSenderPort,
        limiter: RateLimiterPort,
    ) -> None:
        self._repo = repo
        self._email_sender = email_sender
        self._limiter = limiter

    # ------------------------------------------------------------------- public

    def register(self, payload: DonationPayload, client_ip: str) -> DonationRecord:
        if not payload.gdpr_consent:
            raise ConsentMissing("gdpr_consent is required")
        if get_issuer(payload.church_id) is None:
            raise ChurchNotConfigured(
                f"church {payload.church_id} is not configured for gåvokvitton"
            )

        ip_key = f"donation-ip:{client_ip}"
        church_key = f"donation-church:{payload.church_id}"
        if not self._limiter.check(ip_key) or not self._limiter.check(church_key):
            raise RateLimited("too many donation registrations")

        donation = DonationRecord(
            church_id=payload.church_id,
            amount_sek=payload.amount_sek,
            method=payload.method,
            email=payload.email,
            gdpr_consent=payload.gdpr_consent,
        )
        self._repo.add(donation)
        return donation

    # -------------------------------------------------------------------- admin

    def list_pending(self, actor: Actor) -> list[DonationRecord]:
        self._require_admin(actor)
        return self._repo.list_pending(resolve_church_id(actor.church_id))

    def verify(self, actor: Actor, donation_id: str) -> VerificationResult:
        self._require_admin(actor)
        donation = self._load_scoped_pending(actor, donation_id)
        issuer = get_issuer(donation.church_id)
        if issuer is None:
            raise ChurchNotConfigured(
                f"church {donation.church_id} is not configured for gåvokvitton"
            )

        receipt_number = f"GK-{donation.received_at.year}-{donation.donation_id[:8].upper()}"

        # Send first: if the provider fails the donation stays PENDING so the
        # kassör can simply retry. Only a delivered receipt flips the status.
        self._email_sender.send_donation_receipt(
            DonationReceipt(
                to_email=donation.email,
                receipt_number=receipt_number,
                church_name=issuer.name,
                church_org_number=issuer.org_number,
                amount_sek=donation.amount_sek,
                method=donation.method,
                donated_at=donation.received_at,
                verified_at=datetime.now(timezone.utc),
            )
        )

        donation.mark_verified(actor.user_id, receipt_number)
        self._repo.update(donation)
        return VerificationResult(
            donation_id=donation.donation_id,
            status=donation.status.value,
            receipt_number=receipt_number,
        )

    def dismiss(self, actor: Actor, donation_id: str) -> DonationRecord:
        self._require_admin(actor)
        donation = self._load_scoped_pending(actor, donation_id)
        donation.mark_dismissed(actor.user_id)
        self._repo.update(donation)
        return donation

    # --------------------------------------------------------------- internals

    def _require_admin(self, actor: Actor) -> None:
        if actor.role not in _ADMIN_ROLES:
            raise NotAuthorized(f"role {actor.role.value} cannot perform this action")

    def _load_scoped_pending(self, actor: Actor, donation_id: str) -> DonationRecord:
        donation = self._repo.get(donation_id)
        if donation is None or donation.church_id != resolve_church_id(actor.church_id):
            raise DonationNotFound(donation_id)
        if donation.status is not DonationStatus.PENDING_VERIFICATION:
            raise DonationAlreadyProcessed(donation_id)
        return donation
