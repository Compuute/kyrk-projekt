#!/usr/bin/env python3
"""Tiny local docs server.

Serves every .md file under `docs/`, `incidents/`, `CONTRIBUTING.md`,
and `README.md` as rendered HTML. Zero build step, no npm, no external
deps required at runtime — if the `markdown` package is importable it
is used, otherwise a small pure-Python fallback renders a subset good
enough to read the docs in a browser.

Usage:
    python3 scripts/docs-serve.py          # serves on http://127.0.0.1:8090
    python3 scripts/docs-serve.py 9000     # custom port

Stop with Ctrl+C.
"""
from __future__ import annotations

import html
import http.server
import re
import socketserver
import sys
from pathlib import Path
from urllib.parse import unquote

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8090

# Files we want to expose. Each entry is relative to PROJECT_DIR.
def discover_files() -> list[Path]:
    roots = [
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "CONTRIBUTING.md",
    ]
    roots += sorted((PROJECT_DIR / "docs").rglob("*.md"))
    incidents = PROJECT_DIR / "incidents"
    if incidents.exists():
        roots += sorted(incidents.glob("*.md"))
    return [r for r in roots if r.exists()]


# --------------------------------------------------------------- rendering

def _render_with_markdown_lib(src: str) -> str:
    import markdown  # type: ignore

    return markdown.markdown(
        src,
        extensions=["fenced_code", "tables", "toc"],
    )


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_LIST_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
_OL_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_CODE_INLINE_RE = re.compile(r"`([^`]+)`")
_HRULE_RE = re.compile(r"^---+\s*$")


def _fallback_inline(text: str) -> str:
    """Pragmatic inline markdown -> HTML (bold, inline code, links)."""
    text = html.escape(text)
    # Unescape backticks so code regex can find them
    text = _CODE_INLINE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = _LINK_RE.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    return text


def _render_fallback(src: str) -> str:
    """Minimal pure-Python markdown renderer.

    Covers: headers (h1-h6), fenced code blocks, unordered lists,
    numbered lists, paragraphs, horizontal rules, links, bold,
    inline code. Everything else passes through as escaped text.
    This is deliberately not a full CommonMark implementation — its
    job is to let a human read the docs in a browser when the real
    `markdown` package isn't installed.
    """
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    in_list = False
    in_olist = False

    def close_list():
        nonlocal in_list, in_olist
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_olist:
            out.append("</ol>")
            in_olist = False

    for line in src.splitlines():
        # Fenced code block
        m = _FENCE_RE.match(line)
        if m:
            if not in_code:
                close_list()
                in_code = True
                code_lang = m.group(1) or ""
                code_buf = []
            else:
                out.append(
                    f'<pre><code class="language-{html.escape(code_lang)}">'
                    + html.escape("\n".join(code_buf))
                    + "</code></pre>"
                )
                in_code = False
                code_buf = []
            continue
        if in_code:
            code_buf.append(line)
            continue

        # Horizontal rule
        if _HRULE_RE.match(line):
            close_list()
            out.append("<hr/>")
            continue

        # Headers
        m = _HEADER_RE.match(line)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(
                f"<h{level}>{_fallback_inline(m.group(2).strip())}</h{level}>"
            )
            continue

        # Unordered list
        m = _LIST_RE.match(line)
        if m:
            if in_olist:
                out.append("</ol>")
                in_olist = False
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_fallback_inline(m.group(2))}</li>")
            continue

        # Ordered list
        m = _OL_RE.match(line)
        if m:
            if in_list:
                out.append("</ul>")
                in_list = False
            if not in_olist:
                out.append("<ol>")
                in_olist = True
            out.append(f"<li>{_fallback_inline(m.group(3))}</li>")
            continue

        # Blank line
        if not line.strip():
            close_list()
            out.append("")
            continue

        # Paragraph
        close_list()
        out.append(f"<p>{_fallback_inline(line)}</p>")

    close_list()
    if in_code:
        out.append(
            "<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>"
        )
    return "\n".join(out)


def render_markdown(src: str) -> str:
    try:
        return _render_with_markdown_lib(src)
    except ImportError:
        return _render_fallback(src)


# ------------------------------------------------------------------ layout

