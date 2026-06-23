# -*- coding: utf-8 -*-
"""
Generuje raport HTML z listy ogłoszeń na stanowisko członka rady nadzorczej.
"""

import html as _html_lib
from datetime import date, datetime
from typing import List, Optional

from scraper import Announcement

# ---------------------------------------------------------------------------
# CSS osadzony w pliku (bez zewnętrznych zasobów)
# ---------------------------------------------------------------------------
_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f4f6f9;
    color: #2c3e50;
    padding: 24px 16px;
}
.container { max-width: 960px; margin: 0 auto; }

/* Nagłówek strony */
header {
    background: #1a3a5c;
    color: #fff;
    border-radius: 10px;
    padding: 28px 32px 20px;
    margin-bottom: 28px;
}
header h1 { font-size: 1.7rem; margin-bottom: 8px; }
header .meta { font-size: 0.88rem; opacity: 0.85; line-height: 1.8; }
header .badge {
    display: inline-block;
    background: #2ecc71;
    color: #fff;
    border-radius: 12px;
    padding: 2px 12px;
    font-size: 0.82rem;
    margin-left: 8px;
    vertical-align: middle;
}

/* Ostrzeżenie metodyczne */
.notice {
    background: #fff8e1;
    border-left: 4px solid #f39c12;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 24px;
    font-size: 0.9rem;
}

/* Filtr info */
.filter-info {
    background: #e8f4fd;
    border-left: 4px solid #3498db;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 28px;
    font-size: 0.9rem;
}

/* Karta ogłoszenia */
.card {
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 24px;
    overflow: hidden;
}
.card-header {
    background: #1a3a5c;
    color: #fff;
    padding: 14px 20px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}
