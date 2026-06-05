"""Tests for the HTML certificate generator."""
from datetime import date

import pytest

from app.adapters.html_pdf_generator import HtmlPdfGenerator
from app.domain.models import Certificate, CertificateType


def _cert(cert_type: CertificateType = CertificateType.BAPTISM) -> Certificate:
    return Certificate(
        church_id="c1",
        church_name="Abune Tekle Haymanot",
        certificate_type=cert_type,
        issued_date=date(2025, 6, 1),
        member_id="m-1",
        issued_by_user_id="u-admin",
        certificate_id="cert-abc-123",
    )


@pytest.fixture
def gen() -> HtmlPdfGenerator:
    return HtmlPdfGenerator()


def test_html_contains_certificate_type_name(gen):
    html = gen.render(_cert(CertificateType.BAPTISM), "Abebe Bikila").decode("utf-8")
    # Should contain the Amharic name from certificate-types.json
    assert "የጥምቀት ምስክር ወረቀት" in html


def test_html_contains_member_name(gen):
    html = gen.render(_cert(), "Abebe Bikila").decode("utf-8")
    assert "Abebe Bikila" in html


def test_html_contains_church_name(gen):
    html = gen.render(_cert(), "Abebe Bikila").decode("utf-8")
    assert "Abune Tekle Haymanot" in html
    # Amharic church name
    assert "አቡነ ተክለ ሃይማኖት" in html


def test_html_contains_verification_url(gen):
    html = gen.render(_cert(), "Abebe Bikila").decode("utf-8")
    assert "certificates/verify/cert-abc-123" in html


def test_html_has_no_external_resources(gen):
    html = gen.render(_cert(), "Abebe Bikila").decode("utf-8")
    # No external stylesheets (rel="stylesheet" pointing to http)
    import re
    external_css = re.findall(r'<link[^>]+href="https?://', html)
    assert len(external_css) == 0, "no external stylesheets"
    # No external scripts
    external_js = re.findall(r'<script[^>]+src="https?://', html)
    assert len(external_js) == 0, "no external scripts"
    # All styles inline
    assert "<style>" in html


def test_sunday_school_seed_shows_correct_icon(gen):
    html = gen.render(
        _cert(CertificateType.SUNDAY_SCHOOL_SEED), "Kidist Yohannes"
    ).decode("utf-8")
    assert "\U0001f331" in html  # 🌱


def test_sunday_school_plant_shows_correct_icon(gen):
    html = gen.render(
        _cert(CertificateType.SUNDAY_SCHOOL_PLANT), "Kidist Yohannes"
    ).decode("utf-8")
    assert "\U0001f33f" in html  # 🌿


def test_sunday_school_tree_shows_correct_icon(gen):
    html = gen.render(
        _cert(CertificateType.SUNDAY_SCHOOL_TREE), "Kidist Yohannes"
    ).decode("utf-8")
    assert "\U0001f333" in html  # 🌳


def test_sunday_school_disciple_shows_correct_icon(gen):
    html = gen.render(
        _cert(CertificateType.SUNDAY_SCHOOL_DISCIPLE), "Kidist Yohannes"
    ).decode("utf-8")
    assert "\U0001f4d6" in html  # 📖


def test_sunday_school_servant_shows_correct_icon(gen):
    html = gen.render(
        _cert(CertificateType.SUNDAY_SCHOOL_SERVANT), "Kidist Yohannes"
    ).decode("utf-8")
    assert "\U0001f56f" in html  # 🕯


def test_sunday_school_ambassador_shows_correct_icon(gen):
    html = gen.render(
        _cert(CertificateType.SUNDAY_SCHOOL_AMBASSADOR), "Kidist Yohannes"
    ).decode("utf-8")
    assert "\U0001f451" in html  # 👑


def test_html_contains_issued_date(gen):
    html = gen.render(_cert(), "Abebe Bikila").decode("utf-8")
    assert "2025-06-01" in html


def test_html_is_valid_document(gen):
    html = gen.render(_cert(), "Abebe Bikila").decode("utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
