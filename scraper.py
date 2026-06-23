# -*- coding: utf-8 -*-
"""
Moduł wyszukiwania i scrapowania ogłoszeń na stanowisko członka rady nadzorczej.
Przeszukuje polski internet przy użyciu DuckDuckGo i pobiera szczegóły stron.
"""

import re
import time
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

import requests
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # fallback to old name

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Zapytania skierowane wyłącznie na ogłoszenia rad nadzorczych
# Uwaga: operator OR nie jest wspierany – używamy osobnych, prostych zapytań
SEARCH_QUERIES = [
    'nabór kandydatów na członka rady nadzorczej spółka ogłoszenie',
    'konkurs stanowisko członka rady nadzorczej ogłoszenie',
    'rada nadzorcza rekrutacja ogłoszenie spółka skarbu państwa 2026',
    'rady nadzorczej nabór ogłoszenie BIP 2025',
    'rady nadzorczej nabór ogłoszenie BIP 2026',
    'członek rady nadzorczej ogłoszenie nabór kandydatów spółka',
]

DISQUALIFYING_PHRASES = [
    "członek zarządu",
    "członków zarządu",  # liczba mnoga
    "prezes zarządu",
    "dyrektor zarządzający",
    "nabór na prezesa",
    "konkurs na prezesa",
    "wiceprezes zarządu",
    "stanowisko prezesa",
    "prokurent",
]

# Frazy wymagane – wynik musi zawierać co najmniej jedną
REQUIRED_PHRASES = [
    "rada nadzorcza",
    "rady nadzorczej",
    "radzie nadzorczej",
    "rady nadzorcz",   # pokrywa odmiany: nadzorczą, nadzorczej itp.
    "nadzorcz",        # szeroki fallback
]

# Polskie nazwy miesięcy do ekstrakcji daty
_MONTHS_PL = (
    "stycznia|lutego|marca|kwietnia|maja|czerwca|"
    "lipca|sierpnia|września|października|listopada|grudnia"
)

DATE_PATTERNS = [
    re.compile(
        rf"\d{{1,2}}\s+(?:{_MONTHS_PL})\s+\d{{4}}", re.IGNORECASE
    ),
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\d{1,2}\.\d{2}\.\d{4}"),
]

# ---------------------------------------------------------------------------
# Modele danych
# ---------------------------------------------------------------------------


# Mapa polskich nazw miesięcy → numer miesiąca
_PL_MONTHS: dict = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4,
    "maja": 5, "czerwca": 6, "lipca": 7, "sierpnia": 8,
    "września": 9, "października": 10, "listopada": 11, "grudnia": 12,
}


@dataclass
class Announcement:
    title: str
    url: str
    source_domain: str
    date: Optional[str]          # surowy tekst daty
    date_parsed: Optional[date]  # sparsowana data (do filtrowania)
    summary: str                 # skrót ze snippetu wyszukiwarki
    details: str                 # pełny tekst pobrany ze strony


# ---------------------------------------------------------------------------
# Funkcje pomocnicze
# ---------------------------------------------------------------------------


def _extract_date(text: str) -> Optional[str]:
    """Wyciąga pierwszą datę znalezioną w tekście jako surowy string."""
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None


def parse_date_str(raw: Optional[str]) -> Optional[date]:
    """
    Parsuje surowy string daty do obiektu date.
    Obsługuje formaty: '12 marca 2026', '2026-03-12', '12.03.2026'.
    Zwraca None gdy parsowanie niemożliwe.
    """
    if not raw:
        return None
    raw = raw.strip()
    # Format: '12 marca 2026'
    m = re.match(
        r"(\d{1,2})\s+(\S+)\s+(\d{4})", raw, re.IGNORECASE
    )
    if m:
        day, month_name, year = m.group(1), m.group(2).lower(), m.group(3)
        month_num = _PL_MONTHS.get(month_name)
        if month_num:
            try:
                return date(int(year), month_num, int(day))
            except ValueError:
                pass
    # Format: '2026-03-12'
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # Format: '12.03.2026'
    m = re.match(r"(\d{1,2})\.(\d{2})\.(\d{4})", raw)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


def _is_relevant(title: str, snippet: str) -> bool:
    """
    Zwraca True tylko gdy tekst dotyczy rady nadzorczej
    i NIE dotyczy zarządu ani innych stanowisk kierowniczych.
    """
    combined = f"{title} {snippet}".lower()

    # Musi zawierać frazę o radzie nadzorczej
    if not any(phrase in combined for phrase in REQUIRED_PHRASES):
        return False

    # Nie może być zdominowany przez frazy o zarządzie
    for phrase in DISQUALIFYING_PHRASES:
        if phrase in combined:
            return False

    return True


