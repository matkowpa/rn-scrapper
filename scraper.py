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
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # fallback to old name

logger = logging.getLogger(__name__)

# Lista bezpośrednich źródeł (BIP / ministerstwa / spółki SP) – patrz sources.py
try:
    from sources import SOURCES
except ImportError:  # pozwól na import modułu jako pakiet
    try:
        from .sources import SOURCES
    except ImportError:
        SOURCES = []


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
        'ogłoszenie konkurs członek rady nadzorczej site:gov.pl',
    # Dynamiczne odkrywanie oferowanego w BIP-ach gmin/powiatow
    # (pełna lista jednostek nie jest statycznie dostępna).
    'site:bip.gov.pl ogłoszenie nabór członek rady nadzorczej',
    'site:bip.gov.pl konkurs członek rady nadzorczej kandydatów',
]

# ---------------------------------------------------------------------------
# Wykrywanie odnośników do naborów NA STRONACH ŹRÓDŁOWYCH (whitelist)
# Tekst kotwicy musi wskazywać AKTYWNY nabór/konkurs i dotyczyć rady nadzorczej.
# ---------------------------------------------------------------------------

RECRUITMENT_LINK_RE = re.compile(
    r"nab[oó]r|konkurs|rekrutacj|kandydat|ogłoszen|zgłoszen", re.IGNORECASE
)

RAD_NADZORCZA_RE = re.compile(
    r"rad(?:y|a|ie|ą)?\s+nadzorcz|nadzorcz", re.IGNORECASE
)

# Domeny urzędowe, których treść jest z definicji wiarygodna: link
# „Ogłoszenie o naborze … członków rady nadzorczej" zamieszczony przez urząd /
# spółkę SP NIE wymaga dodatkowego wezwania do działania (CV, termin), bo
# sam tytuł stanowi ogłoszenie. Obowiązuje tam tylko kontrola roku i fraz
# dyskwalifikujących.
OFFICIAL_DOMAIN_SUFFIXES = (
    "gov.pl",
)


def _is_official_domain(domain: str) -> bool:
    """True dla domen urzędowych (np. *.bip.gov.pl, *.gov.pl)."""
    d = (domain or "").lower()
    return d.endswith(OFFICIAL_DOMAIN_SUFFIXES)

# Serwisy agregujące / reklamowe – wyniki z nich NIE są realnymi ogłoszeniami
# o naborach (JOOBLE i podobne to agregatory ofert / reklamy serwisów rekrutacyjnych).
# Dopasowanie przez podciąg w domenie; celowo bez generycznych słów (np. "kariera"),
# by nie odcinać oficjalnych stron BIP.
BLOCKED_DOMAINS = (
    "jooble",        # agregator / reklamy
    "pracuj.pl",     # portal ofert
    "pracujw.pl",
    "indeed",        # globalny agregator
    "linkedin",      # sieć / oferty spons
    "careerjet", "monster.com", "neuvoo", "adzuna",
    "olx.pl",        # ogłoszenia drobne
    "career",        # tylko gdy w kontekście "career." (portale ofert)
    "youtube",       # filmy o karierze, nie ogłoszenia
    "lex.pl",        # bazy aktów prawnych – nigdy nie zawierają ogłoszeń naboru
    "cire.pl",       # serwis branżowy z artykułami, nie ogłoszeniami
)

# Frazy wskazujące, że mamy do czynienia z ARTYKUŁEM / poradnikiem / analizą prawniczą /
# omówieniem tematu rad nadzorczych, a NIE z realnym ogłoszeniem o nabor/rekrutacji.
# (np. wyniki z lex.pl, portali prawnych, blogów)
ARTICLE_OR_LEGAL_PHRASES = [
    "wyjaśniamy", "wyjaśniam", "poradnik",
    "jak zostać", "co robi rada", "jak powstaje",
    "wszystko o", "przewodnik", "na czym polega",
    "opisującą", "opisuje", "o tym czym jest",
    "granice odpowiedzialności", "badanie",
    "nowelizacja", "już od", "obowiązki członka", "prawa i obowiązki",
    "jakie kompetencje", "kompetencje rady", "rola rady",
    "analiza", "ekspert", "komentarz", "opinia",
    "poruszyliśmy", "kancelaria",
    "stan prawny",
]

