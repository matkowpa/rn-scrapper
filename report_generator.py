# -*- coding: utf-8 -*-
"""
Generuje raport Markdown z listy ogłoszeń na stanowisko członka rady nadzorczej.
"""

from datetime import datetime
from typing import List

from scraper import Announcement


def _md_escape(text: str) -> str:
    """Escape znaków specjalnych Markdown w tekście wierszowym."""
    # Escapujemy tylko potoki i znaczniki tabeli; nie ingerujemy w linki
    return text.replace("|", "\\|")


def _format_details(details: str, max_lines: int = 40) -> str:
    """
    Formatuje szczegółową treść ogłoszenia jako zablokowany cytat Markdown.
    Ogranicza do max_lines niepustych wierszy.
    """
    lines = [ln.strip() for ln in details.splitlines() if ln.strip()]
    truncated = len(lines) > max_lines
    selected = lines[:max_lines]
    block = "\n".join(f"> {ln}" for ln in selected)
    if truncated:
        block += "\n>\n> *(treść skrócona – odwiedź link po pełne ogłoszenie)*"
    return block


def generate_report(announcements: List[Announcement]) -> str:
    """
    Buduje i zwraca pełny raport jako ciąg znaków w formacie Markdown.

    Parametry
    ----------
    announcements : list[Announcement]
        Lista ogłoszeń zwrócona przez scraper.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    count = len(announcements)

    lines: List[str] = []

    # ── Nagłówek ──────────────────────────────────────────────────────────────
    lines += [
        "# Raport: Ogłoszenia na stanowisko Członka Rady Nadzorczej",
        "",
        f"**Data wygenerowania:** {now}  ",
        f"**Liczba znalezionych ogłoszeń:** {count}  ",
        f"**Źródło danych:** DuckDuckGo (region: pl-pl) + bezpośrednie pobieranie stron",
        "",
        "> **Uwaga metodyczna:** Wyniki obejmują wyłącznie ogłoszenia dotyczące "
        "stanowiska *członka rady nadzorczej*. Ogłoszenia na stanowiska zarządcze "
        "(np. członek zarządu, prezes zarządu) zostały odfiltrowane.",
        "",
        "---",
        "",
    ]

    if count == 0:
        lines += [
            "## Brak wyników",
            "",
            "Nie znaleziono ogłoszeń spełniających kryteria wyszukiwania. "
            "Spróbuj ponownie później lub dostosuj zapytania w pliku `scraper.py`.",
            "",
        ]
        return "\n".join(lines)

    # ── Spis treści ────────────────────────────────────────────────────────────
    lines += ["## Spis treści", ""]
    for i, ann in enumerate(announcements, 1):
        anchor = re.sub(r"[^\w\s-]", "", ann.title.lower()).strip()
        anchor = re.sub(r"[\s]+", "-", anchor)
        short_title = ann.title[:80] + ("…" if len(ann.title) > 80 else "")
        lines.append(f"{i}. [{short_title}](#{anchor})")
    lines += ["", "---", ""]

    # ── Szczegółowe ogłoszenia ─────────────────────────────────────────────────
    lines.append("## Ogłoszenia")
    lines.append("")

    for i, ann in enumerate(announcements, 1):
        short_title = ann.title[:100] + ("…" if len(ann.title) > 100 else "")

        lines += [
            f"### {i}. {short_title}",
            "",
        ]

        # Tabela metadanych
        lines += [
            "| Pole            | Wartość |",
            "|-----------------|---------|",
            f"| **Link**        | [{ann.url}]({ann.url}) |",
            f"| **Źródło**      | {_md_escape(ann.source_domain)} |",
            f"| **Data ogłoszenia** | {_md_escape(ann.date or '—  *(nie znaleziono)*')} |",
            "",
        ]

        # Skrót (snippet z wyszukiwarki)
        lines += [
            "#### Skrót ogłoszenia",
            "",
            f"> {_md_escape(ann.summary.strip().replace(chr(10), ' '))}",
            "",
        ]

        # Pełne szczegóły pobrane ze strony
        lines += [
            "#### Szczegóły (treść ze strony)",
            "",
            _format_details(ann.details),
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# Lokalny import re potrzebny do generowania kotwic
import re
