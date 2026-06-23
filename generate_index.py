"""
Generates docs/index.html — an archive page listing all historical reports.
Run automatically by the GitHub Actions workflow after each scrape.
"""
from pathlib import Path
from datetime import datetime


def main():
    reports_dir = Path("docs/reports")
    reports = sorted(reports_dir.glob("*.html"), reverse=True)

    rows = []
    for r in reports:
        try:
            dt = datetime.strptime(r.stem, "%Y%m%d_%H%M%S")
            label = dt.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            label = r.stem
        rows.append(f'<li><a href="reports/{r.name}">{label}</a></li>')

    items_html = "\n    ".join(rows) if rows else "<li>Brak raportów.</li>"

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rada Nadzorcza – Raporty</title>
  <style>
    body {{ font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; color: #333; }}
    h1 {{ font-size: 1.5rem; }}
    p.info {{ color: #666; font-size: 0.9rem; }}
    ul {{ padding-left: 1.2em; }}
    li {{ margin: 8px 0; font-size: 1rem; }}
    a {{ color: #1a73e8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Członek Rady Nadzorczej – Historia raportów</h1>
  <p class="info">Raporty generowane automatycznie 3x dziennie (ok. 08:00, 13:00, 18:00 PL).<br>
  Kliknij wybrany raport, aby zobaczyć ogłoszenia z danego dnia.</p>
  <ul>
    {items_html}
  </ul>
</body>
</html>"""

    out = Path("docs/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"index.html updated — {len(reports)} raport(ów).")


if __name__ == "__main__":
    main()
