"""HTML-based certificate generator for production use.

Generates a self-contained HTML document styled as a printable certificate.
Uses trilingual metadata from certificate-types.json. The HTML can be
printed to PDF via the browser (Ctrl+P) or converted server-side with
wkhtmltopdf / Chrome headless.

No external resources — fully self-contained for offline printing.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import Certificate


def _load_certificate_types() -> dict:
    types_path = Path(__file__).resolve().parent.parent.parent / "certificate-types.json"
    with open(types_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("certificate_types", {})


_SUNDAY_SCHOOL_ICONS = {
    "sunday_school_seed": "\U0001f331",       # 🌱
    "sunday_school_plant": "\U0001f33f",       # 🌿
    "sunday_school_tree": "\U0001f333",        # 🌳
    "sunday_school_disciple": "\U0001f4d6",    # 📖
    "sunday_school_servant": "\U0001f56f",     # 🕯
    "sunday_school_ambassador": "\U0001f451",  # 👑
}


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="am">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{cert_type_am} — Abune Tekle Haymanot</title>
<style>
@page {{
  size: A4 landscape;
  margin: 0;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'Noto Sans Ethiopic', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: #f5f0e8;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}}

.certificate {{
  width: 900px;
  min-height: 600px;
  background: #fffef7;
  border: 3px solid #8b6914;
  border-radius: 8px;
  padding: 48px 56px;
  position: relative;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.1);
}}

.certificate::before {{
  content: '';
  position: absolute;
  top: 12px; left: 12px; right: 12px; bottom: 12px;
  border: 1px solid #c9a84c;
  border-radius: 4px;
  pointer-events: none;
}}

.cross-seal {{
  font-size: 56px;
  color: #8b6914;
  margin-bottom: 8px;
  line-height: 1;
}}

.church-name-am {{
  font-size: 20px;
  color: #333;
  margin-bottom: 4px;
  font-weight: 600;
}}

.church-name-sv {{
  font-size: 16px;
  color: #666;
  margin-bottom: 24px;
}}

.cert-type {{
  font-size: 28px;
  font-weight: 700;
  color: #8b6914;
  margin-bottom: 8px;
}}

.cert-icon {{
  font-size: 40px;
  margin-bottom: 8px;
}}

.cert-type-sv {{
  font-size: 16px;
  color: #888;
  margin-bottom: 32px;
}}

.member-name {{
  font-size: 32px;
  font-weight: 700;
  color: #222;
  margin-bottom: 8px;
  border-bottom: 2px solid #c9a84c;
  display: inline-block;
  padding-bottom: 4px;
}}

.issue-date {{
  font-size: 16px;
  color: #555;
  margin-top: 16px;
  margin-bottom: 24px;
}}

.verification {{
  font-size: 12px;
  color: #999;
  margin-top: 24px;
  word-break: break-all;
}}

.verification a {{
  color: #8b6914;
  text-decoration: none;
}}

.seal-placeholder {{
  position: absolute;
  bottom: 40px;
  right: 60px;
  width: 80px;
  height: 80px;
  border: 2px dashed #c9a84c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #c9a84c;
  text-align: center;
  line-height: 1.2;
}}

@media print {{
  body {{ background: white; padding: 0; }}
  .certificate {{ box-shadow: none; }}
}}
</style>
</head>
<body>
<div class="certificate">
  <div class="cross-seal">&#x2726;</div>
  <div class="church-name-am">{church_name_am}</div>
  <div class="church-name-sv">{church_name_sv}</div>

  {icon_html}
  <div class="cert-type">{cert_type_am}</div>
  <div class="cert-type-sv">{cert_type_sv}</div>

  <div class="member-name">{member_name}</div>

  <div class="issue-date">{issued_date}</div>

  <div class="verification">
    <a href="{verification_url}">{verification_url}</a>
  </div>

  <div class="seal-placeholder">Church<br/>Seal</div>
</div>
</body>
</html>
"""


class HtmlPdfGenerator:
    def __init__(self) -> None:
        self._cert_types = _load_certificate_types()

    def render(self, certificate: Certificate, member_full_name: str) -> bytes:
        cert_type_key = certificate.certificate_type.value
        type_meta = self._cert_types.get(cert_type_key, {})

        cert_type_am = type_meta.get("am", cert_type_key)
        cert_type_sv = type_meta.get("sv", cert_type_key)

        icon = _SUNDAY_SCHOOL_ICONS.get(cert_type_key, "")
        icon_html = f'<div class="cert-icon">{icon}</div>' if icon else ""

        verification_url = (
            f"https://kyrka.se/certificates/verify/{certificate.certificate_id}"
        )

        church_name_am = (
            "አቡነ ተክለ ሃይማኖት "
            "ኢትዮጵያ ኦርቶዶክስ "
            "ተዋሕዶ ቤተ ክርስቲያን"
        )
        church_name_sv = "Abune Tekle Haymanot Etiopiska Ortodoxa Tewahedo Kyrkan"

        html = _HTML_TEMPLATE.format(
            cert_type_am=cert_type_am,
            cert_type_sv=cert_type_sv,
            church_name_am=church_name_am,
            church_name_sv=church_name_sv,
            icon_html=icon_html,
            member_name=member_full_name,
            issued_date=certificate.issued_date.isoformat(),
            verification_url=verification_url,
            cert_id=certificate.certificate_id,
        )

        return html.encode("utf-8")
