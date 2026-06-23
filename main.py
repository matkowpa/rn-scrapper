# -*- coding: utf-8 -*-
"""
Punkt wejścia aplikacji.

Uruchomienie:
    python main.py                        # domyślnie: ostatnie 3 miesiące
    python main.py --date 2026-04-01      # ogłoszenia od 1 kwietnia 2026
    python main.py --months 6             # ogłoszenia z ostatnich 6 miesięcy

Wygenerowany raport zapisywany jest w katalogu roboczym jako:
    raport_rada_nadzorcza_YYYYMMDD_HHMMSS.html
"""

import argparse
import logging
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pathlib import Path

from scraper import search_and_scrape
from report_html import generate_html_report

# ---------------------------------------------------------------------------
# Konfiguracja logowania
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parsowanie argumentów CLI
# ---------------------------------------------------------------------------

def _parse_args() -> date:
    """
    Zwraca datę odcięcia na podstawie argumentów wiersza poleceń.

    --date YYYY-MM-DD   ustaw konkretną datę graniczną
    --months N          cofnij się o N miesięcy od dziś (domyślnie: 1)
    """
    parser = argparse.ArgumentParser(
        description="Wyszukiwarka ogłoszeń BIP – Członek Rady Nadzorczej"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Data odcięcia (format: YYYY-MM-DD). Tylko ogłoszenia od tej daty.",
    )
    group.add_argument(
        "--months",
        type=int,
        default=1,
        metavar="N",
        help="Liczba miesięcy wstecz od dziś (domyślnie: 1).",
    )
    args = parser.parse_args()

    today = date.today()
    if args.date:
        try:
            cutoff = date.fromisoformat(args.date)
        except ValueError:
            parser.error(f"Nieprawidłowy format daty: '{args.date}'. Użyj YYYY-MM-DD.")
        if cutoff > today:
            parser.error(f"Data odcięcia ({cutoff}) nie może być w przyszłości.")
    else:
        cutoff = today - relativedelta(months=args.months)

    return cutoff


# ---------------------------------------------------------------------------
# Główna logika
# ---------------------------------------------------------------------------


def main() -> None:
    cutoff_date = _parse_args()
    today = date.today()

    logger.info("=" * 60)
    logger.info("Wyszukiwarka ogłoszeń – CZŁONEK RADY NADZORCZEJ")
    logger.info("Filtr daty: od %s do %s", cutoff_date.strftime("%d.%m.%Y"), today.strftime("%d.%m.%Y"))
    logger.info("=" * 60)

    # Wyszukaj i przescrapuj ogłoszenia
    all_announcements = search_and_scrape(
        max_results_per_query=8,
        delay_between_results=1.2,
        delay_between_queries=3.0,
    )

    # Zastosuj filtr daty
    def _after_cutoff(ann) -> bool:
        if ann.date_parsed is None:
            return True  # brak daty – zachowaj (nie można wykluczyć)
        return ann.date_parsed >= cutoff_date

    filtered = [a for a in all_announcements if _after_cutoff(a)]
    excluded = len(all_announcements) - len(filtered)
    logger.info(
        "Po filtrze daty: %d ogłoszeń (odrzucono %d starszych niż %s)",
        len(filtered), excluded, cutoff_date.strftime("%d.%m.%Y"),
    )

    if not filtered:
        logger.warning("Nie znaleziono ogłoszeń po dacie %s.", cutoff_date.strftime("%d.%m.%Y"))

    # Generuj raport HTML
    html_report = generate_html_report(filtered, cutoff_date=cutoff_date)

    # Zapisz do pliku
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"raport_rada_nadzorcza_{timestamp}.html")
    output_path.write_text(html_report, encoding="utf-8")

    logger.info("Raport HTML zapisany: %s", output_path.resolve())

    print("\n" + "=" * 60)
    print(f"Źródło:                            Polski internet (wszystkie źródła)")
    print(f"Data odcięcia:                     {cutoff_date.strftime('%d.%m.%Y')}")
    print(f"Wszystkich ogłoszeń znalezionych:  {len(all_announcements)}")
    print(f"Po filtrze daty:                   {len(filtered)}")
    print(f"Odrzucono (za stare / brak daty*): {excluded}")
    print(f"  * ogłoszenia bez daty są zachowywane")
    print(f"Plik raportu: {output_path.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
