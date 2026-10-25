#!/usr/bin/env python3
"""Sanity-check the built site: files exist, internal links resolve,
worksheets present, and no obvious junk markup. Prints PASS or FAIL.

    python3 check_output.py

Copyright (c) 2026 Asdale Dynamics, LLC. MIT License.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")

EXPECTED = (
    "index.html",
    "00-introduction.html", "01-why-pivot.html",
    "02-transferable-skills.html", "03-resume-rewrites-with-ai.html",
    "04-portfolio-first-proof.html", "05-learning-paths.html",
    "06-side-income-ladder.html", "07-impostor-feelings.html",
    "worksheets/pivot-reasons.html", "worksheets/skills-inventory.html",
    "worksheets/resume-rewrite.html", "worksheets/portfolio-plan.html",
    "worksheets/learning-plan.html", "worksheets/income-ladder.html",
    "worksheets/pep-talk-notes.html",
)

failures = []


def check(label, ok, detail=""):
    print("%-52s %s" % (("PASS %s" % label) if ok else ("FAIL %s" % label), detail))
    if not ok:
        failures.append(label)


def main():
    for rel in EXPECTED:
        check("exists: %s" % rel, os.path.isfile(os.path.join(SITE, rel)))
    if failures:
        check("build first", False, "run: python3 build.py")

    for rel in EXPECTED:
        path = os.path.join(SITE, rel)
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        rel_dir = os.path.dirname(rel)

        # collect target fragments counted with # prefix
        heads = {m.group(1) for m in re.finditer(r'<h[1-6][^>]*id="([^"]+)"', text)}
        for href in re.finditer(r'href="([^"]+)"', text):
            href = href.group(1)
            if href.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            target, _, frag = href.partition("#")
            if target and not target.startswith("//"):
                target_path = os.path.normpath(os.path.join(rel_dir, target))
                if not os.path.isfile(os.path.join(SITE, target_path)):
                    failures.append("broken link %s in %s" % (href, rel))
            elif frag and not target:
                if frag not in heads:
                    failures.append("broken anchor #%s in %s" % (frag, rel))

        for junk in ("<script src=\"http", "var ga", "superseded-anchor"):
            if junk in text:
                failures.append("junk %r in %s" % (junk, rel))
        if "</htlm>" in text or text.count("<!doctype html>") != 1:
            failures.append("structure problem in %s" % rel)
        n = text.count("<h1>") + text.count("<h2>") + text.count("<h3>")
        if n == 0:
            failures.append("no headings in %s" % rel)
        if "</a>" not in text and rel != "worksheets/pep-talk-notes.html":
            failures.append("no links in %s" % rel)

    # index links to every page
    index = os.path.join(SITE, "index.html")
    if os.path.isfile(index):
        txt = open(index, encoding="utf-8").read()
        for rel in EXPECTED:
            if rel not in ("index.html",):
                if os.path.basename(rel) not in txt:
                    failures.append("index missing link to %s" % rel)

    if failures:
        print("\nFAIL: %d problem(s)" % len(failures))
        for f in sorted(set(failures)):
            print("  -", f)
        return 1
    print("\nPASS: all checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
