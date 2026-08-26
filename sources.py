# -*- coding: utf-8 -*-
"""
Lista zweryfikowanych źródeł (BIP, strony korporacyjne, ministerstwa), które
publikują ogłoszenia o naborach / konkursach na członków rad nadzorczych.

Dlaczego whitelist?
DuckDuckGo zwraca pomieszane wyniki: reklamy agregatorów (jooble), artykuły
prawne (lex.pl), treści egzaminacyjne oraz PRZETERMINOWANE ogłoszenia.
Zgodnie z ustawą o zasadach zarządzania mieniem państwowym ogłoszenia
o konkursach muszą być publikowane na stronie internetowej spółki oraz
właściwego ministra — dlatego czytamy te źródła BEZPOŚREDNIO.

Każdy wpis ma status `verified` (True = potwierdzono działanie i poprawność
encji w dniu utworzenia listy; False = do obserwacji, crawler pomija błędy).

UWAGA STRUKTURALNA: skrobak NIE polega na statycznych selektorach CSS każdej
strony (te się zmieniają). Zamiast tego traktuje każdy wpis jako punkt startowy
i szuka na stronie odnośników pasujących do wzorców w scraper.py
(RECRUITMENT_LINK_RE / RAD_NADZORCZA_RE). Dzięki temu zmiana layoutu nie psuje
działania — psuje je dopiero całkowita zmiana adresu.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """Jedno źródło do bezpośredniego przeszukiwania."""
    id: str          # krótki identyfikator techniczny
    name: str        # nazwa wyświetlana w logach
    url: str         # punkt startowy (strona główna lub sekcja aktualności)
    category: str    # 'ministerstwo' | 'spolka' | 'portal'
    verified: bool   # czy potwierdzono dostępność i właściwą encję


SOURCES: list = [
    # ------------------------------------------------------------------
    # Ministerstwa / centra rządowe (obowiązek publikacji konkursów)
    # ------------------------------------------------------------------
    Source("map",      "Ministerstwo Aktywów Państwowych",
           "https://www.gov.pl/web/aktywa-majatkowe/aktualnosci", "ministerstwo", True),
    Source("mf",       "Ministerstwo Finansów",
           "https://www.gov.pl/web/finanse/aktualnosci", "ministerstwo", False),
    Source("miklimat", "Ministerstwo Klimatu i Środowiska",
           "https://www.gov.pl/web/klimat/aktualnosci", "ministerstwo", False),
    Source("minfra",   "Ministerstwo Infrastruktury",
           "https://www.gov.pl/web/infrastruktura/aktualnosci", "ministerstwo", False),
    Source("mcyrfr",   "Ministerstwo Cyfryzacji",
           "https://www.gov.pl/web/cyfryzacja/aktualnosci", "ministerstwo", False),

    # ------------------------------------------------------------------
    # Największe spółki Skarbu Państwa / z istotnym udziałem SP
    # ------------------------------------------------------------------
    Source("orlen",    "ORLEN S.A.",
           "https://www.orlen.pl", "spolka", True),
    Source("gkpge",    "Grupa PGE",
           "https://www.gkpge.pl", "spolka", False),     # blokada botów dla części UA
    Source("tauron",   "TAURON Polska Energia",
           "https://www.tauron.pl", "spolka", True),
    Source("enea",     "Grupa Enea",
           "https://grupa-enea.pl", "spolka", False),
    Source("energa",   "Grupa Energa",
           "https://www.grupa-energa.pl", "spolka", False),
    Source("kghm",     "KGHM Polska Miedź",
           "https://kghm.com", "spolka", True),
    Source("plk",      "PKP Polskie Linie Kolejowe",
           "https://www.plk-sa.pl", "spolka", True),
    Source("pkpcargo", "PKP Cargo",
           "https://pkpcargo.com", "spolka", False),
    Source("intercity","PKP Intercity",
           "https://www.intercity.pl", "spolka", False),
    Source("poczta",   "Poczta Polska",
           "https://www.poczta-polska.pl", "spolka", True),
    Source("pzu",      "Grupa PZU",
           "https://www.pzu.pl", "spolka", True),        # było chwilowo w przerwie tech.
    Source("gpw",      "GPW Warszawska Giełda Papierów Wartościowych",
           "https://www.gpw.pl", "spolka", True),
    Source("kdpw",     "KDPW",
           "https://www.kdpw.pl", "spolka", False),
    Source("bgk",      "Bank Gospodarstwa Krajowego",
           "https://www.bgk.pl", "spolka", True),
    Source("pkobp",    "PKO Bank Polski",
           "https://www.pkobp.pl", "spolka", False),
    Source("gazsystem","Gaz-System",
           "https://www.gaz-system.pl", "spolka", False),
    Source("pse",      "Polskie Sieci Elektroenergetyczne",
           "https://www.pse.pl", "spolka", True),
    Source("pfr",      "Polski Fundusz Rozwoju",
           "https://pfr.pl", "spolka", False),
    Source("cpk",      "Centralny Port Komunikacyjny",
           "https://cpk.pl", "spolka", False),
    Source("wody",     "Wody Polskie",
           "https://www.wody.gov.pl", "spolka", False),
    Source("arp",      "ARP Industrial (Agencja Rozwoju Przemysłu)",
                      "https://www.arpindustrial.pl", "spolka", False),

    # ------------------------------------------------------------------
    # Samorządy (gminy/powiaty) - oficjalne miejsca publikacji ogloszen
    # o naborach na clonkow rad nadzorczych jednostek samorzadu
    # lokalnego. Adresy zweryfikowane HTTP 200 w dniu 2026-08-26.
    # Dla pozostalych gmin/powiatow odkrycie zapewnia faza DDG
    # (zapytania `site:bip.gov.pl`) - patrz scraper.SEARCH_QUERIES.
    # ------------------------------------------------------------------
    Source("um_jaslo",     "BIP Miasta Jaslo",
           "https://um_jaslo.bip.gov.pl", "bip", True),
    Source("bip_krakow",   "BIP m.st. Krakow",
           "https://www.bip.krakow.pl", "bip", True),
    Source("bip_wroclaw",  "BIP m.st. Wroclaw",
           "https://bip.wroclaw.pl", "bip", True),
    Source("bip_poznan",   "BIP m.st. Poznan",
           "https://bip.poznan.pl", "bip", True),
    Source("bip_bialystok","BIP m.st. Bialystok",
           "https://bip.bialystok.pl", "bip", True),


    # ------------------------------------------------------------------
    # Porty morskie (samorządowe / spółki z udziałem państwa)
    # ------------------------------------------------------------------
    Source("portgd",   "Zarząd Morskich Portów Gdańsk",
           "https://www.port.gdansk.pl", "spolka", False),
    Source("portgy",   "Zarząd Portów Gdynia",
           "https://www.port.gdynia.pl", "spolka", False),
    Source("portszcz", "Szczecińskie i Świnoujskie Porty",
           "https://port.szczecin.pl", "spolka", False),
]


def active_sources() -> list:
    """Zwraca listę aktywnych źródeł (cała lista; blokady obsługiwane w crawlerze)."""
    return list(SOURCES)