.card-header h2 {
    font-size: 1.0rem;
    font-weight: 600;
    line-height: 1.4;
    flex: 1;
}
.card-header a { color: #aad4f5; text-decoration: none; }
.card-header a:hover { text-decoration: underline; }
.card-number {
    background: rgba(255,255,255,0.18);
    border-radius: 50%;
    min-width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 700;
    flex-shrink: 0;
}
.card-body { padding: 18px 20px; }

/* Tabela metadanych */
.meta-table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 0.88rem; }
.meta-table td { padding: 6px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
.meta-table td:first-child { font-weight: 600; color: #555; width: 130px; white-space: nowrap; }
.meta-table a { color: #2980b9; word-break: break-all; }

/* Skrót */
.section-label {
    font-size: 0.8rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
    margin-top: 14px;
}
.summary-box {
    background: #f8f9fa;
    border-left: 3px solid #95a5a6;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 0.9rem;
    font-style: italic;
    color: #555;
    line-height: 1.6;
}

/* Szczegóły – rozwijane */
details { margin-top: 12px; }
summary {
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    color: #2980b9;
    padding: 6px 0;
    list-style: none;
    user-select: none;
}
summary::before { content: "▶ "; font-size: 0.7em; }
details[open] summary::before { content: "▼ "; }
.details-content {
    background: #fdfdfd;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 14px;
    margin-top: 8px;
    font-size: 0.85rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 420px;
    overflow-y: auto;
    color: #444;
}

/* Brak wyników */
.empty {
    text-align: center;
    padding: 60px 20px;
    color: #888;
    font-size: 1.1rem;
}

/* Stopka */
footer {
    text-align: center;
    font-size: 0.8rem;
    color: #999;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #ddd;
}

/* Date badge */
.date-badge {
    display: inline-block;
    background: #e8f8f0;
    color: #27ae60;
    border: 1px solid #a9dfbf;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.8rem;
    font-weight: 600;
}
.date-unknown {
    background: #fef9e7;
    color: #b7950b;
    border-color: #f9e79f;
}
"""


def _e(text: str) -> str:
    """HTML escape."""
    return _html_lib.escape(str(text))


def _render_card(idx: int, ann: Announcement) -> str:
    date_label = ann.date or "—"
    date_class = "date-badge" if ann.date_parsed else "date-badge date-unknown"

    # Skróć szczegóły do rozsądnej długości
    details_lines = [ln.strip() for ln in ann.details.splitlines() if ln.strip()]
    details_text = "\n".join(details_lines[:60])
    if len(details_lines) > 60:
        details_text += "\n\n… (treść skrócona – odwiedź link po pełne ogłoszenie)"

    return f"""
<div class="card" id="ann-{idx}">
  <div class="card-header">
    <span class="card-number">{idx}</span>
    <h2><a href="{_e(ann.url)}" target="_blank" rel="noopener">{_e(ann.title)}</a></h2>
  </div>
  <div class="card-body">
    <table class="meta-table">
      <tr>
        <td>Data ogłoszenia</td>
        <td><span class="{date_class}">{_e(date_label)}</span></td>
      </tr>
      <tr>
        <td>Źródło</td>
        <td>{_e(ann.source_domain)}</td>
      </tr>
      <tr>
        <td>Link</td>
        <td><a href="{_e(ann.url)}" target="_blank" rel="noopener">{_e(ann.url)}</a></td>
      </tr>
    </table>

    <div class="section-label">Skrót ogłoszenia</div>
    <div class="summary-box">{_e(ann.summary)}</div>

    <details>
      <summary>Pokaż pełne szczegóły (treść pobrana ze strony)</summary>
      <div class="details-content">{_e(details_text)}</div>
    </details>
  </div>
</div>"""


def generate_html_report(
    announcements: List[Announcement],
    cutoff_date: Optional[date] = None,
) -> str:
    """
    Buduje i zwraca pełny raport jako HTML.

    Parametry
    ----------
    announcements : list[Announcement]
        Lista ogłoszeń (już przefiltrowana przez wywołującego).
    cutoff_date : date | None
        Data odcięcia użyta do filtrowania – pokazywana w nagłówku.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    count = len(announcements)

    cutoff_info = (
        f"Wyświetlane są wyłącznie ogłoszenia opublikowane po "
        f"<strong>{cutoff_date.strftime('%d.%m.%Y')}</strong> "
        f"(ostatnie 3 miesiące od dnia dzisiejszego)."
        if cutoff_date
        else ""
    )
    date_unknown_count = sum(1 for a in announcements if not a.date_parsed)

    cards_html = "".join(_render_card(i + 1, ann) for i, ann in enumerate(announcements))

    if not announcements:
        cards_html = """
<div class="empty">
  Brak ogłoszeń spełniających kryteria daty.<br>
  <small>Spróbuj ponownie lub dostosuj zapytania w pliku <code>scraper.py</code>.</small>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ogłoszenia – Członek Rady Nadzorczej</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="container">

  <header>
    <h1>Ogłoszenia na stanowisko Członka Rady Nadzorczej</h1>
    <div class="meta">
      Data wygenerowania: <strong>{now_str}</strong> &nbsp;|&nbsp;
      Znaleziono ogłoszeń: <strong>{count}</strong>
      <span class="badge">HTML</span>
      <br>
      Źródło danych: DuckDuckGo (region: pl-pl) + bezpośrednie pobieranie stron
    </div>
  </header>

  <div class="notice">
    <strong>Uwaga metodyczna:</strong> Wyniki obejmują wyłącznie ogłoszenia dotyczące
    stanowiska <em>członka rady nadzorczej</em>. Ogłoszenia na stanowiska zarządcze
    (np. członek zarządu, prezes zarządu) zostały odfiltrowane.
  </div>

  {f'<div class="filter-info">🗓 <strong>Filtr daty:</strong> {cutoff_info}' +
   (f' Ogłoszenia bez rozpoznanej daty: <strong>{date_unknown_count}</strong> (oznaczone żółto).' if date_unknown_count else '') +
   '</div>' if cutoff_info else ''}

  {cards_html}

  <footer>
    Raport wygenerowany automatycznie &nbsp;·&nbsp; {now_str}
    &nbsp;·&nbsp; Projekt RN &nbsp;·&nbsp; Dane: DuckDuckGo / ddgs
  </footer>

</div>
</body>
</html>"""