def _fetch_html(url: str, timeout: int = 12) -> Optional[str]:
    """Pobiera HTML strony. Zwraca None przy błędzie.
    Przy błędach SSL (częste na stronach BIP) ponawia próbę bez weryfikacji.
    """
    import urllib3
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.exceptions.SSLError:
        # Wiele polskich stron BIP ma nieprawidłowe certyfikaty – próba bez weryfikacji
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            logger.debug("Pobrano bez weryfikacji SSL: %s", url)
            return resp.text
        except Exception as exc2:
            logger.warning("Nie udało się pobrać (brak SSL) %s: %s", url, exc2)
            return None
    except Exception as exc:
        logger.warning("Nie udało się pobrać %s: %s", url, exc)
        return None


def _parse_page(html: str, fallback: str) -> dict:
    """
    Parsuje HTML i zwraca słownik z: title, date, details.
    Przy braku treści używa fallback (snippet DDG).
    """
    soup = BeautifulSoup(html, "lxml")

    # Usuń elementy niezwiązane z treścią
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Tytuł
    h1 = soup.find("h1")
    title_tag = soup.find("title")
    title = (h1.get_text(strip=True) if h1 else "") or (
        title_tag.get_text(strip=True) if title_tag else ""
    )

    # Pełny tekst strony do ekstrakcji daty
    full_text = soup.get_text(separator=" ", strip=True)
    date = _extract_date(full_text)

    # Główna treść – próbuj semantyczne tagi, potem body
    main_elem = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|tresc|ogloszenie", re.I))
        or soup.find(class_=re.compile(r"content|main|article|tresc|post", re.I))
        or soup.body
    )

    if main_elem:
        raw = main_elem.get_text(separator="\n", strip=True)
        # Kompresuj wielokrotne puste linie
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        details = raw[:2500] + ("…" if len(raw) > 2500 else "")
    else:
        details = fallback

    return {"title": title, "date": date, "details": details}


# ---------------------------------------------------------------------------
# Główna funkcja
# ---------------------------------------------------------------------------


def search_and_scrape(
    max_results_per_query: int = 8,
    delay_between_results: float = 1.2,
    delay_between_queries: float = 3.0,
) -> list:
    """
    Przeszukuje DuckDuckGo zapytaniami ukierunkowanymi na rady nadzorcze,
    pobiera treść stron i zwraca listę obiektów Announcement.

    Parametry
    ----------
    max_results_per_query : int
        Maksymalna liczba wyników na jedno zapytanie DDG.
    delay_between_results : float
        Przerwa (s) między pobieraniem kolejnych stron.
    delay_between_queries : float
        Przerwa (s) między kolejnymi zapytaniami DDG.
    """
    seen_urls: set = set()
    announcements: list = []

    for query in SEARCH_QUERIES:
        logger.info("Zapytanie DDG: %s", query)

        try:
            with DDGS() as ddgs:
                raw_results = list(
                    ddgs.text(
                        query,
                        region="pl-pl",
                        safesearch="off",
                        max_results=max_results_per_query,
                    )
                )
        except Exception as exc:
            logger.error("Błąd wyszukiwarki DDG: %s", exc)
            raw_results = []

        for result in raw_results:
            url: str = result.get("href", "")
            title: str = result.get("title", "")
            snippet: str = result.get("body", "")

            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            # Filtr trafności
            if not _is_relevant(title, snippet):
                logger.debug("Pomijam (nieistotne): %.60s", title)
                continue

            logger.info("Przetwarzam: %.70s", title)

            # Pobierz stronę
            html = _fetch_html(url)
            if html:
                parsed = _parse_page(html, snippet)
                raw_date = parsed["date"] or _extract_date(snippet)
                ann = Announcement(
                    title=parsed["title"] or title,
                    url=url,
                    source_domain=url.split("/")[2] if "//" in url else url,
                    date=raw_date,
                    date_parsed=parse_date_str(raw_date),
                    summary=snippet[:600],
                    details=parsed["details"],
                )
            else:
                # Fallback – tylko dane ze snippetu DDG
                raw_date = _extract_date(snippet)
                ann = Announcement(
                    title=title,
                    url=url,
                    source_domain=url.split("/")[2] if "//" in url else url,
                    date=raw_date,
                    date_parsed=parse_date_str(raw_date),
                    summary=snippet[:600],
                    details=snippet,
                )

            announcements.append(ann)
            time.sleep(delay_between_results)

        time.sleep(delay_between_queries)

    logger.info("Łącznie znaleziono %d ogłoszeń.", len(announcements))
    return announcements
