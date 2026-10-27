"""Main text of a saved research web page (tier 5, C3, #81).

Press releases and article pages carry menus, cookie banners and footers that would otherwise
become chunks. Keep the article body only: the first <article> or <main> element, else <body>,
with navigation, scripts and forms removed. The stored raw file is unchanged (its sha256 stays
the manifest's); only the parsed text is narrower.
bs4 comes with the ingest requirements (edgartools), so it is imported lazily.
"""
from __future__ import annotations

import re
from pathlib import Path

DROP = ["script", "style", "noscript", "nav", "header", "footer", "form", "aside", "svg",
        "button", "iframe", "template"]
# Containers whose class or id names say they are not article text.
NOISE = re.compile(r"cookie|consent|banner|breadcrumb|share|social|subscribe|related|promo|"
                   r"newsletter|menu|navbar|skip", re.I)


def article_text(path: Path) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
    for tag in soup(DROP):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.attrs is None:  # inside an element already removed
            continue
        names = " ".join(tag.get("class", [])) + " " + (tag.get("id") or "")
        if NOISE.search(names) and tag.name not in ("html", "body", "main", "article"):
            tag.decompose()
    candidates = soup.find_all("article") or soup.find_all("main")
    root = max(candidates, key=lambda t: len(t.get_text())) if candidates else (soup.body or soup)
    lines = [" ".join(line.split()) for line in root.get_text("\n").splitlines()]
    text, prev = [], None
    for line in lines:
        if line and line != prev:  # drop blanks and the doubled labels of collapsible menus
            text.append(line)
        prev = line or prev
    return "\n".join(text)
