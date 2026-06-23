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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Inter', 'Segoe UI', sans-serif;
    background: #f0f4f8;
    color: #1a202c;
    min-height: 100vh;
}

.container { max-width: 900px; margin: 0 auto; padding: 0 16px 48px; }

/* ── Header ──────────────────────────────────────── */
header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    color: #fff;
    padding: 36px 32px 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
header::before {
    content: '';
    position: absolute;
    inset: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.header-back {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: rgba(255,255,255,0.75);
    text-decoration: none;
    font-size: 0.82rem;
    font-weight: 500;
    margin-bottom: 16px;
    transition: color 0.15s;
}
.header-back:hover { color: #fff; }
header h1 {
    position: relative;
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.4px;
    margin-bottom: 10px;
}
.header-meta {
    position: relative;
    font-size: 0.875rem;
    opacity: 0.85;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
}
.header-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(255,255,255,0.15);
    border-radius: 99px;
    padding: 3px 12px;
    font-size: 0.8rem;
    font-weight: 500;
}
.chip-green { background: rgba(34,197,94,0.25); color: #bbf7d0; }

/* ── Info banners ─────────────────────────────────── */
.banner {
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 16px;
    font-size: 0.875rem;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}
.banner-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 1px; }
.banner-yellow { background: #fefce8; border: 1px solid #fde68a; color: #713f12; }
.banner-blue   { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }

/* ── Section heading ──────────────────────────────── */
.section-heading {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #718096;
    margin: 28px 0 12px;
}

/* ── Announcement card ────────────────────────────── */
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    margin-bottom: 16px;
    overflow: hidden;
    transition: box-shadow 0.15s, border-color 0.15s;
}
.card:hover {
    box-shadow: 0 4px 24px rgba(37,99,235,0.10);
    border-color: #93c5fd;
}

.card-header {
    padding: 16px 20px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    border-bottom: 1px solid #f1f5f9;
}
.card-number {
    min-width: 32px;
    height: 32px;
    background: #eff6ff;
    color: #2563eb;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 700;
    flex-shrink: 0;
}
.card-title {
    flex: 1;
    font-size: 0.975rem;
    font-weight: 600;
    line-height: 1.45;
    color: #1a202c;
}
.card-title a {
    color: inherit;
    text-decoration: none;
}
.card-title a:hover { color: #2563eb; text-decoration: underline; }

.card-body { padding: 16px 20px; }

/* ── Metadata pills ───────────────────────────────── */
.meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 14px;
}
.meta-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 99px;
    padding: 4px 12px;
    font-size: 0.78rem;
    color: #4a5568;
}
.meta-pill strong { color: #1a202c; font-weight: 600; }

.date-badge {
    background: #f0fdf4;
    border-color: #86efac;
    color: #15803d;
}
.date-unknown {
    background: #fefce8;
    border-color: #fde68a;
    color: #92400e;
}

/* ── URL link ─────────────────────────────────────── */
.url-link {
    display: block;
    font-size: 0.78rem;
    color: #2563eb;
    word-break: break-all;
    margin-bottom: 14px;
    text-decoration: none;
    opacity: 0.8;
}
.url-link:hover { opacity: 1; text-decoration: underline; }

/* ── Summary ──────────────────────────────────────── */
.label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #a0aec0;
    margin-bottom: 6px;
}
.summary-box {
    background: #f8fafc;
    border-left: 3px solid #93c5fd;
    border-radius: 0 6px 6px 0;
    padding: 10px 14px;
    font-size: 0.875rem;
    font-style: italic;
    color: #4a5568;
    line-height: 1.65;
}

/* ── Expandable details ───────────────────────────── */
details { margin-top: 12px; }
summary {
    cursor: pointer;
    font-size: 0.82rem;
    font-weight: 600;
    color: #2563eb;
    padding: 6px 0;
    list-style: none;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 6px;
}
summary::before { content: "▶"; font-size: 0.65em; transition: transform 0.2s; }
details[open] summary::before { content: "▼"; }
.details-content {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px;
    margin-top: 8px;
    font-size: 0.82rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 400px;
    overflow-y: auto;
    color: #4a5568;
}