# Frazy wskazujące na treści EDUKACYJNE / egzaminacyjne (np. kursy, testy, certyfikaty),
# a nie ogłoszenia o nabor na członka rady nadzorczej.
EXAM_OR_EDU_PHRASES = [
    "egzamin", "test kwalifikacyjny", "test", "certyfikat",
    "kurs", "szkolenie dla", "praktyka", "program",
    "aktualna", "przykładowe",
]

# Frazy sygnalizujące, że ogłoszenie/poszukiwania już się zakończyły (nieaktualne)
# lub że strona jest zwykłą stroną-przykład, a nie żywym naborem.
STALE_OR_CLOSED_PHRASES = [
    "zakończył się", "zakończył się nabór", "zakończono",
    "minął termin", "upłynął termin", "termin minął",
    "nabór zakończony", "rekrutacja zakończona",
    "nieaktualne", "usunięto ogłoszenie",
    "nie aktualne", "ostateczny termin",
]

# Reklamy serwisów rekrutacyjnych – typowe frazy marketingowe agregatorów (np. JOOBLE).
# Uwaga: świadomie NIE umieszczamy tu słowa "plikuj", bo występuje w prawdziwych
# ogłoszeniach BIP ("plikuj" / "aplikacja") – mogłoby to odrzucać ważne nabory.
AD_MARKETING_PHRASES = [
    "serwisy pracy", "portale pracy", "zobacz więcej ofert",
    "setki ofert", "zweryfikowany pracodawca",
    "praca w branży", "oferta z portalu",
]

DISQUALIFYING_PHRASES = [
    # Stanowiska kierownicze NIErzad nadzorcza
    "członek zarządu",
    "członków zarządu",  # liczba mnoga
    "prezes zarządu",
    "dyrektor zarządzający",
    "nabór na prezesa",
    "konkurs na prezesa",
    "wiceprezes zarządu",
    "stanowisko prezesa",
    "prokurent",
    # Artykuły / prawnie / poradniki / analizy (np. lex.pl)
    *ARTICLE_OR_LEGAL_PHRASES,
    # Treści egzaminacyjne / edukacyjne
    *EXAM_OR_EDU_PHRASES,
    # Nieaktualne / zakończone
    *STALE_OR_CLOSED_PHRASES,
    # Reklmy serwisów
    *AD_MARKETING_PHRASES,
]

# Frazy wymagane – wynik musi zawierać co najmniej jedną (o radzie nadzorczej)
REQUIRED_PHRASES = [
    "rada nadzorcza",
    "rady nadzorczej",
    "radzie nadzorczej",
    "rady nadzorcz",   # pokrywa odmiany: nadzorczą, nadzorczej itp.
    "nadzorcz",        # szeroki fallback
]

# Frazy wymagane – aby wynik NAPRAWDĘ dotyczył AKTYWNEGO na boru / poszukiwania kandydatów
# (a nie artykułu o radach nadzorczych czy omówienia przepisów).
# Musi wystąpić przynajmniej jedna z nich, by wynik został zaakceptowany.
RECRUITMENT_PHRASES = [
    "nabór", "naboru", "nabory",
    "rekru",           # rekrutacja / rekrutujemy
    "kandydat", "kandydaci", "kandydatów", "kandydata",
    "poszukuje", "poszukujemy", "poszukiwany",
    "ogłoszenie o naborze", "ogłasza nabór",
    "konkurs na", "konkurs o",
    "zaprasza", "zaprasza do",
    "wyłonienie", "wyłanian",
    "obsadzenia", "obsadzili",
    "zgłoszenie kandydatury", "zgłaszanie kandydatów",
    "aplik",           # aplikuj / aplikację
    "ponowny nabór", "otwarty nabór",
]

