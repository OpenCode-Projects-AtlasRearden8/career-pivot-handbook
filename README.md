# The Career Pivot Handbook

A warm, plain-English manual for changing careers — with a bedside nurse
turning author/tech-builder as the worked example throughout, adaptable to
anyone. Built by **Asdale Dynamics, LLC** in the same beginner-friendly voice
as Dylan Asdale's *The Massive AI Manual*: clear, kind, step by step, never
condescending.

## What's inside

- **`docs/`** — Markdown chapters: transferable-skills inventory, résumé
  rewrites with AI, portfolio-first proof, affordable learning paths, a
  side-income ladder, and impostor-feeling pep talks.
- **`docs/worksheets/`** — Fill-in worksheets you complete in a text editor,
  in a notebook, or with the fill-in HTML pages.
- **`site/`** — A generated static HTML site (after you run the build).
- **`build.py`** — A zero-dependency Python build script. No packages to
  install, no accounts, no internet required after you have the files.

## Principles

- **Local-first.** Everything runs from your machine. No sign-ups, no
  tracking, no job-board spam, no ads, no affiliate links.
- **No secrets.** There are no API keys, accounts, or personal data in this
  repo. Worksheets are yours; never commit real personal details.
- **Worksheets over lectures.** Every chapter ends in something you *do*.

## How to run it

You need Python 3.8+ (standard library only).

```bash
python3 build.py          # builds site/ from docs/
python3 build.py --serve  # build + serve at http://localhost:8000
```

Open `site/index.html` in any browser. Re-run the build whenever you edit
anything in `docs/`.

## Verify the build

```bash
python3 build.py && python3 check_output.py
```

`check_output.py` sanity-checks the generated site (files exist, no broken
internal links, worksheets present). It should report `PASS`.

## Credit & license

Created by **Asdale Dynamics, LLC** — Dylan Asdale's company for
beginner-friendly AI education, books, and practical tools
(dylanasdale.github.io / *The Massive AI Manual*). Distributed under the MIT
License; see `LICENSE`.
