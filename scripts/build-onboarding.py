#!/usr/bin/env python3
"""Build a single HTML onboarding document from the selected docs.

Takes the new-engineer reading order and concatenates everything into
one self-contained `build/onboarding.html`. The file has a clickable
table of contents, print-friendly CSS, and no external assets — you
can email it, open it in a browser, or use the browser's "Save as
PDF" to ship a PDF to a new hire.

If `pandoc` is available locally, also emits `build/onboarding.pdf`
via `pandoc build/onboarding.html -o build/onboarding.pdf`. Pandoc
is optional — the HTML file is always generated.

Usage:
    python3 scripts/build-onboarding.py

Output:
    build/onboarding.html
    build/onboarding.pdf   (only if pandoc is installed)
"""
from __future__ import annotations

import html
import shutil
import subprocess
import sys
from pathlib import Path

# Re-use the inline markdown renderer from docs-serve.py to keep a
# single code path for markdown -> HTML.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module

_ds = import_module("docs-serve") if (Path(__file__).parent / "docs-serve.py").exists() else None
if _ds is None:
    # Allow the module name 'docs-serve' (hyphen) to be loaded explicitly
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "docs_serve", Path(__file__).parent / "docs-serve.py"
    )
    _ds = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(_ds)

render_markdown = _ds.render_markdown

PROJECT_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_DIR / "build"

# New-engineer reading order. This is the sequence that lands a new
# hire from "just got hired" to "can open a PR safely". Keep it short
# and intentional — not every doc belongs here.
READING_ORDER: list[tuple[str, str]] = [
    ("README.md",                         "Project overview"),
    ("CONTRIBUTING.md",                   "How to contribute"),
    ("docs/10-getting-started.md",        "Getting started (15 min)"),
    ("docs/00-vision.md",                 "Vision"),
    ("docs/01-architecture-red-yellow-green.md", "Architecture: RED / YELLOW / GREEN"),
    ("docs/03-mvp-scope.md",              "MVP scope"),
    ("docs/05-security-principles.md",    "Security principles"),
    ("docs/06-auth-strategy.md",          "Auth strategy"),
    ("docs/04-ai-boundaries.md",          "AI boundaries"),
    ("docs/07-openclaw-production-flow.md", "OpenClaw production flow"),
    ("docs/11-development-guide.md",      "Development guide"),
    ("docs/12-operations.md",             "Operations"),
    ("docs/13-runbook.md",                "Incident runbook"),
    ("docs/governance/rbac.md",           "RBAC matrix"),
    ("docs/governance/policies.md",       "Policies: retention, deletion, access"),
    ("docs/governance/security-review-template.md", "Security review template"),
]


