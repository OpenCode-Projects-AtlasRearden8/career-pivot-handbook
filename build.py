#!/usr/bin/env python3
"""Build the Career Pivot Handbook static site from docs/ into site/.

Zero dependencies: Python 3.8+ standard library only. Local-first: no
network calls, no accounts, no telemetry.

Usage:
    python3 build.py            # build site/
    python3 build.py --serve    # build, then serve at http://localhost:8000

Copyright (c) 2026 Asdale Dynamics, LLC. MIT License.
"""

import argparse
import html
import os
import re
import shutil
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
SITE = os.path.join(ROOT, "site")

TITLES = {
    "00-introduction.md": "Introduction: You Can Change Careers (Really)",
    "01-why-pivot.md": "Chapter 1: Naming Why You Want to Pivot",
    "02-transferable-skills.md": "Chapter 2: Inventorying Your Transferable Skills",
    "03-resume-rewrites-with-ai.md": "Chapter 3: Résumé Rewrites with AI Help",
    "04-portfolio-first-proof.md": "Chapter 4: Portfolio-First Proof",
    "05-learning-paths.md": "Chapter 5: Affordable Learning Paths",
    "06-side-income-ladder.md": "Chapter 6: The Side-Income Ladder",
    "07-impostor-feelings.md": "Chapter 7: Impostor Feelings (Pep Talks)",
    "worksheets/pivot-reasons.md": "Worksheet: Pivot Reasons",
    "worksheets/skills-inventory.md": "Worksheet: Skills Inventory",
    "worksheets/resume-rewrite.md": "Worksheet: Résumé Rewrite",
    "worksheets/portfolio-plan.md": "Worksheet: Portfolio Plan",
    "worksheets/learning-plan.md": "Worksheet: Learning Plan",
    "worksheets/income-ladder.md": "Worksheet: Income Ladder",
    "worksheets/pep-talk-notes.md": "Worksheet: Pep Talk Notes",
}

CHAPTER_DESCS = {
    "00-introduction.md": "How to use this handbook, promises kept and broken.",
    "01-why-pivot.md": "Move toward something, not just away from something.",
    "02-transferable-skills.md": "Rename old-work skills in new-field language.",
    "03-resume-rewrites-with-ai.md": "Free AI tools, honest drafting, one résumé per target.",
    "04-portfolio-first-proof.md": "Proof beats claims: a small, honest site of real artifacts.",
    "05-learning-paths.md": "Learn for free, produce while you learn, low-energy friendly.",
    "06-side-income-ladder.md": "Earn before you leap, rung by documented rung.",
    "07-impostor-feelings.md": "Six pre-written pep talks, plus the worst-case audit.",
}

# ---------------------------------------------------------------------------
# Small Markdown renderer (the subset used by the handbook)
# ---------------------------------------------------------------------------

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*(.+?)\*\*(?!\*)")
ITAL = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")

UL_ITEM = re.compile(r"^[-*]\s+(.*)$")
OL_ITEM = re.compile(r"^(\d+)\.\s*(.*)$")
CHECK = re.compile(r"^\[([ xX])\]\s*(.*)$")
CELL_RULE = re.compile(r"^:?-{2,}:?$")


def _inline(text, escape=True):
    """Render inline markdown (code, bold, links) to HTML.

    Recursion passes escape=False because the string is already escaped
    once, at the outermost call.
    """
    s = IMAGE.sub("", html.escape(text, quote=False)) if escape else text
    s = INLINE_CODE.sub(lambda m: "<code>%s</code>" % m.group(1), s)
    s = BOLD.sub(lambda m: "<strong>%s</strong>" % _inline(m.group(1), False), s)
    s = ITAL.sub(lambda m: "<em>%s</em>" % _inline(m.group(1), False), s)
    s = LINK.sub(lambda m: _link_html(m.group(1), m.group(2)), s)
    return s


def _link_html(label, href):
    if SCHEME.match(href) or href.startswith("#"):
        return '<a href="%s">%s</a>' % (href, label)
    return '<a href="%s">%s</a>' % (href.replace(".md", ".html"), label)


def _flush(paragraph_open, out, buf):
    if paragraph_open:
        out.append("<p>%s</p>\n" % _inline(" ".join(buf).strip()))
        buf.clear()
    return False


def _code_block(lines, idx, out):
    out.append("<pre><code>")
    idx += 1
    while idx < len(lines) and not lines[idx].startswith("```"):
        out.append(html.escape(lines[idx]) + "\n")
        idx += 1
    out.append("</code></pre>\n")
    return idx + 1