# Frazy SILNEGO wezwania do działania – charakterystyczne dla PRAWDZIWEGO
# ogłoszenia (organ wprost zaprasza do aplikowania i wskazuje termin/formę).
# Artykuły prasowe, akty prawne i komunikaty opisujące procedury ich NIE mają.
# Wynik musi zawierać co najmniej jedną taką frazę, aby został zaakceptowany.
STRONG_ACTION_PHRASES = [
    "zaprasza do składania",          # "…zaprasza do składania zgłoszeń"
    "składania zgłoszeń",
    "składanie zgłoszeń",
    "zgłoszenia kandydatur",
    "przesłać aplikację",
    "przesyłania aplikacji",
    "należy przesłać",
    "aplikacje należy",
    "kandydatury należy",
    "termin składania",
    "składać kandydatury",
    "w terminie do",
    "do dnia",
    "cv",
    "list motywacyjny",
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


_LABEL_DATE_RE = re.compile(
    r"(?:data\s+publikacji|opublikowano|data\s+og[łl]oszenia"
    r"|data\s+dodania|dodano|utworzono|wytworzono|data\s+wydania"
    r"|wpisano\s+do\s+bip)",
    re.IGNORECASE,
)

_META_DATE_FIELDS = (
    ("property", "article:published_time"),
    ("property", "og:published_time"),
    ("name", "pubdate"),
    ("name", "date"),
    ("name", "dc.date"),
    ("itemprop", "datePublished"),
)


def _clean_iso(value: str) -> Optional[str]:
    """'2026-08-12T09:30:00+02:00' -> '2026-08-12'; None gdy brak roku."""
    m = re.search(r"\b(20[0-3]\d)-(\d{2})-(\d{2})", value)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    return None


def _extract_publication_date(soup, full_text: str) -> Optional[str]:
    """
    Wyciąga DATĘ PUBLIKACJI ogłoszenia (a nie dowolną datę z treści,
    np. termin składania aplikacji) – używane do kolumny „Data ogłoszenia".

    Kolejność pewności:
      1. metatagi (article:published_time, datePublished, pubdate…),
      2. element <time datetime> lub tekst <time>,
      3. etykieta przed datą („Data publikacji: 12.08.2026", „Opublikowano …"),
      4. None → wywołujący spada na ogólną heurystykę pierwszej daty.
    """
    # 1) Metatagi
    for attr, name in _META_DATE_FIELDS:
        tag = soup.find("meta", attrs={attr: name})
        if tag:
            content = (tag.get("content") or "").strip()
            cleaned = _clean_iso(content)
            if cleaned:
                return cleaned

    # 2) <time>
    time_tag = soup.find("time")
    if time_tag:
        candidate = (time_tag.get("datetime") or "").strip() \
            or time_tag.get_text(" ", strip=True)
        cleaned = _clean_iso(candidate) or _extract_date(candidate)
        if cleaned:
            return cleaned

    # 3) Etykieta bezpośrednio przed datą
    m = _LABEL_DATE_RE.search(full_text)
    if m:
        window = full_text[m.start():m.start() + 60]
        labelled = _extract_date(window)
        if labelled:
            return labelled
    return None



def _has_stale_years(title: str, text: str = "") -> bool:
    """
    Heurystyka przeterminowanych ogłoszeń (problem: DDG zwracał archiwalne
    nabory z 2018/2021 oraz komunikaty z 2013 r.).

    Zasada: patrzysz na tytuł + początek treści (pierwsze 1200 znaków).
      * jeśli występuje JAKIKOLWIEK rok >= (rok bieżący - 1) → AKTUALNE,
      * jeśli NIE ma żadnego świeżego roku, ale jest starszy (np. 2013/2021)
        → PRZETERMINOWANE,
      * brak jakichkolwiek lat 20xx → nie rozstrzyga (False).

    Tylko rok w tytule nie decyduje samodzielnie — komunikaty sprzed lat często
    mają bezdatne tytuły, a data kryje się w treści.
    """
    current_year = datetime.now().year
    window = f"{title} {(text or '')[:1200]}"
    years = [int(y) for y in re.findall(r"\b(20[0-3]\d)\b", window)]
    if not years:
        return False
    newest = max(years)
    if newest < current_year - 1:
        logger.debug("Stale (najnowszy rok %d < %d): %.60s",
                     newest, current_year - 1, title)
        return True
    return False


def _is_relevant(
    title: str,
    snippet: str,
    details: Optional[str] = None,
    domain: Optional[str] = None,
    trusted: bool = False,
) -> bool:
    """
    Zwraca True tylko dla REALNYCH, AKTUALNYCH ogłoszeń o nabor na członka rady
    nadzorczej (a nie reklam agregatorów, artykułów prawniczych, treści o
    egzaminach czy nieaktualnych ogłoszeń).

    Kryteria (wszystkie muszą być spełnione):
      * wynik nie pochodzi z domen-agregatorów/reklam (BLOCKED_DOMAINS),
      * tekst musi dotyczyć rady nadzorczej (REQUIRED_PHRASES),
      * tekst musi zawierać frazy AKTYWNEGO naboru/rekrutacji (RECRUITMENT_PHRASES),
      * tekst musi zawierać SILNE WEZWANIE DO DZIAŁANIA (STRONG_ACTION_PHRASES) –
        to odróżnia realne ogłoszenie od artykułu/aktu prawnego/komunikatu,
      * tekst nie może zawierać żadnej frazy dyskwalifikującej (DISQUALIFYING_PHRASES).

    Sprawdzamy łącznie tytuł + snippet z wyszukiwarki oraz (jeśli podano)
    pełną treść pobranej strony (details).
    """
    if domain:
        d = domain.lower()
        if any(b in d for b in BLOCKED_DOMAINS):
            return False

    combined = f"{title} {snippet}".lower()
    if details:
        combined = f"{combined}\n{details}".lower()

    # Musi dotyczyć tematu rady nadzorczej
    if not any(phrase in combined for phrase in REQUIRED_PHRASES):
        return False

    # Musi dotyczyć AKTYWNEGO naboru / poszukiwania kandydatów
    if not any(phrase in combined for phrase in RECRUITMENT_PHRASES):
        return False

    # Musi zawierać silne wezwanie do działania (odróżnia ogłoszenie od
    # artykułu, aktu prawnego czy komunikatu opisującego procedurę).
    # Domeny urzędowe (*.gov.pl) są zwolnione z TEGO kryterium – sam link
    # „ogłoszenie o naborze" na BIP jest formalnym ogłoszeniem.
    if not trusted and not any(
        phrase in combined for phrase in STRONG_ACTION_PHRASES
    ):
        return False

    # Nie może zawierać fraz dyskwalifikujących
    if any(phrase in combined for phrase in DISQUALIFYING_PHRASES):
        return False

    return True


def _fetch_html(url: str, timeout: int = 12) -> Optional[str]:
    """Pobiera HTML strony. Zwraca None przy błędzie.
    Przy błędach SSL (częste na stronach BIP) ponawia próbę bez weryfikacji.
    """
    import urllib3
    try:
        resp = requests.get(url, headers=HEADERS,
                            timeout=(6, timeout), verify=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.exceptions.SSLError:
        # Wiele polskich stron BIP ma nieprawidłowe certyfikaty – próba bez weryfikacji
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(url, headers=HEADERS,
                                timeout=(6, timeout), verify=False)
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
    date = (
        _extract_publication_date(soup, full_text)
        or _extract_date(full_text)
    )

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
# Pobieranie BEZPOŚREDNIO ze źródeł whitelist (BIP / ministerstwa / spółki)
# ---------------------------------------------------------------------------


def collect_from_sources(
    max_links_per_source: int = 4,
    delay_between_results: float = 0.8,
) -> list:
    """
    Czyta strony z WHITELISTY źródeł (sources.py) i wykrywa odnośniki
    do naborów na członków rad nadzorczych bezpośrednio na ich stronach.

    To obejście problemu DDG: agregatory (jooble), artykuły (lex.pl) i stare
    wyniki nie mają tu dostępu, bo czytamy wyłącznie oficjalne domeny.
    Kandydaci przechodzą potem TĘ SAMĄ ścieżkę walidacji co wyniki DDG
    (_is_relevant + _has_stale_years), więc jakość jest spójna.

    Zwraca listę obiektów Announcement (bez deduplikacji z DDG – robi to
    search_and_scrape).
    """
    announcements: list = []

    for src in SOURCES:
        logger.info("[Źródło %s] %s → %s", src.id, src.name, src.url)
        html = _fetch_html(src.url)
        if not html:
            logger.warning("[Źródło %s] brak odpowiedzi – pomijam", src.id)
            continue

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as exc:  # parsowanie się nie wykona
            logger.warning("[Źródło %s] błąd parsowania: %s", src.id, exc)
            continue

        candidates = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)
            if not text or len(text) < 12:
                continue
            text_lower = text.lower()
            if not RECRUITMENT_LINK_RE.search(text_lower):
                continue
            if not RAD_NADZORCZA_RE.search(text_lower):
                continue

            href = urljoin(src.url, a["href"].strip())
            if not href.startswith("http"):
                continue
            if href.lower().split("?")[0].endswith(".pdf"):
                # Ogłoszenia PDF nie są parsowalne z pewnością – pomijamy,
                # zwykle ten sam nabór ma wersję HTML/aktualność na stronie.
                continue
            candidates.append((text, href))
            if len(candidates) >= max_links_per_source:
                break

        if not candidates:
            logger.info("[Źródło %s] brak pasujących odnośników", src.id)
            continue

        for anchor_text, url in candidates:
            time.sleep(delay_between_results)
            domain = urlparse(url).netloc
            page_html = _fetch_html(url)

            if page_html:
                parsed = _parse_page(page_html, anchor_text)
                ann_title = parsed["title"] or anchor_text
                details_text = parsed["details"]

                if not _is_relevant(
                    ann_title, anchor_text,
                    details=details_text, domain=domain,
                    trusted=_is_official_domain(domain),
                ):
                    logger.debug("[Źródło %s] odrzucono treść: %.60s",
                                 src.id, ann_title)
                    continue
                if _has_stale_years(ann_title, details_text):
                    logger.debug("[Źródło %s] odrzucono (stare): %.60s",
                                 src.id, ann_title)
                    continue

                raw_date = parsed["date"] or _extract_date(anchor_text)
                announcements.append(Announcement(
                    title=ann_title,
                    url=url,
                    source_domain=domain,
                    date=raw_date,
                    date_parsed=parse_date_str(raw_date),
                    summary=anchor_text[:600],
                    details=details_text,
                ))
            else:
                # Strony szczegółów nie pobrano – dopuść tylko, jeśli SAM tekst
                # kotwicy przejdzie pełne filtrowanie (bardzo konserwatywnie).
                if _is_relevant(anchor_text, anchor_text, domain=domain,
                                trusted=_is_official_domain(domain)) \
                        and not _has_stale_years(anchor_text):
                    raw_date = _extract_date(anchor_text)
                    announcements.append(Announcement(
                        title=anchor_text,
                        url=url,
                        source_domain=domain,
                        date=raw_date,
                        date_parsed=parse_date_str(raw_date),
                        summary=anchor_text[:600],
                        details=anchor_text,
                    ))

        logger.info("[Źródło %s] zaakceptowano ogłoszeń: %d",
                    src.id, len(announcements))

    return announcements


# ---------------------------------------------------------------------------
# Główna funkcja
# ---------------------------------------------------------------------------


def search_and_scrape(
    max_results_per_query: int = 8,
    delay_between_results: float = 1.2,
    delay_between_queries: float = 3.0,
    use_direct_sources: bool = True,
) -> list:
    """
    Przeszukuje DuckDuckGo zapytaniami ukierunkowanymi na rady nadzorcze,
    pobiera treść stron i zwraca listę obiektów Announcement.

    Faza 1 (nowość): bezpośrednie czytanie whitelisty źródeł BIP/portali
    (`use_direct_sources`) — najwyższa wiarygodność.
    Faza 2: klasyczne wyszukiwanie DDG jako uzupełnienie (agregatory domenowo
    blokowane; przeterminowane heurystyką roku).

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

    # ------------------------------------------------------------------
    # FAZA 1 – bezpośrednie czytanie whitelisty źródeł (BIP / ministerstwa
    # / spółki SP). Wyniki mają najwyższą wiarygodność i wchodzą do puli
    # przed wynikami wyszukiwarki; duplikaty są odsiewane przez seen_urls.
    # ------------------------------------------------------------------
    if use_direct_sources and SOURCES:
        try:
            logger.info("Faza 1: bezpośrednie źródła (%d pozycji)…", len(SOURCES))
            for ann in collect_from_sources(
                delay_between_results=delay_between_results,
            ):
                if ann.url in seen_urls:
                    continue
                seen_urls.add(ann.url)
                announcements.append(ann)
            logger.info("Faza 1 zakończona: %d ogłoszeń ze źródeł bezpośrednich.",
                        len(announcements))
        except Exception as exc:
            logger.error("Błąd fazy źródeł bezpośrednich: %s", exc)

    # ------------------------------------------------------------------
    # FAZA 2 – DuckDuckGo jako uzupełnienie
    # ------------------------------------------------------------------
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

            domain = url.split("/")[2] if "//" in url else url

            # Odrzuć od razu domeny-agregatory/reklamy (np. JOOBLE)
            if any(b in domain.lower() for b in BLOCKED_DOMAINS):
                logger.debug("Pomijam (domena zablokowana): %s", domain)
                continue

            logger.info("Przetwarzam: %.70s", title)

            # Pobierz stronę
            html = _fetch_html(url)
            if html:
                parsed = _parse_page(html, snippet)
                ann_title = parsed["title"] or title
                # Rygorystyczna weryfikacja także na pełnej treści strony
                if not _is_relevant(
                    ann_title, snippet,
                    details=parsed["details"], domain=domain,
                    trusted=_is_official_domain(domain),
                ):
                    logger.debug("Pomijam (pełna treść nieistotna): %.60s", title)
                    continue
                if _has_stale_years(ann_title,
                                    (parsed["details"] or "")[:600]):
                    logger.debug("Pomijam (przeterminowane): %.60s", title)
                    continue
                raw_date = (
                    parsed["date"]
                    or _extract_date(parsed["title"])
                    or _extract_date(snippet)
                )
                ann = Announcement(
                    title=ann_title,
                    url=url,
                    source_domain=domain,
                    date=raw_date,
                    date_parsed=parse_date_str(raw_date),
                    summary=snippet[:600],
                    details=parsed["details"],
                )
            else:
                # Fallback – tylko tekst ze snippetu DDG (bez pobranej strony)
                if not _is_relevant(title, snippet, domain=domain,
                                    trusted=_is_official_domain(domain)):
                    logger.debug("Pomijam (nieistotne): %.60s", title)
                    continue
                raw_date = _extract_date(snippet)
                ann = Announcement(
                    title=title,
                    url=url,
                    source_domain=domain,
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