/* ── Empty state ──────────────────────────────────── */
.empty {
    text-align: center;
    padding: 60px 20px;
    color: #a0aec0;
    font-size: 1rem;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    margin-top: 16px;
}
.empty-icon { font-size: 2.5rem; display: block; margin-bottom: 12px; }

/* ── Footer ───────────────────────────────────────── */
footer {
    text-align: center;
    font-size: 0.78rem;
    color: #a0aec0;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #e2e8f0;
}
footer a { color: #2563eb; text-decoration: none; }
footer a:hover { text-decoration: underline; }
"""


def _e(text: str) -> str:
    """HTML escape."""
    return _html_lib.escape(str(text))


def _render_card(idx: int, ann: Announcement) -> str:
    date_label = ann.date or "brak daty"
    date_class = "meta-pill date-badge" if ann.date_parsed else "meta-pill date-unknown"

    details_lines = [ln.strip() for ln in ann.details.splitlines() if ln.strip()]
    details_text = "\n".join(details_lines[:60])
    if len(details_lines) > 60:
        details_text += "\n\n… (treść skrócona – odwiedź link po pełne ogłoszenie)"

    return f"""
<div class="card" id="ann-{idx}">
  <div class="card-header">
    <div class="card-number">{idx}</div>
    <div class="card-title">
      <a href="{_e(ann.url)}" target="_blank" rel="noopener">{_e(ann.title)}</a>
    </div>
  </div>
  <div class="card-body">
    <div class="meta-row">
      <span class="{date_class}">&#128197; {_e(date_label)}</span>
      <span class="meta-pill">&#127760; {_e(ann.source_domain)}</span>
    </div>
    <a class="url-link" href="{_e(ann.url)}" target="_blank" rel="noopener">&#128279; {_e(ann.url)}</a>
    <div class="label">Skrót ogłoszenia</div>
    <div class="summary-box">{_e(ann.summary)}</div>
    <details>
      <summary>Pokaż pełne szczegóły</summary>
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
  <span class="empty-icon">&#128269;</span>
  Brak ogłoszeń spełniających kryteria daty.<br>
  <small>Spróbuj ponownie lub dostosuj zapytania w pliku <code>scraper.py</code>.</small>
</div>"""

    filter_banner = ""
    if cutoff_info:
        unknown_note = (f" Ogłoszeń bez rozpoznanej daty: <strong>{date_unknown_count}</strong> (oznaczone żółto)."
                        if date_unknown_count else "")
        filter_banner = f'<div class="banner banner-blue"><span class="banner-icon">&#128197;</span><div><strong>Filtr daty:</strong> {cutoff_info}{unknown_note}</div></div>'

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ogłoszenia – Członek Rady Nadzorczej</title>
  <style>{_CSS}</style>
</head>
<body>

  <header>
    <a class="header-back" href="../index.html">&#8592; Powrót do listy raportów</a>
    <h1>&#128269; Ogłoszenia – Członek Rady Nadzorczej</h1>
    <div class="header-meta">
      <span class="header-chip">&#128197; {now_str}</span>
      <span class="header-chip chip-green">&#9679; {count} ogłoszeń</span>
      <span class="header-chip">&#127760; BIP, Google, Yahoo, Brave, Startpage</span>
    </div>
  </header>

  <div class="container">
    <div class="banner banner-yellow">
      <span class="banner-icon">&#9888;</span>
      <div><strong>Uwaga metodyczna:</strong> Wyniki obejmują wyłącznie ogłoszenia dotyczące stanowiska
      <em>członka rady nadzorczej</em>. Ogłoszenia zarządcze (zarząd, prezes) zostały odfiltrowane.</div>
    </div>

    {filter_banner}

    <div class="section-heading">Lista ogłoszeń ({count})</div>
    {cards_html}

    <footer>
      Raport wygenerowany automatycznie &nbsp;·&nbsp; {now_str} &nbsp;·&nbsp;
      <a href="../index.html">&#8592; Wszystkie raporty</a>
    </footer>
  </div>

</body>
</html>"""
