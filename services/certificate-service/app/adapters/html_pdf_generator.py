"""HTML-based certificate generator with multiple design themes.

Generates self-contained HTML document styled as a printable certificate.
Supports:
1. Ecclesiastical Theme: Double red-gold borders, Orthodox cross, bilingual parallel columns.
2. Sunday School Theme: Colorful growth color palettes, child friendly design, dynamic requirement checklists.
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

_SUNDAY_SCHOOL_THEMES = {
    "sunday_school_seed": {"color": "#2e7d32", "bg": "#f1f8e9", "icon": "🌱"},       # 🌱 Green
    "sunday_school_plant": {"color": "#2e7d32", "bg": "#f1f8e9", "icon": "🌿"},      # 🌿 Green
    "sunday_school_tree": {"color": "#1b5e20", "bg": "#e8f5e9", "icon": "🌳"},       # 🌳 Deep Green
    "sunday_school_disciple": {"color": "#1565c0", "bg": "#e3f2fd", "icon": "📖"},   # 📖 Blue
    "sunday_school_servant": {"color": "#e65100", "bg": "#fff3e0", "icon": "🕯"},    # 🕯 Orange/Gold
    "sunday_school_ambassador": {"color": "#4a148c", "bg": "#f3e5f5", "icon": "👑"}, # 👑 Royal Purple
}

_ECCLESIASTICAL_TEMPLATE = """<!DOCTYPE html>
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
  border: 8px double #8b6914;
  border-radius: 8px;
  padding: 40px 48px;
  position: relative;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.1);
}}
.certificate::before {{
  content: '';
  position: absolute;
  top: 6px; left: 6px; right: 6px; bottom: 6px;
  border: 2px solid #a30000;
  border-radius: 4px;
  pointer-events: none;
}}
.cross {{
  font-size: 40px;
  color: #a30000;
  margin-bottom: 8px;
}}
.church-name-am {{
  font-size: 20px;
  color: #333;
  font-weight: 600;
  margin-bottom: 4px;
}}
.church-name-sv {{
  font-size: 15px;
  color: #555;
  margin-bottom: 24px;
  letter-spacing: 0.5px;
}}
.cert-title-am {{
  font-size: 28px;
  font-weight: 700;
  color: #8b6914;
  margin-bottom: 4px;
}}
.cert-title-sv {{
  font-size: 18px;
  font-weight: 600;
  color: #666;
  margin-bottom: 28px;
  text-transform: uppercase;
}}
.columns {{
  display: flex;
  justify-content: space-between;
  margin: 20px 0;
  gap: 32px;
}}
.column {{
  flex: 1;
  text-align: justify;
  font-size: 14px;
  line-height: 1.6;
  color: #222;
}}
.column-am {{
  font-family: 'Noto Sans Ethiopic', sans-serif;
  direction: ltr;
}}
.column-sv {{
  font-family: 'Segoe UI', Roboto, sans-serif;
}}
.highlight-name {{
  font-size: 24px;
  font-weight: 700;
  color: #a30000;
  display: block;
  margin: 12px 0;
  text-align: center;
  border-bottom: 1px dashed #8b6914;
  padding-bottom: 4px;
}}
.meta-info {{
  margin-top: 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  font-size: 12px;
  color: #555;
}}
.sign-line {{
  width: 180px;
  border-top: 1px solid #8b6914;
  margin-top: 40px;
  padding-top: 6px;
  text-align: center;
}}
.verification {{
  font-size: 10px;
  color: #999;
  position: absolute;
  bottom: 15px;
  left: 48px;
  word-break: break-all;
}}
.verification a {{
  color: #8b6914;
  text-decoration: none;
}}
.seal-placeholder {{
  position: absolute;
  bottom: 35px;
  right: 48px;
  width: 80px;
  height: 80px;
  border: 2px dashed #8b6914;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #8b6914;
  text-align: center;
  line-height: 1.2;
.print-actions {{
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
}}
.print-actions button {{
  background: #a30000;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  font-size: 14px;
  font-family: inherit;
}}
.print-actions button:hover {{
  background: #7a0000;
}}
@media print {{
  body {{ background: white; padding: 0; }}
  .certificate {{ box-shadow: none; }}
  .print-actions {{ display: none; }}
}}
</style>
</head>
<body>
<div class="print-actions">
  <button onclick="window.print()">Skriv ut / Spara PDF</button>
</div>
<div class="certificate">
  <div class="cross">✠</div>
  <div class="church-name-am">{church_name_am}</div>
  <div class="church-name-sv">{church_name_sv}</div>
  
  <div class="cert-title-am">{cert_type_am}</div>
  <div class="cert-title-sv">{cert_type_sv}</div>

  <div class="columns">
    <div class="column column-am">
      በዚህ ቅዱስ ዕለት <span class="highlight-name">{member_name}</span> የተባሉት ይህንን ቤተ ክርስቲያን መንፈሳዊ ሥርዓት በምስክርነት እና በታማኝነት መፈጸማቸውን እናረጋግጣለን።
    </div>
    <div class="column column-sv">
      Härmed intygas med detta officiella dokument att <span class="highlight-name">{member_name}</span> har mottagit och fullbordat detta kyrkliga sakrament/handling.
    </div>
  </div>

  <div class="meta-info">
    <div>
      <strong>Issued Date / ቀን:</strong> {issued_date}<br/>
      <strong>Church / ቤተ ክርስቲያን:</strong> {issuing_church_name}
    </div>
    <div class="sign-line">
      Pastor / Underskrift
    </div>
  </div>

  <div class="verification">
    Verify / ማረጋገጫ: <a href="{verification_url}">{verification_url}</a>
  </div>

  <div class="seal-placeholder">Official<br/>Seal</div>
</div>
</body>
</html>
"""

_SUNDAY_SCHOOL_TEMPLATE = """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{cert_type_sv} — Söndagsskola</title>
<style>
@page {{
  size: A4 landscape;
  margin: 0;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: #eceff1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}}
.certificate {{
  width: 900px;
  min-height: 600px;
  background: #ffffff;
  border: 6px solid {theme_color};
  border-radius: 12px;
  padding: 36px 44px;
  position: relative;
  box-shadow: 0 6px 30px rgba(0,0,0,0.08);
}}
.inner-border {{
  position: absolute;
  top: 8px; left: 8px; right: 8px; bottom: 8px;
  border: 1px solid {theme_color};
  opacity: 0.3;
  border-radius: 8px;
  pointer-events: none;
}}
.header {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}}
.icon-badge {{
  font-size: 42px;
  background: {theme_bg};
  width: 70px;
  height: 70px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid {theme_color};
}}
.title-group {{
  text-align: left;
}}
.church-header {{
  font-size: 12px;
  text-transform: uppercase;
  color: #777;
  font-weight: 700;
  letter-spacing: 1px;
}}
.title-group h1 {{
  font-size: 24px;
  color: {theme_color};
  font-weight: 800;
}}
.diploma-title {{
  font-size: 32px;
  font-weight: 800;
  color: #1a1a1a;
  margin: 12px 0 6px 0;
  text-align: center;
}}
.subtitle {{
  font-size: 14px;
  color: #555;
  text-align: center;
  margin-bottom: 20px;
}}
.member-name {{
  font-size: 28px;
  font-weight: 700;
  color: {theme_color};
  text-align: center;
  margin: 10px auto;
  border-bottom: 2px solid {theme_color};
  display: block;
  width: 60%;
  padding-bottom: 4px;
}}
.split-content {{
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  gap: 36px;
}}
.requirements-card {{
  flex: 1.3;
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px 20px;
  text-align: left;
}}
.requirements-card h3 {{
  font-size: 13px;
  color: {theme_color};
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 4px;
}}
.req-list {{
  list-style: none;
  font-size: 11px;
  color: #333;
  line-height: 1.8;
}}
.req-list li {{
  margin-bottom: 4px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}}
.check-mark {{
  color: {theme_color};
  font-weight: bold;
}}
.sign-card {{
  flex: 0.7;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 12px;
  color: #555;
  text-align: left;
}}
.sign-line {{
  border-top: 1px solid #ccc;
  margin-top: 40px;
  padding-top: 6px;
  text-align: center;
}}
.verification {{
  font-size: 9px;
  color: #999;
  position: absolute;
  bottom: 15px;
  left: 44px;
}}
.verification a {{
  color: {theme_color};
  text-decoration: none;
}}
.print-actions {{
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
}}
.print-actions button {{
  background: {theme_color};
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  font-size: 14px;
  font-family: inherit;
}}
.print-actions button:hover {{
  filter: brightness(0.85);
}}
@media print {{
  body {{ background: white; padding: 0; }}
  .certificate {{ box-shadow: none; }}
  .print-actions {{ display: none; }}
}}
</style>
</head>
<body>
<div class="print-actions">
  <button onclick="window.print()">Skriv ut / Spara PDF</button>
</div>
<div class="certificate">
  <div class="inner-border"></div>
  
  <div class="header">
    <div class="icon-badge">{icon}</div>
    <div class="title-group">
      <div class="church-header">Abune Tekle Haymanot Söndagsskola</div>
      <h1>{cert_type_sv}</h1>
    </div>
  </div>

  <div class="diploma-title">DIPLOM / የሰንበት ትምህርት ምስክር ወረቀት</div>
  <div class="subtitle">Härmed tilldelas detta bevis till / ይህ የምስክር ወረቀት የተሰጠው ለ:</div>
  
  <div class="member-name">{member_name}</div>

  <div class="split-content">
    <div class="requirements-card">
      <h3>Uppfyllda kunskapskrav / ያጠናቀቋቸው መመዘኛዎች</h3>
      <ul class="req-list">
        {checklist_html}
      </ul>
    </div>
    
    <div class="sign-card">
      <div>
        <strong>Datum / ቀን:</strong> {issued_date}<br/>
        <strong>Församling / ቤተ ክርስቲያን:</strong> {issuing_church_name}
      </div>
      <div class="sign-line">
        Söndagsskolans ledare / Underskrift
      </div>
    </div>
  </div>

  <div class="verification">
    Verify / ማረጋገጫ: <a href="{verification_url}">{verification_url}</a>
  </div>
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

        verification_url = (
            f"https://kyrka.se/certificates/verify/{certificate.certificate_id}"
        )

        church_name_am = (
            "አቡነ ተክለ ሃይማኖት "
            "ኢትዮጵያ ኦርቶዶክስ "
            "ተዋሕዶ ቤተ ክርስቲያን"
        )
        church_name_sv = "Abune Tekle Haymanot Etiopiska Ortodoxa Tewahedo Kyrkan"

        # Determine theme layout
        if cert_type_key.startswith("sunday_school_"):
            theme = _SUNDAY_SCHOOL_THEMES.get(
                cert_type_key, {"color": "#333", "bg": "#f0f0f0", "icon": "🎓"}
            )
            
            # Build checklist of requirements dynamically
            reqs = type_meta.get("requirements", {})
            req_sv = reqs.get("sv", [])
            req_am = reqs.get("am", [])
            
            checklist_items = []
            for sv, am in zip(req_sv, req_am):
                checklist_items.append(
                    f'<li><span class="check-mark">✓</span> {sv} / {am}</li>'
                )
            if not checklist_items:
                checklist_items.append('<li><span class="check-mark">✓</span> Genomförd söndagsskolenivå / የሰንበት ትምህርት ደረጃን ያጠናቀቀ</li>')
            
            checklist_html = "\\n".join(checklist_items)
            
            html = _SUNDAY_SCHOOL_TEMPLATE.format(
                cert_type_sv=cert_type_sv,
                theme_color=theme["color"],
                theme_bg=theme["bg"],
                icon=theme["icon"],
                member_name=member_full_name,
                issued_date=certificate.issued_date.isoformat(),
                issuing_church_name=certificate.church_name or "Stockholms församling",
                checklist_html=checklist_html,
                verification_url=verification_url,
            )
        else:
            # Ecclesiastical / Liturgical Layout
            html = _ECCLESIASTICAL_TEMPLATE.format(
                cert_type_am=cert_type_am,
                cert_type_sv=cert_type_sv,
                church_name_am=church_name_am,
                church_name_sv=church_name_sv,
                member_name=member_full_name,
                issued_date=certificate.issued_date.isoformat(),
                issuing_church_name=certificate.church_name or "Abune Tekle Haymanot församling",
                verification_url=verification_url,
            )

        return html.encode("utf-8")