PAGE_TMPL = """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="utf-8"/>
<title>{title} — kyrk-projekt docs</title>
<style>
  :root {{
    --fg: #222;
    --muted: #666;
    --bg: #faf9f6;
    --card: #fff;
    --accent: #3b5bdb;
    --border: #e5e5e5;
    --code-bg: #f3f4f6;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--fg);
    line-height: 1.6;
  }}
  .layout {{ display: flex; min-height: 100vh; }}
  aside {{
    width: 280px;
    background: #1f2230;
    color: #d6d8e0;
    padding: 20px 16px 48px;
    overflow-y: auto;
    position: sticky;
    top: 0;
    align-self: flex-start;
    height: 100vh;
  }}
  aside h1 {{ color: #fff; font-size: 16px; margin: 0 0 4px; }}
  aside .sub {{ color: #8a90a8; font-size: 12px; margin-bottom: 18px; }}
  aside ul {{ list-style: none; padding: 0; margin: 0; }}
  aside li {{ margin: 2px 0; }}
  aside a {{
    display: block;
    color: #c8cbdc;
    text-decoration: none;
    font-size: 13px;
    padding: 6px 8px;
    border-radius: 4px;
  }}
  aside a:hover {{ background: #2b2f40; color: #fff; }}
  aside a.active {{ background: #3b5bdb; color: #fff; }}
  aside .section {{
    margin-top: 14px;
    padding-top: 10px;
    border-top: 1px solid #2b2f40;
    color: #8a90a8;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding-left: 8px;
  }}
  main {{
    flex: 1;
    padding: 40px 48px;
    max-width: 820px;
  }}
  main h1 {{ margin-top: 0; }}
  main h2 {{ margin-top: 32px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  main h3 {{ margin-top: 24px; }}
  main code {{ background: var(--code-bg); padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
  main pre {{
    background: #1f2230;
    color: #e4e6ef;
    padding: 14px 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
  }}
  main pre code {{ background: transparent; color: inherit; padding: 0; }}
  main a {{ color: var(--accent); }}
  main table {{ border-collapse: collapse; margin: 12px 0; }}
  main th, main td {{ border: 1px solid var(--border); padding: 6px 10px; }}
  main th {{ background: #f3f4f6; text-align: left; }}
  main blockquote {{
    border-left: 4px solid var(--accent);
    padding: 4px 14px;
    color: var(--muted);
    background: #f3f4f6;
    margin: 12px 0;
  }}
  footer {{
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 13px;
  }}
  @media (max-width: 820px) {{
    .layout {{ flex-direction: column; }}
    aside {{ width: auto; position: static; height: auto; }}
    main {{ padding: 24px 20px; }}
  }}
</style>
</head>
<body>
<div class="layout">
  <aside>
    <h1>kyrk-projekt</h1>
    <div class="sub">Local docs viewer</div>
    {sidebar}
  </aside>
  <main>
    {content}
    <footer>
      Served locally from <code>{path}</code>. Not indexed, not tracked,
      not shipped anywhere.
    </footer>
  </main>
</div>
</body>
</html>
"""


def build_sidebar(files: list[Path], active: Path | None) -> str:
    """Group files into root / docs / governance / architecture /
    impact / incidents sections for readability."""
    groups: dict[str, list[Path]] = {
        "Root": [],
        "Docs": [],
        "Governance": [],
        "Architecture": [],
        "Impact": [],
        "Incidents": [],
    }
    for f in files:
        rel = f.relative_to(PROJECT_DIR)
        parts = rel.parts
        if len(parts) == 1:
            groups["Root"].append(f)
        elif parts[0] == "docs" and len(parts) == 2:
            groups["Docs"].append(f)
        elif parts[0] == "docs" and parts[1] == "governance":
            groups["Governance"].append(f)
        elif parts[0] == "docs" and parts[1] == "architecture":
            groups["Architecture"].append(f)
        elif parts[0] == "docs" and parts[1] == "impact":
            groups["Impact"].append(f)
        elif parts[0] == "incidents":
            groups["Incidents"].append(f)
        else:
            groups["Docs"].append(f)

    out = []
    for label, items in groups.items():
        if not items:
            continue
        out.append(f'<div class="section">{label}</div>')
        out.append("<ul>")
        for f in items:
            rel = f.relative_to(PROJECT_DIR).as_posix()
            klass = ' class="active"' if active and f == active else ""
            title = f.stem
            out.append(f'<li><a href="/{rel}"{klass}>{html.escape(title)}</a></li>')
        out.append("</ul>")
    return "\n".join(out)


# ----------------------------------------------------------------- handler

class DocsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = unquote(self.path.lstrip("/"))
        if not path or path == "/":
            path = "README.md"
        target = (PROJECT_DIR / path).resolve()
        try:
            target.relative_to(PROJECT_DIR)
        except ValueError:
            self.send_error(403, "outside project")
            return
        if not target.exists() or not target.is_file():
            self.send_error(404, "not found")
            return
        if target.suffix.lower() != ".md":
            # Serve non-markdown files (images inside docs) as-is
            self.send_response(200)
            self.end_headers()
            self.wfile.write(target.read_bytes())
            return
        src = target.read_text(encoding="utf-8")
        rendered = render_markdown(src)
        sidebar = build_sidebar(discover_files(), active=target)
        page = PAGE_TMPL.format(
            title=target.stem,
            sidebar=sidebar,
            content=rendered,
            path=html.escape(str(target.relative_to(PROJECT_DIR))),
        )
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: N802, ARG002
        # Quiet by default — uncomment to debug.
        pass


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    with socketserver.TCPServer(("127.0.0.1", port), DocsHandler) as httpd:
        print(f"kyrk-projekt docs serving on http://127.0.0.1:{port}")
        print("Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
