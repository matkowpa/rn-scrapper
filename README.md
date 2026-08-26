# rn-scrapper — Monitor naborów na członków rad nadzorczych

Automatyczny scraper ogłoszeń o naborach / konkursach na stanowisko
**członka rady nadzorczej** (spółki Skarbu Państwa, spółki komunalne,
ministerstwa). Raport jest generowany automatycznie i publikowany jako strona.

## 🌐 Strona z raportami

**https://matkowpa.github.io/rn-scrapper/**

Na stronie głównej znajduje się lista wszystkich dotychczasowych raportów;
każdy raport zawiera ogłoszenia wraz z linkami do źródeł (BIP / strony spółek),
datami publikacji i skrótami treści. Poszczególne raporty są pod ścieżką
`docs/reports/<YYYYMMDD_HHMMSS>.html`.

## Jak to działa?

1. **GitHub Actions** uruchamia scraper cyklicznie wg harmonogramu (`cron`)
   oraz ręcznie (*Actions → Scrape – Rada Nadzorcza → Run workflow*).
2. Scraper pobiera wyniki z **DuckDuckGo (pl-pl)** oraz **bezpośrednio**
   ze zweryfikowanej listy źródeł (`sources.py`): ministerstwa (gov.pl),
   największe spółki Skarbu Państwa (ORLEN, PGE, TAURON, KGHM, Poczta Polska,
   BGK, GPW itd.), porty morskie.
3. Wyniki przechodzą wielostopniową filtrację jakości:
   - blokada agregatorów i serwisów reklamowych (jooble, pracuj.pl…),
   - odrzucanie artykułów prawnych/blogów (lex.pl, cire.pl) i treści
     egzaminacyjnych,
   - wymagane frazy aktywnego naboru („zaprasza do składania zgłoszeń"…),
   - heurystyka przeterminowanych ogłoszeń (lata 2018/2021 → odrzucone),
   - dla domen urzędowych `*.gov.pl` – uproszczona walidacja (sam link
     „ogłoszenie o naborze" na BIP jest wiarygodny).
4. Raport HTML trafia do `docs/reports/`, a indeks (`docs/index.html`)
   jest przebudowywany przez `generate_index.py`.
5. Zmiany są commitowane i pushowane → **GitHub Pages** publikuje stronę
   automatycznie (źródło: gałąź `master`, folder `/docs`).

## Uruchomienie ręczne workflow

GitHub → zakładka **Actions** → workflow **„Scrape – Rada Nadzorcza"** →
przycisk **Run workflow**.

## Uruchomienie lokalne

```bash
pip install -r requirements.txt
python main.py            # domyślnie: ostatni miesiąc, raport HTML
python main.py --help     # szczegóły flag (miesiące, data graniczna, ścieżka wyjściowa)
```

## Struktura repozytorium

| Plik / katalog | Opis |
|---|---|
| `main.py` | punkt wejścia (argumenty CLI, orkiestracja) |
| `scraper.py` | wyszukiwanie DDG + pobieranie źródeł bezpośrednich + filtry |
| `sources.py` | whitelist źródeł (ministerstwa, spółki SP, porty) |
| `report_html.py` | generator raportu HTML |
| `generate_index.py` | indeks raportów (`docs/index.html`) |
| `docs/reports/` | opublikowane raporty |
| `.github/workflows/scrape.yml` | harmonogram / workflow Actions |