HTML_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>kyrk-projekt — onboarding pack</title>
<style>
  :root {{
    --fg: #1f2230;
    --muted: #6b7280;
    --bg: #ffffff;
    --accent: #3b5bdb;
    --border: #e5e7eb;
    --code-bg: #f3f4f6;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: Georgia, "Times New Roman", serif;
    color: var(--fg);
    background: var(--bg);
    line-height: 1.55;
  }}
  main {{ max-width: 740px; margin: 40px auto; padding: 0 32px; }}
  .cover {{
    text-align: center;
    padding: 60px 0 40px;
    border-bottom: 2px solid var(--fg);
    margin-bottom: 40px;
  }}
  .cover h1 {{ font-size: 36px; margin: 0 0 6px; }}
  .cover .subtitle {{ font-size: 16px; color: var(--muted); }}
  .cover .version {{ margin-top: 16px; font-size: 12px; color: var(--muted); }}
  nav.toc {{
    background: #f8f9fb;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 18px 24px;
    margin-bottom: 48px;
  }}
  nav.toc h2 {{ margin-top: 0; font-size: 18px; }}
  nav.toc ol {{ margin: 0; padding-left: 20px; }}
  nav.toc li {{ margin: 4px 0; }}
  nav.toc a {{ color: var(--accent); text-decoration: none; }}
  .section {{
    margin-bottom: 56px;
    padding-bottom: 40px;
    border-bottom: 1px dashed var(--border);
  }}
  .section:last-child {{ border-bottom: none; }}
  .section-header {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 20px;
    border-bottom: 2px solid var(--fg);
    padding-bottom: 6px;
  }}
  .section-num {{
    font-family: sans-serif;
    font-weight: bold;
    color: var(--muted);
    font-size: 14px;
  }}
  .section h1 {{ margin: 0; font-size: 26px; }}
  h2 {{ font-size: 20px; margin-top: 24px; }}
  h3 {{ font-size: 16px; margin-top: 18px; }}
  code {{ background: var(--code-bg); padding: 1px 5px; border-radius: 3px; font-size: 13px; font-family: "SFMono-Regular", Consolas, monospace; }}
  pre {{
    background: #1f2230;
    color: #e4e6ef;
    padding: 12px 14px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.5;
    font-family: "SFMono-Regular", Consolas, monospace;
  }}
  pre code {{ background: transparent; color: inherit; padding: 0; font-size: 12px; }}
  a {{ color: var(--accent); }}
  table {{ border-collapse: collapse; margin: 12px 0; font-size: 14px; }}
  th, td {{ border: 1px solid var(--border); padding: 5px 10px; }}
  th {{ background: #f3f4f6; text-align: left; }}
  blockquote {{
    border-left: 4px solid var(--accent);
    padding: 2px 12px;
    color: var(--muted);
    background: #f8f9fb;
    margin: 12px 0;
  }}
  footer {{
    margin-top: 48px;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
  }}
  /* Print styles — activates when user does Cmd+P / Ctrl+P */
  @media print {{
    body {{ font-size: 10pt; }}
    main {{ max-width: 100%; margin: 0; padding: 0 20mm; }}
    .cover {{ page-break-after: always; }}
    nav.toc {{ page-break-after: always; }}
    .section {{ page-break-before: always; border-bottom: none; }}
    pre {{
      background: #f3f4f6;
      color: var(--fg);
      border: 1px solid var(--border);
    }}
    footer {{ page-break-before: avoid; }}
    a {{ color: var(--fg); text-decoration: underline; }}
    a::after {{ content: " (" attr(href) ")"; font-size: 8pt; color: var(--muted); }}
  }}
</style>
</head>
<body>
<main>
  <section class="cover">
    <h1>kyrk-projekt</h1>
    <div class="subtitle">Onboarding pack — for new engineers</div>
    <div class="version">Generated from <code>scripts/build-onboarding.py</code></div>
  </section>

  <nav class="toc">
    <h2>Contents</h2>
    <ol>
      {toc}
    </ol>
  </nav>

  {sections}

  <footer>
    This document is generated from the docs/ tree. For the latest
    version, run <code>make onboarding</code> in the kyrk-projekt
    repo, or open the live docs viewer with <code>make docs-serve</code>.
  </footer>
</main>
</body>
</html>
"""


def _slugify(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def build() -> Path:
    BUILD_DIR.mkdir(exist_ok=True)

    toc_items: list[str] = []
    section_blocks: list[str] = []
    found = 0
    missing: list[str] = []

    for idx, (rel, title) in enumerate(READING_ORDER, start=1):
        path = PROJECT_DIR / rel
        if not path.exists():
            missing.append(rel)
            continue
        found += 1
        slug = _slugify(f"{idx}-{title}")
        toc_items.append(
            f'<li><a href="#{slug}">{html.escape(title)}</a>'
            f' <span style="color:#6b7280">({html.escape(rel)})</span></li>'
        )
        body_html = render_markdown(path.read_text(encoding="utf-8"))
        section_blocks.append(
            f'<section class="section" id="{slug}">\n'
            f'  <div class="section-header">'
            f'    <span class="section-num">{idx:02d}</span>'
            f'    <h1>{html.escape(title)}</h1>'
            f'  </div>\n'
            f'  {body_html}\n'
            f"</section>"
        )

    page = HTML_TMPL.format(
        toc="\n      ".join(toc_items),
        sections="\n\n".join(section_blocks),
    )
    out = BUILD_DIR / "onboarding.html"
    out.write_text(page, encoding="utf-8")

    print(f"wrote {out}")
    print(f"  sections: {found} / {len(READING_ORDER)}")
    if missing:
        print(f"  missing:  {len(missing)}")
        for m in missing:
            print(f"    - {m}")

    # Try pandoc for PDF
    if shutil.which("pandoc"):
        pdf = BUILD_DIR / "onboarding.pdf"
        try:
            subprocess.run(
                ["pandoc", str(out), "-o", str(pdf),
                 "--pdf-engine=wkhtmltopdf"],
                check=True,
                stderr=subprocess.DEVNULL,
            )
            print(f"wrote {pdf}")
        except subprocess.CalledProcessError:
            # wkhtmltopdf not installed — fall back to default engine
            try:
                subprocess.run(
                    ["pandoc", str(out), "-o", str(pdf)],
                    check=True,
                )
                print(f"wrote {pdf}")
            except subprocess.CalledProcessError:
                print("pandoc found but PDF export failed — open the HTML in a browser and use Save as PDF")
    else:
        print("pandoc not installed — open build/onboarding.html in a browser and use Cmd+P / Ctrl+P to save as PDF")
    return out


if __name__ == "__main__":
    build()
