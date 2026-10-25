# STATUS.md

## What was built

**The Career Pivot Handbook** — a markdown-first manual for changing
careers, with a bedside nurse turning author/tech-builder (Maya) as the
worked example throughout, adaptable to anyone.

- `docs/` — 8 markdown chapters (introduction, why pivot, transferable
  skills, résumé rewrites with AI, portfolio-first proof, affordable
  learning paths, side-income ladder, impostor-feelings pep talks).
- `docs/worksheets/` — 7 fill-in worksheets (pivot reasons, skills
  inventory, résumé rewrite, portfolio plan, learning plan, income ladder,
  pep-talk notes), usable as printed pages or text files.
- `build.py` — zero-dependency Python static-site generator (stdlib only):
  renders every markdown file into a themed HTML page with sidebar
  navigation, badge labels, prev/next-free routing via index, mobile and
  print stylesheets, and a local HTTP server mode (`--serve`).
- `check_output.py` — verification script: confirms all 16 expected pages
  exist, all internal links/anchors resolve, no junk markup or CDN scripts,
  and every page has structure and links. Reports PASS.
- `site/` — generated static HTML output (16 files).
- `LICENSE` — MIT License; copyright line is exactly:
  `Copyright (c) 2026 Asdale Dynamics, LLC`
- `README.md` — usage, principles (local-first, no job-board spam, no
  secrets), and credits Asdale Dynamics, LLC.

## How to run it

Requires Python 3.8+, no packages installed.

```bash
python3 build.py          # build site/ from docs/
python3 build.py --serve  # build + serve at http://localhost:8000
python3 check_output.py   # verify the generated site (reports PASS)
```

Open `site/index.html` in any browser, or `python3 build.py --serve` and
visit http://localhost:8000.

## Verification results

- `python3 build.py` — succeeds; `built site/ (16 files)`.
- `python3 check_output.py` — `PASS: all checks succeeded` (files, internal
  links, anchors, no junk/CDN, index coverage).
- HTML tag-balance audit across all 16 generated pages — 0 unbalanced files
  (run via Python html.parser during development).
- `python3 build.py --serve` — server responds 200 for `index.html` and
  `worksheets/skills-inventory.html` (spot-checked with curl).
- Renderer hardening fixed during testing: tables, multi-line bold/italics,
  code fences, list continuation lines, checkbox items, depth-aware nav
  links for `worksheets/`, plus a stuck-guard that raises if the renderer
  ever fails to advance.

## Known gaps

- The markdown renderer covers the subset used by this handbook (headings,
  paragraphs, lists with continuation lines, checkbox items, tables,
  fenced code, blockquotes, inline code/bold/italic/links); it is not a
  full CommonMark implementation.
- Fill-in worksheets render as blank list items/tables; they are designed
  for printing or as prompts, not as interactive forms.
- No prev/next chapter pager (navigation is via the sidebar and index).
- Git repository is initialized locally with a first commit; nothing is
  pushed, published, or shared anywhere by design (local-first).
- `site/` is generated output and is intentionally not committed
  (`.gitignore`); regenerate it after any edit with `python3 build.py`.