def _is_separator(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(CELL_RULE.match(c) for c in cells)


def _table_block(lines, idx):
    header = [c.strip() for c in lines[idx].strip().strip("|").split("|")]
    idx += 2
    head = "<tr><th>%s</th></tr>\n" % "</th><th>".join(_inline(c) for c in header)
    out = ["<table>\n<thead>\n", head, "</thead>\n<tbody>\n"]
    n = 0
    while idx < len(lines) and lines[idx].strip().startswith("|"):
        cells = [c.strip() for c in lines[idx].strip().strip("|").split("|")]
        out.append("<tr><td>%s</td></tr>\n" % "</td><td>".join(_inline(c) for c in cells))
        idx += 1
        n += 1
    out.append("</tbody>\n</table>\n")
    return idx, "".join(out), n


def _list_block(lines, idx, out, ordered):
    """Consume a consecutive run of list items; render, return new index."""
    out.append("<%s>\n" % ("ol" if ordered else "ul"))
    pattern = OL_ITEM if ordered else UL_ITEM
    while idx < len(lines) and pattern.match(lines[idx].strip()):
        m = pattern.match(lines[idx].strip())
        text = m.group(2) if ordered else m.group(1)
        cb = CHECK.match(text)
        if cb:
            text = "%s %s" % ("☑" if cb.group(1).lower() == "x" else "☐",
                              cb.group(2))
        # absorb indented continuation lines into this item
        idx += 1
        while idx < len(lines) \
                and re.match(r"^\s{2,}\S", lines[idx]) \
                and not UL_ITEM.match(lines[idx].strip()) \
                and not OL_ITEM.match(lines[idx].strip()) \
                and not lines[idx].lstrip().startswith(">"):
            text += " " + lines[idx].strip()
            idx += 1
        out.append("<li>%s</li>\n" % _inline(text))
    out.append("</%s>\n" % ("ol" if ordered else "ul"))
    return idx


def render_markdown(text):
    lines = text.split("\n")
    out = []
    idx = 0
    in_p = False
    buf = []
    last_idx, stuck = -1, 0
    while idx < len(lines):
        if idx == last_idx:
            stuck += 1
            if stuck > 1000:
                raise RuntimeError("STUCK at idx=%d line=%r" % (idx, lines[idx]))
        else:
            last_idx, stuck = idx, 0
        stripped = lines[idx].strip()

        # blank / standalone fill-in marker lines
        if not stripped or stripped.startswith("☐") or re.match(r"^\[\s?\]\s", stripped):
            in_p = _flush(in_p, out, buf)
            idx += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            in_p = _flush(in_p, out, buf)
            level = len(m.group(1))
            out.append("<h%d>%s</h%d>\n" % (level, _inline(m.group(2)), level))
            idx += 1
            continue

        # fenced code
        if stripped.startswith("```"):
            in_p = _flush(in_p, out, buf)
            idx = _code_block(lines, idx, out)
            continue

        # horizontal rule
        if stripped in ("---", "***"):
            in_p = _flush(in_p, out, buf)
            out.append("<hr>\n")
            idx += 1
            continue

        # blockquote (multi-line, with ">" on the closing line too)
        if stripped.startswith(">"):
            in_p = _flush(in_p, out, buf)
            chunks = []
            while idx < len(lines) and lines[idx].strip().startswith(">"):
                chunks.append(lines[idx].strip().lstrip(">").strip())
                idx += 1
            content = _inline(" ".join(chunks).strip())
            if not content:
                content = '<span class="fill-line"><br></span>'
            out.append("<blockquote>\n<p>%s</p>\n</blockquote>\n" % content)
            continue

        # table
        if stripped.startswith("|") and idx + 1 < len(lines) \
                and _is_separator(lines[idx + 1]):
            in_p = _flush(in_p, out, buf)
            idx, tbl, _ = _table_block(lines, idx)
            out.append(tbl)
            continue

        # lists
        if UL_ITEM.match(stripped) or OL_ITEM.match(stripped):
            in_p = _flush(in_p, out, buf)
            ordered = bool(OL_ITEM.match(stripped))
            idx = _list_block(lines, idx, out, ordered)
            continue

        # paragraph text (join consecutive lines, inline when the block ends)
        buf.append(stripped)
        in_p = True
        idx += 1
    _flush(in_p, out, buf)
    return "".join(out)


# ---------------------------------------------------------------------------
# Page scaffolding
# ---------------------------------------------------------------------------

STYLE = """
:root {
  --bg: #fdfbf7; --ink: #2b2b2b; --accent: #0d6b4f; --accent2: #7a4b18;
  --card: #ffffff; --line: #e6e0d6;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.65 Georgia, 'Times New Roman', serif; }
.layout { display: flex; min-height: 100vh; }
nav.toc { width: 270px; flex: 0 0 auto; background: #f6f2ea;
  border-right: 1px solid var(--line); padding: 1.2rem 1rem 2rem; }
nav.toc h2 { font-family: Helvetica, Arial, sans-serif; font-size: 0.72rem;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent2); }
nav.toc a { display: block; padding: 0.28rem 0.5rem; color: var(--ink);
  text-decoration: none; border-radius: 4px; font-size: 0.92rem;
  line-height: 1.35; }
nav.toc a:hover { background: #efe8d8; }
nav.toc a.active { background: var(--accent); color: #fff; }
nav.toc small { color: #8a8171; display: block; margin-top: 1.2rem;
  line-height: 1.7; }
main { flex: 1; max-width: 46rem; margin: 0 auto;
  padding: 2.5rem 2.2rem 3rem; }
h1 { font-family: Helvetica, Arial, sans-serif; font-size: 1.9rem;
  line-height: 1.25; color: var(--accent); margin-bottom: 0.4rem; }
h2 { font-family: Helvetica, Arial, sans-serif; font-size: 1.28rem;
  margin-top: 2.1rem; color: var(--accent); }
h3 { font-size: 1.05rem; font-family: Helvetica, Arial, sans-serif;
  color: var(--accent2); }
p { margin: 0.85rem 0; }
blockquote { border-left: 4px solid var(--accent2); margin: 1.2rem 0;
  padding: 0.55rem 1rem; background: #fbf6ec; font-style: italic; }
code { background: #eee9dd; padding: 0.1rem 0.35rem; border-radius: 3px;
  font-size: 0.88em; }
pre { background: #2f2c26; color: #f3efe6; padding: 1rem;
  border-radius: 6px; overflow-x: auto; }
pre code { background: transparent; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 1.1rem 0;
  font-size: 0.93rem; }
th, td { border: 1px solid var(--line); padding: 0.5rem 0.65rem;
  text-align: left; vertical-align: top; }
th { background: #efe8d8; font-family: Helvetica, Arial, sans-serif;
  font-size: 0.83rem; }
li .cb { color: var(--accent2); font-weight: bold; }
hr { border: none; border-top: 1px solid var(--line); margin: 2.2rem 0; }
.badge { display: inline-block; font-family: Helvetica, Arial, sans-serif;
  font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--accent2); border: 1px solid #e8d9a8; padding: 0.18rem 0.65rem;
  border-radius: 99px; margin-right: 0.3rem; }
.pager { display: flex; justify-content: space-between; gap: 1rem;
  margin-top: 3rem; font-family: Helvetica, Arial, sans-serif;
  font-size: 0.9rem; }
.pager a { color: var(--accent); text-decoration: none; }
.pager a:hover { text-decoration: underline; }
footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--line);
  font-size: 0.8rem; color: #8a8171; font-family: Helvetica, Arial, sans-serif; }
footer a { color: var(--accent2); }
.cardgrid { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 1rem; margin: 1.5rem 0; }
.card { background: var(--card); border: 1px solid var(--line);
  border-radius: 8px; padding: 0.9rem 1rem; }
.card a { color: var(--accent); text-decoration: none;
  font-family: Helvetica, Arial, sans-serif; font-size: 0.95rem;
  font-weight: bold; }
.card a:hover { text-decoration: underline; }
.card p { font-size: 0.88rem; color: #5d574b; margin: 0.35rem 0 0; }
@media (max-width: 860px) {
  .layout { flex-direction: column; }
  nav.toc { width: auto; border-right: none;
    border-bottom: 1px solid var(--line); }
}
@media print {
  nav.toc, .pager { display: none; }
  main { max-width: none; padding: 0; }
}
"""


def page_html(rel, body, title):
    """Render a full HTML page with sidebar navigation (depth-aware links)."""
    prefix = "" if not rel.startswith("worksheets/") else "../"
    nav_main, nav_ws = [], []
    for name in sorted(TITLES, key=lambda k: (k.startswith("worksheets"), k)):
        href = name.replace(".md", ".html")
        if name.startswith("worksheets/"):
            cls = ' class="active"' if name == rel else ""
            nav_ws.append('<a href="%sworksheets/%s"%s>%s</a>'
                          % (prefix, name[len("worksheets/"):].replace(
                              ".md", ".html"), cls, html.escape(TITLES[name])))
        else:
            cls = ' class="active"' if name == rel else ""
            nav_main.append('<a href="%s%s"%s>%s</a>' % (
                prefix, href, cls, html.escape(TITLES[name])))
    ws_part = "\n".join(nav_ws)
    footer_link = "%sindex.html" % prefix
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s — The Career Pivot Handbook</title>
<style>%s</style>
</head>
<body>
<div class="layout">
<nav class="toc">
<h2>Handbook</h2>
%s
<h2>Worksheets</h2>
%s
<small>Local-first · no tracking · no ads<br>
© 2026 Asdale Dynamics, LLC.<br>MIT License.</small>
</nav>
<main>
%s
<footer>
Created by <strong>Asdale Dynamics, LLC</strong> — beginning-friendly AI
education, books, and tools from Dylan Asdale (<a
href="https://dylanasdale.github.io">dylanasdale.github.io</a>, <em>The
Massive AI Manual</em>). This handbook is education only — never medical,
financial, tax, or legal advice. <a href="%s">Back to the start →</a>
</footer>
</main>
</div>
</body>
</html>
""" % (html.escape(title), STYLE, "\n".join(nav_main),
       ws_part, body, footer_link)


def build_site():
    if not os.path.isdir(DOCS):
        print("error: docs/ not found", file=sys.stderr)
        return 1
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(os.path.join(SITE, "worksheets"))
    ch_cards, ws_links = [], []

    for name in sorted(TITLES, key=lambda k: (k.startswith("worksheets"), k)):
        src = os.path.join(DOCS, name)
        if not os.path.exists(src):
            print("warning: missing docs/%s" % name, file=sys.stderr)
            continue
        with open(src, encoding="utf-8") as f:
            md = f.read()
        title = TITLES[name]
        # strip a leading "# title" line that duplicates the page title
        if md.startswith("# "):
            md = md.split("\n", 1)[1].lstrip("\n")
        body = render_markdown(md)
        badge = "Worksheet" if name.startswith("worksheets/") else "Chapter"
        body = ('<h1>%s</h1>\n<p><span class="badge">%s · local use only '
                "</span></p>\n" % (html.escape(title), badge)) + body
        out_rel = name.replace(".md", ".html")
        with open(os.path.join(SITE, out_rel), "w", encoding="utf-8") as f:
            f.write(page_html(name, body, title))
        if name.startswith("worksheets/"):
            ws_links.append('<a href="%s">%s</a>'
                            % (out_rel, html.escape(title)))
        else:
            ch_cards.append('<div class="card"><a href="%s">%s</a>'
                            "<p>%s</p></div>"
                            % (out_rel, html.escape(title),
                               html.escape(CHAPTER_DESCS.get(name, ""))))

    index_body = """<h1>The Career Pivot Handbook</h1>
<p><span class="badge">local-first</span><span class="badge">no job-board spam</span>
<span class="badge">worksheets included</span></p>
<p>A warm, plain-English manual for changing careers, with a bedside nurse
turning author and tech-builder as the worked example throughout — and steps
that adapt to anyone. Written by <strong>Asdale Dynamics, LLC</strong> in the
voice of Dylan Asdale's <em>The Massive AI Manual</em>: clear, kind, step by
step, never condescending.</p>
<h2>Start here: the chapters</h2>
<div class="cardgrid">
%s
</div>
<h2>Fill-in worksheets</h2>
<p>%s</p>
<h2>The promise</h2>
<p>Everything here runs on your computer, offline. No sign-ups, no tracking,
no ads, no job-board spam. Education only — never medical, financial, tax,
or legal advice.</p>
<h2>One honest caveat</h2>
<p>Changing careers takes months, not days. This handbook shows real
timelines and asks you to fill things in; reading alone will not move
anyone's résumé. Do the worksheets. Slow is normal.</p>
""" % (" ".join(ch_cards), " ".join(ws_links))
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page_html("_index", index_body, "The Career Pivot Handbook"))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Build the handbook site.")
    ap.add_argument("--serve", action="store_true",
                    help="serve site/ at http://localhost:8000 after build")
    args = ap.parse_args()
    rc = build_site()
    if rc:
        return rc
    n = sum(len(files) for _, _, files in os.walk(SITE))
    print("built site/ (%d files)" % n)
    if args.serve:
        os.chdir(SITE)
        print("serving http://127.0.0.1:8000 — Ctrl-C to stop")
        try:
            HTTPServer(("127.0.0.1", 8000), SimpleHTTPRequestHandler).serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
